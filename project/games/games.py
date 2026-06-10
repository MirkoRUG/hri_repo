from session import SessionWrapper
from twisted.internet.defer import inlineCallbacks
import settings
import logging

# probably change
from .twenty_questions import run as questions_game
from .describe_images import run as image_game
from .description import run as description_game
from .storytelling import run as storytelling_game

@inlineCallbacks
def run_games(s: SessionWrapper):

    if s.language_level == 1:
        yield questions_game(s)

    elif s.language_level == 2:
        yield description_game(s)

    elif s.language_level == 3:
        yield image_game(s)

    else:
        yield storytelling_game(s)
