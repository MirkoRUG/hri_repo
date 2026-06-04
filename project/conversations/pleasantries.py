from session import SessionWrapper
import logging
from twisted.internet.defer import inlineCallbacks


@inlineCallbacks
def pleasantries(s: SessionWrapper):
    """Models small-talk between a human and robot, using personal information gleaned from previous sessions.

    The robot (through an LLM) will ask a few simple questions, mostly phatic expressions, in order to get the human comfortable and at ease.

    :param s: wrapper containing all required context + conversational history
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
                """})
    robot_speech = s.get_llm_response(None)
    logging.info(f"Robot speech: {robot_speech}")
    
    s.conversation_history.append({"role": "assistant", "content": robot_speech})

    for _ in range(3):
        # human_answer = yield s.say_and_listen(robot_speech)
        human_answer = input("Enter human response:")
        robot_speech = s.get_llm_response(human_answer)
        logging.info(f"Robot speech: {robot_speech}")

    # yield s.session.call("rie.dialogue.say_animated", text=robot_speech)
    human_answer = input("Enter human response: ")
    # human_answer = yield s.listen()
    s.conversation_history.append({"role": "user", "content": human_answer})

    # FIXME (medium priority) the llm will keep asking questions making the exit of the conversation quite sudden; add a small closer saying we're moving onto the exercises now.

    s.conversation_history.append({"role": "developer",
        "content": "Now that we have talked to the user for a bit, tell me in a very compressed manner how the user is feeling. Respond by giving a number on a scale of 1-5 indicating how ready for learning you believe the user to be, followed by a short, single sentence which elaborates on the number. USE THIS FORMAT: [1-5]; <summary>."})
    response = s.client.chat.completions.create(
        messages=s.conversation_history, model=s.model, temperature=0.3
    )

    # FIXME (high priority): this function crashes the program for some reason (i suspect im using inlinecallbacks wrong)

    # would love to actually return the answer here but wamp does not twisted does not like that on inlinecallbacks. 
    # adding it to conversation history for now; probably should set variables on the Session object in the final iteration.
    answer = response.choices[0].message.content or ""
    s.conversation_history.append({"role": "assistant", "content": answer})
    
    # s.determine_language_level()
    # logging.info(
    #     f"Assigned language level: {s.language_level}"
    # )
