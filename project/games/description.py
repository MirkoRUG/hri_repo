import logging
import settings
from session import SessionWrapper
from twisted.internet.defer import inlineCallbacks

MAX_CLUES = 4


@inlineCallbacks
def run(s: SessionWrapper):
    """Description game: robot describes a word, child guesses it.

    The robot gives progressively more specific clues until the child guesses
    correctly or MAX_CLUES clues have been given.
    """
    game_history = [
        {
            "role": "developer",
            "content": f"""You are a speech therapist social-robot helping a child with Developmental Language Disorder practice language.
You are playing a word guessing game. Your job is to describe a word so the child can guess it.

Rules of the game:
- Think of ONE simple, common word appropriate for a child (animal, food, object, or action).
- First, output **ONLY** the word you chose on a line by itself, prefixed with "WORD:" (e.g. "WORD: apple"). **Do not say anything else yet**.
- The child tries to guess the word. If they don't gess, you give progressively more helpful clues
- Do not use the word itself or obvious synonyms in the clues.

Interaction guidelines:
- (most important) keep sentences extremely short. Maximum 1 to 2 sentences per turn.
- The child has difficulty understanding complex sentences and finding the right words to say.
- Use very simple vocabulary
""",
        }
    ]

    # 1. ave the LLM pick a word
    response = s.client.chat.completions.create(
        messages=game_history, model=s.model, temperature=0.9
    )
    answer = (response.choices[0].message.content or "")
    game_history.append({"role": "assistant", "content": answer})

    target_word = ""
    if answer.upper().startswith("WORD:"):
        target_word = answer.split(":")[1].strip().lower()

    if not target_word:
        logging.warning(f"Could not parse target word from LLM: {answer}")
        target_word = "apple"

    logging.info(f"[description game] target word: {target_word}")

    # Tell the LLM what its job is for the rest of the game
    game_history.append(
        {
            "role": "developer",
            "content": f"""The word is "{target_word}".
Now play the game:
- Give one clue at a time, starting broad and getting more specific with each turn.
- After each clue, wait for the child's guess.
- If the child guesses correctly, say "YES! Well done!" followed by a short celebration. **Begin that message with "CORRECT:" so the system can detect the correct guess.**
- If the guess is wrong, give a more specific clue. Do NOT say the word.
- Keep all sentences short and simple.
""",
        }
    )

    # 2. Get first broad clue before saying anything
    game_history.append({"role": "user", "content": "Give me the first clue."})
    response = s.client.chat.completions.create(
        messages=game_history, model=s.model, temperature=0.5
    )
    clue = (response.choices[0].message.content or "")
    game_history.append({"role": "assistant", "content": clue})

    for clue_num in range(MAX_CLUES):
        if clue_num == 0:
            # Combine intro + first clue into a single say call to avoid any overlap
            intro = f"Let's play a guessing game! I will describe a word, and you try to guess what it is. Here is your first clue: {clue}"

        human_guess = yield s.say_and_listen(intro) if not settings.debug else input(f"[clue {clue_num+1}: {clue}].")

        logging.info(f"Child guessed: {human_guess}")
        game_history.append({"role": "user", "content": human_guess})

        response = s.client.chat.completions.create(
            messages=game_history, model=s.model, temperature=0.3
        )
        robot_reply = (response.choices[0].message.content or "")
        game_history.append({"role": "assistant", "content": robot_reply})

        if "correct" in robot_reply.lower():
            celebration = robot_reply[len("CORRECT:"):].strip()
            yield s.say(celebration) if not settings.debug else print(f"[robot] {celebration}")
            logging.info(f"Child guessed correctly: {target_word}")
            return

        # Wrong guess
        clue = robot_reply

    # Ran out of clues
    reveal = f"The word was {target_word}! Good try, maybe next time you'll get it!"
    yield s.say(reveal) if not settings.debug else print(f"[robot] {reveal}")
