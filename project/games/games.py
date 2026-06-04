from session import SessionWrapper
from twisted.internet.defer import inlineCallbacks

# probably change
from 20questions import run as questions_game
from describe_images import run as describe_game
from description import run as description_game
from storytelling import run as storytelling_game

@inlineCallbacks
def run_games(s: SessionWrapper):
    yield s.session.call(
        "rie.dialogue.say_animated",
        text="Great! Now let's play a language game together."
    )

    if s.language_level == 1:
        yield questions_game(s)

    elif s.language_level == 2:
        yield describe_game(s)

    elif s.language_level == 3:
        yield description_game(s)

    else:
        yield storytelling_game(s)