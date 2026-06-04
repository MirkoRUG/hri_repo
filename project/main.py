import os
import logging

from autobahn.twisted.component import Component, run
from dotenv import load_dotenv
from twisted.internet.defer import inlineCallbacks

from conversations import *
from session import SessionWrapper
from games import run_games

load_dotenv()
logging.basicConfig(level=logging.INFO)
realm  = os.environ["REALM"]


@inlineCallbacks
def main(session, details):
    """driver code.

    Models one full session between the robot and a human, consisting of the following:
        1) pleasantries; the goal of which is to get the human comfortable
        2) a number of language learning games; the difficulty and number of games is personalized to each human
        3) wrap-up, consisting of final encouragement and, depending on the age of the human, more/less in-depth reflection on progress.
    """
    # setup
    manager = SessionWrapper(session, "alex")

    # conversational flow
    yield pleasantries(manager)
    yield run_games (manager)
    yield wrapup(manager)


wamp = Component(
    transports=[
        {
            "url": "wss://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"],
            "max_retries": 0,
        }
    ],
    realm=realm,
)
wamp.on_join(main)


if __name__ == "__main__":
    run([wamp])

