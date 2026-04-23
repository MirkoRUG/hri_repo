import os

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


def get_llm_response(user_input, conversation_history):
    conversation_history.append({"role": "user", "content": user_input})
    try:
        response = client.chat.completions.create(
            messages=conversation_history, model="gpt-4o-mini", temperature=0.3
        )
        answer = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": answer})
        return answer, conversation_history
    except Exception as e:
        print(f"Error in API call: {e}")
        return (
            "I'm having trouble processing that. Could you try again?",
            conversation_history,
        )


@inlineCallbacks
def STT_setup(session):
    # Setup
    audio_processor = SpeechToText()
    audio_processor.silence_time = 1
    audio_processor.silence_threshold2 = 100
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
def say_and_listen(session, audio_processor, question_text):
    """
    To avoid self-hearing:
    Turn ears OFF -> Speak -> Turn ears ON -> Wait for reply -> Turns ears OFF
    """
    # don't listen
    audio_processor.do_speech_recognition = False
    # Ask the question
    yield session.call("rie.dialogue.say_animated", text=question_text)

    perform_movement(session, frames=[{"time": 400, "data": {"body.head.roll": -0.174}}], force=True)
    # List to reply (waiting)
    audio_processor.do_speech_recognition = True
    while not audio_processor.new_words:
        yield sleep(0.5)
        audio_processor.loop()
    perform_movement(session, frames=[{"time": 400, "data": {"body.head.roll": 0}}], force=True)

    # Return the last sentence heard, and turn off listening
    word_array = audio_processor.give_me_words()
    audio_processor.do_speech_recognition = False
    return word_array[-1][0] if word_array else ""


@inlineCallbacks
def main(session, details):
    yield session.call("rom.optional.behavior.play", name="BlocklyStand")

    audio_processor = yield STT_setup(session)

    # System prompt to keep responses brief for the draft
    context = [{"role": "developer", "content": "You are a social robot being used in the context of speech and language therapy to help children with developmental language disorder. The interaction will consist of a getting-to-know-you conversation with a new patient. "}]
    robot_speech = "I'm ready to listen now. say something."

    # conversational loop
    for _ in range(3):
        human_answer = yield say_and_listen(session, audio_processor, robot_speech)
        print(f"Human said: {human_answer}")

        # Prevent empty calls to OpenAI
        if not human_answer:
            robot_speech = "I didn't quite hear you."
            continue

        robot_speech, context = get_llm_response(human_answer, context)
        print(f"Robot planned response: {robot_speech}")

    # Wrap up
    yield session.call("rie.dialogue.say_animated", text=robot_speech + ". Goodbye.")
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
