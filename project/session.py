import logging
from typing import List

import cv2
import numpy as np
import settings
from alpha_mini_rug import perform_movement
from alpha_mini_rug.speech_to_text import SpeechToText
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import Session
from body import Body
from deepface import DeepFace
from openai import OpenAI
from twisted.internet.defer import inlineCallbacks

EMOTION_FRAME_SKIP = 30

class SessionWrapper:
    """Wrapper for the wamp object. Keeps track of LLM related variables as well."""
    audio_processor: SpeechToText
    conversation_history: List = []
    client: OpenAI
    model: str
    human_name: str
    human_context: str
    conversation_context: str
    session: Session
    language_level: int = 1
    enthousiasm: int = 2
    current_emotion: str | None
    _frame_counter: int

    def __init__(self, session, name: str):
        self.session = session
        self.language_level = 1
        self.current_emotion = None
        self._frame_counter = 0
        self._body = Body()
        self.human_name = name
        self.conversation_context = ""
        self._body = Body()
        self.load_personalization_data()

        self.client = settings.client
        self.model = settings.model

    @inlineCallbacks
    def setup(self):
        if not settings.debug:
            yield self.session.call("rom.optional.behavior.play", name="BlocklySafeStand")
            yield self.setup_STT()
            # yield self.setup_vision()

    @inlineCallbacks
    def shut_down(self):
        if not settings.debug:
            cv2.destroyAllWindows()
            yield self.session.call("rom.sensor.sight.close")
            yield self.session.call("rom.optional.behavior.play", name="BlocklyCrouch")
            self.session.leave()

    def load_personalization_data(self):
        """Loads details on personalization from file, indexed by filename.

        Assumes the files are stored in the relative folder './data' and in the format '<name>.md'. 
        """
        with open(f"data/{self.human_name}.md", "r") as f:
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

    def save_personalization_data(self):
        """Save the current child profile."""
        with open(f"data/{self.human_name}-convo.md", "w") as f:
            f.write(self.conversation_context)

    def update_child_profile(self):
        """Update the child's profile using the latest conversation."""

        prompt = f"""
Current child profile: {self.human_context}
Conversation history: {self.conversation_history}

Update the profile with new information. 

Rules:
- Keep previously known information.
- Add new information learned from the conversation.
- Remove duplicated information.
- Keep the profile concise.
- Mention interests, hobbies, favourite things, recent activities,
family members, pets, personality traits or anything else useful
for future conversations.
- Include the current language level: {self.language_level}.

Only include the information in the current conversation, not the previously known information. 
"""

        response = self.client.chat.completions.create(
            messages=[{
                "role": "developer",
                "content": prompt
            }],
            model=self.model,
            temperature=0
            )

        self.conversation_context = response.choices[0].message.content or ""

    @inlineCallbacks
    def setup_STT(self):
        """Sets up google SpeechToText and subscribes to the audio stream from the robot.

        :param session: wamp session object
        :return: audio_processor object
        """
        # Setup
        self.audio_processor = SpeechToText()
        self.audio_processor.silence_time = 2
        self.audio_processor.silence_threshold2 = 1000
        self.audio_processor.logging = False

        info = yield self.session.call("rom.sensor.hearing.info")
        logging.debug("Hearing Info:", info)

        yield self.session.call("rom.sensor.hearing.sensitivity", 1650)
        yield self.session.call("rie.dialogue.config.language")

        # Subscribe to the audio stream and pass the data to the audio_processor
        yield self.session.subscribe(
            self.audio_processor.listen_continues, "rom.sensor.hearing.stream"
        )
        yield self.session.call("rom.sensor.hearing.stream")

    @inlineCallbacks
    def setup_vision(self):
        yield self.session.subscribe(self._on_frame, "rom.sensor.sight.stream")
        yield self.session.call("rom.sensor.sight.stream")

    def _on_frame(self, frame):
        if frame is None or not isinstance(frame, dict):
            return

        raw = frame["data"]["body.head.eyes"]
        nparr = np.frombuffer(raw, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        self._frame_counter += 1
        if self._frame_counter % EMOTION_FRAME_SKIP == 0:
            try:
                result = DeepFace.analyze(image, actions=["emotion"], enforce_detection=True)
                dominant = result[0]["dominant_emotion"]
                confidence = result[0]["emotion"][dominant]
                threshold = 90 if dominant == "sad" else 40
                if confidence >= threshold:
                    self.current_emotion = dominant
                    logging.info(f"Detected emotion: {self.current_emotion} ({confidence:.1f}%)")
            except Exception as e:
                logging.debug(f"DeepFace: {e}")

        if self.current_emotion:
            cv2.putText(image, self.current_emotion, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Camera Stream", image)
        cv2.waitKey(1)

    def get_custom_llm_response(self, context: List, user_input: str|None = None):
        """Fetches response from the LLM given an optional input and custom context.

        Useful for one-off prompts disconnected from the conversational flow.

        :param input: optional prompt from the user
        :param context: bespoke context for this prompt
        :return: generated llm response
        :rtype: str
        """
        if user_input:
            context.append({"role": "user", "content": user_input})
        try:
            response = self.client.chat.completions.create(
                messages=context, model=self.model, temperature=0.3
            )
            answer = response.choices[0].message.content
            return answer if answer else ""
        except Exception as e:
            logging.warning(f"Error in API call: {e}")
            return ""

    def get_llm_response(self, user_input: str|None = None) -> str:
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
        human_response = word_array[-1][0] if word_array else ""
        logging.debug("Stopped listening")
        logging.info(f"Human speech: {human_response}")

        if "dance" in human_response.lower():
            yield self.session.call("rom.optional.behavior.play", name="BlocklyThriller")
            yield sleep(15)

        return human_response

    @inlineCallbacks
    def say(self, text: str, say_animated: bool = False):
        """Make the robot say a string.

        Turns off the robot's microphone while speaking to avoid self-hearing.
        Picks a set of movements based on trigger words; falls back to say_animated.

        :param text: string to say
        :param say_animated: an overwrite to make sure the robot uses say_animated
        """
        # don't listen
        self.audio_processor.do_speech = False

        if say_animated:
            self.session.call("rie.dialogue.say_animated", text=text)
            return

        s = text.lower()
        # Select movement to go along with sentence
        if any(w in s for w in ["win", "victory", "congratulations"]):
            frames = self._body.victory_movement(s)
            perform_movement(self.session, frames=frames, force=True)
            yield self.session.call("rie.dialogue.say", text=text)
        elif any(w in s for w in ["food", "fruit", "drink", "beverage", " eat"]):
            frames = self._body.eating_movement(s)
            perform_movement(self.session, frames=frames, force=True)
            yield self.session.call("rie.dialogue.say", text=text)
        elif any(w in s for w in ["yes", "correct", "well done", "great job", "good job"]):
            frames = self._body.yes_movement()
            perform_movement(self.session, frames=frames, force=True)
            yield self.session.call("rie.dialogue.say", text=text)
        elif any(w in s for w in ["no ", "wrong", "incorrect"]):
            frames = self._body.no_movement()
            perform_movement(self.session, frames=frames, force=True)
            yield self.session.call("rie.dialogue.say", text=text)
        elif any(w in s for w in ["hello", "hey", "goodbye", "bye", "see you", "farewell", "hi!", "hi,", "hi!", "hi "]):
            self.session.call("rom.optional.behavior.play", name="BlocklyWaveRightArm")
            yield self.session.call("rie.dialogue.say", text=text)
        else:
            yield self.session.call("rie.dialogue.say_animated", text=text)

    @inlineCallbacks
    def say_and_listen(self, text: str):
        """Make the robot say a string and listen for a human response.

        :return: human response
        :rtype: str
        """
        yield self.say(text)
        response = yield self.listen()
        return response
