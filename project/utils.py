"""This file contains a collection of miscellaneous utility functions."""

from twisted.internet.defer import inlineCallbacks
from typing import List

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
    audio_processor.silence_time = 2
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
