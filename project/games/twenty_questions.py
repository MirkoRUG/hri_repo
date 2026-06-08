import logging

import settings
from session import SessionWrapper
from twisted.internet.defer import inlineCallbacks

MAX_QUESTIONS = 20


def interpret_yes_no(s: SessionWrapper, child_response: str) -> str:
    """Classify a child's answer to a yes/no answer. Makes it easier to parse.

    :param child_response: whatever the child said
    :return: one of "yes", "no", or "unclear"
    :rtype: str
    """
    if not child_response:
        return "unclear"

    context = [{
        "role": "developer",
        "content": """You classify a child's spoken answer to a yes-or-no question.
Respond with EXACTLY ONE lowercase word:
- "yes" if the child agrees or confirms (yes, yeah, yep, correct, right, uh-huh, ...).
- "no" if the child disagrees or denies (no, nope, nah, wrong, not really, ...).
- "unclear" if you really cannot tell.
Output only one of: yes, no, unclear.""",
    }]

    response = s.get_custom_llm_response(context, child_response).strip().lower()
    if response in ("yes", "no", "unclear"):
        return response
    else:
        return "unclear"


@inlineCallbacks
def run(s: SessionWrapper):
    """Twenty Questions: the child thinks of something, the robot guesses it,
    by only asking yes or no questions.

    :param s: session object
    """
    game_history = [{
        "role": "developer",
        "content": f"""You are a friendly social robot playing the game Twenty Questions with a child who has Developmental Language Disorder (DLD).
The child has thought of any word (an animal, a food, an object, a person, a place, ...) and you must guess it by asking yes/no questions.

Rules of the game:
- Start broad to find the kind of thing it is (e.g. "Is it an animal?", "Is it something you can eat?"), then narrow down.
- Ask ONE short yes/no question per turn (e.g. "Does it have four legs?", "Can it fly?").
- The child can ONLY answer yes or no, so NEVER ask open questions.
- Use the answers so far to narrow down the word. Never repeat a question.
- When you are fairly sure of an answer, make a guess by naming one specific word.
  Prefix that guess with "GUESS:" (e.g. "GUESS: Is it a dog?").
  **Only use the "GUESS:" prefix when you are naming one specific word.**

Interaction guidelines:
- Keep every question to ONE short, simple sentence.
- **Use VERY SIMPLE vocabulary; the child struggles with language.**

The following is contextual information for the child you are interacting with: {s.human_context}
""",
    }]

    # Introduce the game and let the child settle on something.
    intro = (
        """Let's play Twenty Questions! Think of any word, but don't tell me.
        I will try to guess it. You only have to say yes or no. Ready?"""
    )
    yield s.say(intro, say_animated=True) if not settings.debug else logging.info(f"[robot] {intro}")

    # Overwrite the first child's repoly. This makes sure the game starts smoothly
    ready = yield s.listen() if not settings.debug else input("[child ready?] ")
    logging.info(f"Child ready response: {ready}")
    game_history.append({"role": "user", "content": "I am thinking of a word."})

    for question_num in range(MAX_QUESTIONS):
        response = s.client.chat.completions.create(
            messages=game_history, model=s.model, temperature=0.4
        )
        robot_question = (response.choices[0].message.content or "").strip()
        game_history.append({"role": "assistant", "content": robot_question})
        logging.info(f"Robot question {question_num + 1}: {robot_question}")

        # Sanitize the guess
        is_guess = robot_question.upper().startswith("GUESS:")
        spoken = robot_question[len("GUESS:"):].strip() if is_guess else robot_question

        # Ask the child and collect their yes/no answer.
        child_response = yield s.say_and_listen(spoken) if not settings.debug else input("Human answer: ")
        logging.info(f"Child answered: {child_response}")

        answer = interpret_yes_no(s, child_response)

        # If we couldn't tell, gently re-ask the same question without burning a turn.
        while answer == "unclear":
            reprompt = "Sorry, I didn't catch that. Can you say yes or no?"
            child_response = yield s.say_and_listen(reprompt) if not settings.debug else input(f"[repeat Q{question_num + 1}] ")
            logging.info(f"Child re-answered: {child_response}")
            answer = interpret_yes_no(s, child_response)

        # Feed the interpreted answer back so the model reasons on a clean signal.
        game_history.append({"role": "user", "content": answer})

        if is_guess and answer == "yes":
            celebration = "Yes! I guessed it! Great job, that was so much fun!"
            yield s.say(celebration) if not settings.debug else logging.info(f"[robot] {celebration}")
            logging.info("Robot guessed correctly.")
            return

    # Ran out of questions; give up gracefully and let the child reveal the answer.
    give_up = "Phew, you really stumped me! I give up. What was your word?"
    reveal = yield s.say_and_listen(give_up) if not settings.debug else input("[reveal] ")
    logging.info(f"Child revealed: {reveal}")

    closing = "Wow, I would never have guessed that! Thanks for playing with me."
    yield s.say(closing) if not settings.debug else logging.info(f"[robot] {closing}")
