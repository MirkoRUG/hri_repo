from session import SessionWrapper
import logging
import settings


def wrapup(s: SessionWrapper):
    """Final part of the conversation between the robot and a child.

    Basically an outro;
    the robot will reflect on the played games and say goodbye to the child.
    """
    if not settings.debug:
        yield s.session.call("rie.dialogue.stt.close")

    s.conversation_history.append({"role": "developer", 
                "content": f"""
                You are a friendly robot companion talking to a child with Developmental Language Disorder (DLD).
                The child has difficulty understanding complex sentences and finding the right words to say.

                The following is contextual information for the child you are interacting with: {s.human_context}
                The child may be more or less expressive, as indicated by the context; adjust accordingly.

                The child just finished playing a number of language learning games with the robot (via a different llm).
                The goal of this conversation is to politely wrap up the interaction. To this end, do the following:
                1. Ask the child if they liked playing together! Feel free to ask one or two follow-up questions depending on their answer.
                2. Adjust your responses to the age of the child (use more in-depth sentences for older children and vice versa.)
                3. The child already had a lengthy interaction with the robot through a different llm. Do not greet them as if this is the start of the conversation.
                4. IF THE USER PROMPT IS (near)-EMPTY: it's likely the speech-to-text failed; ask the user to clarify.
                5. This part of the conversation will last for 3 turns in total. Keep this in mind when planning your responses.
                """})

    robot_speech = s.get_llm_response()
    logging.info(f"Robot speech: {robot_speech}")
    
    s.conversation_history.append({"role": "assistant", "content": robot_speech})

    for _ in range(3):
        human_answer = yield input("Enter human response: ") if settings.debug else s.say_and_listen(robot_speech)
        robot_speech = s.get_llm_response(human_answer)
        logging.info(f"Robot speech: {robot_speech}")

    if not settings.debug:
        yield s.say(robot_speech)

    human_answer = yield input("Enter human response: ") if settings.debug else s.listen()
    s.conversation_history.append({"role": "user", "content": human_answer})

    # Respond to the last answer so the conversation doesn't end abruptly.
    s.conversation_history.append({"role": "developer", 
                "content": f"""That's it for the conversation. Acknowledge the child's last response, then say goodbye!"""})

    robot_speech = s.get_llm_response()

    if not settings.debug:
        s.say(robot_speech)
        yield s.session.call("rom.optional.behavior.play", name="BlocklyCrouch")
        s.session.leave()
