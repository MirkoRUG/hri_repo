import logging

from openai import OpenAI
from twisted.internet.defer import inlineCallbacks
from alpha_mini_rug.speech_to_text import SpeechToText
from alpha_mini_rug import perform_movement
from autobahn.twisted.util import sleep
from typing import List
from autobahn.twisted.wamp import Session
import os

class SessionWrapper:
    """Wrapper for the wamp object. Keeps track of LLM related variables as well."""
    audio_processor: SpeechToText
    conversation_history: List = []
    client: OpenAI
    model: str
    human_context: str
    session: Session
    language_level: int = 1

    def __init__(self, session, name: str):
        self.session = session
        self.language_level = 1
        self.setup_STT()
        self.load_personalization_data(name)

        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


    def load_personalization_data(self, name: str):
        """Loads details on personalization from file, indexed by filename.

        Assumes the files are stored in the relative folder './data' and in the format '<name>.md'.

        :param name: filename to load data from
        """
        logging.debug(f"loading personalization info for {name}")
        with open(f"data/{name}.md") as f:
            self.human_context = f.read()
            
    def count_child_words(self) -> int:
        """Count all words spoken by the child so far."""

        total = 0

        for message in self.conversation_history:
            if message["role"] == "user":
                total += len(message["content"].split())

        return total
    
    def determine_language_level(self):
        """Calculate the child's level based on the word count in the initial conversation."""
        words = self.count_child_words()

        if words < 5: 
            self.language_level = 1
        elif words < 15:
            self.language_level = 2
        elif words < 30:
            self.language_level = 3
        else:
            self.language_level = 4

        logging.info(
            f"Child spoke {words} words. "
            f"Assigned level {self.language_level}"
        )

    @inlineCallbacks
    def setup_STT(self):
        """Sets up google SpeechToText and subscribes to the audio stream from the robot.

        :param session: wamp session object
        :return: audio_processor object
        """
        # Setup
        self.audio_processor = SpeechToText()
        self.audio_processor.silence_time = 2
        self.audio_processor.silence_threshold2 = 200
        self.audio_processor.logging = False

        info = yield self.session.call("rom.sensor.hearing.info")
        logging.debug("Hearing Info:", info)

        yield self.session.call("rom.sensor.hearing.sensitivity", 1650)
        yield self.session.call("rie.dialogue.config.language", lang="en")

        # Subscribe to the audio stream and pass the data to the audio_processor
        yield self.session.subscribe(
            self.audio_processor.listen_continues, "rom.sensor.hearing.stream"
        )
        yield self.session.call("rom.sensor.hearing.stream")


    def get_llm_response(self, user_input: str|None) -> str:
        """Fetches response from the LLM given an optional input and preceeding context.

        :param str|None user_input: optional prompt from the user
        :return: newly generated llm response
        :rtype: str

        """
        if user_input:
            self.conversation_history.append({"role": "user", "content": user_input})
        try:
            response = self.client.chat.completions.create(
                messages=self.conversation_history, model=self.model, temperature=0.3
            )
            answer = response.choices[0].message.content
            self.conversation_history.append({"role": "assistant", "content": answer})
            return answer if answer else ""
        except Exception as e:
            logging.warning(f"Error in API call: {e}")
            return "I'm having trouble processing that. Could you try again?"


    @inlineCallbacks
    def listen(self): # FIXME (low priority): figure out how to add typing to inlineCallbacks
        """Have the robot listen to a human response.

        Has the robot tilt its head to indicate it's listening. 

        :return: human response
        :rtype: str
        """
        perform_movement(self.session, frames=[{"time": 400, "data": {"body.head.roll": -0.174}}], force=True)
        self.audio_processor.do_speech = True
        logging.debug("Listening...")
        while not self.audio_processor.new_words:
            yield sleep(0.5)
            self.audio_processor.loop()
        perform_movement(self.session, frames=[{"time": 400, "data": {"body.head.roll": 0}}], force=True)

        # Return the last sentence heard, and turn off listening
        word_array = self.audio_processor.give_me_words()
        self.audio_processor.do_speech = False
        logging.debug("Stopped listening") 
        logging.info(f"Human speech: {word_array[-1][0] if word_array else ""}")
        return word_array[-1][0] if word_array else ""


    @inlineCallbacks
    def say_and_listen(self, question_text: str):
        """Make the robot say a string and listen for a human response.

        Turns off the robot's microphone while speaking to avoid self-hearing:
        Turn ears OFF -> Speak -> Turn ears ON -> Wait for reply -> Turns ears OFF

        :return: human response
        :rtype: str
        """
        # don't listen
        self.audio_processor.do_speech = False
        # Ask the question
        yield self.session.call("rie.dialogue.say_animated", text=question_text)

        response = yield self.listen()
        return response

