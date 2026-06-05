from session import SessionWrapper
from twisted.internet.defer import inlineCallbacks

# probably change
from .twenty_questions import run as questions_game
from .describe_images import run as describe_game
from .description import run as description_game
from .storytelling import run as storytelling_game

@inlineCallbacks
def run_games(s: SessionWrapper):
    yield s.say("Great! Now let's play a language game together."
    )

    if s.language_level == 1:
        yield s.say("level 1 let's go"
        )
        # yield describe)image_game(s)

    elif s.language_level == 2:
        # twenty questions game where the robot thinks of a word and the child says yes
        # yield questions_game(s)
        pass

    elif s.language_level == 3:
        yield description_game(s)

    else:
        yield storytelling_game(s)
