import os
from typing import List, Tuple

from alpha_mini_rug import perform_movement
from alpha_mini_rug.speech_to_text import SpeechToText
from autobahn.twisted.component import Component, run
from autobahn.twisted.util import sleep
from dotenv import load_dotenv
from openai import OpenAI
from twisted.internet.defer import inlineCallbacks


load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
realm  = os.environ.get("REALM")
model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def get_llm_response(user_input: str|None, conversation_history: List) -> Tuple[str, List]:
    """Fetches response from the LLM given an optional input and preceeding context.

    :param str|None user_input: optional prompt from the user
    :param List conversation_history: previous prompts in the current context; the llm response is appended to this list
    :return: tuple, newly generated llm response + appended context 
    :rtype: tuple[str|None, List]

    """
    if user_input:
        conversation_history.append({"role": "user", "content": user_input})
    try:
        response = client.chat.completions.create(
            messages=conversation_history, model=model, temperature=0.3
        )
        answer = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": answer})
        return answer if answer else "", conversation_history
    except Exception as e:
        print(f"Error in API call: {e}")
        return (
            "I'm having trouble processing that. Could you try again?",
            conversation_history,
        )


@inlineCallbacks
def STT_setup(session):
    """Sets up google SpeechToText and subscribes to the audio stream from the robot.

    :param session: wamp session object
    :return: audio_processor object
    """
    # Setup
    audio_processor = SpeechToText()
    audio_processor.silence_time = 1
    audio_processor.silence_threshold2 = 200
    audio_processor.logging = False

    info = yield session.call("rom.sensor.hearing.info")
    print("Hearing Info:", info)

    yield session.call("rom.sensor.hearing.sensitivity", 1650)
    yield session.call("rie.dialogue.config.language", lang="en")

    # Subscribe to the audio stream and pass the data to the audio_processor
    yield session.subscribe(
        audio_processor.listen_continues, "rom.sensor.hearing.stream"
    )
    yield session.call("rom.sensor.hearing.stream")
    return audio_processor


@inlineCallbacks
def listen(session, audio_processor):
    """Have the robot listen to a human response.

    Has the robot tilt its head to indicate it's listening. 

    :param session: wamp session object
    :param audio_processor: SpeechToText instance connected to the robot
    :return: human response
    :rtype: str
    """
    perform_movement(session, frames=[{"time": 400, "data": {"body.head.roll": -0.174}}], force=True)
    audio_processor.do_speech = True
    print("Listening...")
    while not audio_processor.new_words:
        yield sleep(0.5)
        audio_processor.loop()
    perform_movement(session, frames=[{"time": 400, "data": {"body.head.roll": 0}}], force=True)

    # Return the last sentence heard, and turn off listening
    word_array = audio_processor.give_me_words()
    audio_processor.do_speech = False
    print("Stopped listening")
    return word_array[-1][0] if word_array else ""


@inlineCallbacks
def say_and_listen(session, audio_processor, question_text: str):
    """Make the robot say a string and listen for a human response.

    Turns off the robot's microphone while speaking to avoid self-hearing:
    Turn ears OFF -> Speak -> Turn ears ON -> Wait for reply -> Turns ears OFF

    :param session: wamp session object
    :param audio_processor: SpeechToText instance connected to the robot
    :return: human response
    :rtype: str
    """
    # don't listen
    audio_processor.do_speech = False
    # Ask the question
    yield session.call("rie.dialogue.say_animated", text=question_text)

    return listen(session, audio_processor)


