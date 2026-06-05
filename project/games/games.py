from session import SessionWrapper
from twisted.internet.defer import inlineCallbacks

# probably change
from .twenty_questions import run as questions_game
from .describe_images import run as describe_game
from .description import run as description_game
from .storytelling import run as storytelling_game

@inlineCallbacks
def run_games(s: SessionWrapper):
    # yield s.session.call(     #TODO remove this?
    #     "rie.dialogue.say_animated",
    #     text="Great! Now let's play a language game together."
    # )

    # 1 is the hardest, 4 is the easiest
    s.language_level = 3

    if s.language_level == 1:
        yield s.say("level 1 let's go"
        )
        # yield describe)image_game(s)

    elif s.language_level == 2:
        yield s.say("level 2 let's go")
        # yield questions_game(s)
        pass

    elif s.language_level == 3:
        yield description_game(s)

    else:
        yield s.say("level 4 let's go")
        # yield storytelling_game(s)
