from session import SessionWrapper
import logging
import settings
from twisted.internet.defer import inlineCallbacks


@inlineCallbacks
def pleasantries(s: SessionWrapper):
    """Models small-talk between a human and robot, using personal information gleaned from previous sessions.

    The robot (through an LLM) will ask a few simple questions, mostly phatic expressions, in order to get the human comfortable and at ease.

    :param s: wrapper containing all required context + conversational history
    :return how cooperative the LLM estimates the child is for learning [1-5], and a short elaboration.
    :rtype tuple[int, str[
    """
    s.conversation_history.append({"role": "developer", # TODO (medium priority): refine this prompt for the LLM
                "content": f"""
                You are a friendly robot companion talking to a child with Developmental Language Disorder (DLD).
                The child has difficulty understanding complex sentences and finding the right words to say.

                The following is contextual information for the child you are interacting with: {s.human_context}
                The child may be more or less expressive, as indicated by the context; adjust accordingly.

                The goal of this conversation is to get the child comfortable talking to the robot. To this end, do the following:
                1. greet them excitedly! if the child responds meaninfully, continue in the direction of conversation for a question or two.
                2. ask them if they did anything interesting recently; suggest some of their interests from the contextual information.
                3. make sure to encourage the child's responses if appropriate.

                Keep in mind that the audio processing attached to the robot is not the best; if the child says something that you determine is nonsensical, ask for clarification instead of immediately accepting a new conversational thread.
                Additionally, this conversation consists of exactly 5 turns; keep this in mind when planning your responses.

                Do not use emojis. Start by saying somehting along the lines of "hello [name], how nice to see you again. Are you ready to play?"
                """})
    robot_speech = s.get_llm_response(None)
    logging.info(f"Robot speech: {robot_speech}")
    
    s.conversation_history.append({"role": "assistant", "content": robot_speech})

    for _ in range(5):
        human_answer = yield input("Enter human response: ") if settings.debug else s.say_and_listen(robot_speech)
        robot_speech = s.get_llm_response(human_answer)
        logging.info(f"Robot speech: {robot_speech}")

    if not settings.debug:
        yield s.session.call("rie.dialogue.say_animated", text=robot_speech)

    human_answer = yield input("Enter human response: ") if settings.debug else s.listen()
    s.conversation_history.append({"role": "user", "content": human_answer})

    # Respond to the last answer so the conversation doesn't end abruptly.
    s.conversation_history.append({"role": "developer", 
                "content": f"""That's it for the pleasantries. Acknowledge the child's last response and tell them in a friendly, polite way that we're going to be moving on to the learning part of the session now-- by playing a few games! Express this sentiment in at most two sentences. """})

    robot_speech = s.get_llm_response(None)

    if not settings.debug:
        s.say(robot_speech)

    s.conversation_history.append({"role": "developer",
        "content": "Now that we have talked to the user for a bit, tell me in a very compressed manner how the user is feeling. Respond by giving a number on a scale of 1-5 indicating how ready for learning you believe the user to be, followed by a short, single sentence which elaborates on the number. USE THIS FORMAT: [1-5]; <summary>."})
    response = s.client.chat.completions.create(
        messages=s.conversation_history, model=s.model, temperature=0.3
    )

    #TEST: untested
    # FIXME: always crashes on unparsable response; dunno why
    answer = response.choices[0].message.content or ""
    s.conversation_history.append({"role": "assistant", "content": answer})
    try: 
        num, rsn = answer.split(';')
        return (int(num, rsn))
    except Exception as e:
        logging.warning("LLM returned unparsable response while returning from pleasantries")
        logging.info(e.__traceback__)
        return (-1, "")