@inlineCallbacks
def get_to_know_conversation(session, audio_processor):
    """Models an initial conversation between a child with DLD and the robot.

    The robot (through an LLM) will ask the child a few simple questions, then summarize the gleaned information and return it.

    :param session: wamp session object
    :param audio_processor: SpeechToText instance connected to the robot
    :return: summary of information about the human conversing with the robot
    :rtype: str
    """
    context = [{"role": "developer",
                "content": """"
                You are a friendly robot companion talking to a child with Developmental Language Disorder (DLD).
                The child has difficulty understanding complex sentences and finding the right words to say.

                Follow these STRICT rules:
                1. (most important) keep sentences extremely short. Maximum 1 to 2 sentences per turn.
                2. Ask only ONE question at a time
                3. ALWAYS give the child options to choose from (eg. "favorite color is green or blue").
                4. Whatever the child answers, say their choice was great a great choice (to encourage them to speak)

                Your main goal for now is to get to know the child.
                """}]

    robot_speech = "Hey there! My name is alpharobot. Can you tell me your name?"
    context.append({"role": "assistant", "content": robot_speech})

    for _ in range(3):
        # listen to what human says
        human_answer = yield say_and_listen(session, audio_processor, robot_speech)
        print(f"Human said: {human_answer}")
        # get LLM response
        robot_speech, context = get_llm_response(human_answer, context)
        print(f"Robot planned response: {robot_speech}")

    yield session.call("rie.dialogue.say_animated", text=robot_speech)
    human_answer = yield listen(session, audio_processor)
    print(f"Human said: {human_answer}")
    context.append({"role": "user", "content": human_answer})

    context.append({"role": "developer",
                    "content": "Now that we know more about the user, tell me in a very compressed manner all the information about the user. The goal is to give this context to another agent to know the preferences of the user"})
    response = client.chat.completions.create(
        messages=context, model="gpt-4o-mini", temperature=0.3
    )
    answer = response.choices[0].message.content
    return answer


@inlineCallbacks
def open_ended_conversation(session, audio_processor, human_information):
    """Models an extended conversation between a child with DLD and the robot.

    This conversation has no predetermined limit and will keep going until an exit keyword is said by the child.

    :param session: wamp session object
    :param audio_processor: SpeechToText instance connected to the robot
    :param str human_information: compressed summary of information about the child in natural language, provided by a speech therapist, caregiver, or a previous conversation with the robot
    """
    exit_conditions = ("quit", "exit", "goodbye")
    context = [{
        "role": "developer",
        "content": f"""
            You are a friendly robot companion talking to a child with Developmental Language Disorder (DLD).
            The child has difficulty understanding complex sentences and finding the right words to say.

            A preliminary conversation with the child has already been performed, which yielded the following information: `{human_information}`.
            
            The goal of this conversation is to further get the child comfortable and familiar with talking to a robot companion. Your goal is to keep the conversation going on topics that the child is familiar and interested in.

            Follow these STRICT rules:
            1. (most important) keep sentences extremely short. Maximum 1 to 2 sentences per turn.
            2. Ask only ONE question at a time; OR let the child ask you questions instead.
            3. when asking a question, ALWAYS give the child options to choose from (eg. "favorite color is green or blue")
            4. Whatever the child answers, say their choice was great a great choice (to encourage them to speak)

            To begin with, ask the child a question based on the contextual information provided above.
        """,
    }]

    human_answer = ""
    robot_speech, context = get_llm_response(None, context)

    while True:
        if any(word in human_answer for word in exit_conditions):
            # wrap up conversation
            return
        else:
            # keep talking
            human_answer = yield say_and_listen(session, audio_processor, robot_speech)
            print(f"Human said: {human_answer}")

            # get LLM response
            robot_speech, context = get_llm_response(human_answer, context)
            print(f"Robot planned response: {robot_speech}")


@inlineCallbacks
def main(session, details):
    """Main function containing driver code.

    Will go through two distinct conversations with a human, one which gathers basic information, and an open-ended conversation to build rapport.

    :param session: wamp session object
    :param details: wamp session details
    """
    yield session.call("rom.optional.behavior.play", name="BlocklyStand")

    audio_processor  = yield STT_setup(session)

    human_information = yield get_to_know_conversation(session, audio_processor)
    print(human_information)

    yield open_ended_conversation(session, audio_processor, human_information)

    # Wrap up
    yield session.call("rie.dialogue.stt.close")
    yield session.call("rie.dialogue.say_animated", text="Goodbye.")
    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    session.leave()


wamp = Component(
    transports=[
        {
            "url": "wss://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"],
            "max_retries": 0,
        }
    ],
    realm=realm,
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])
