import os
import settings

from autobahn.twisted.component import Component, run
from dotenv import load_dotenv
from twisted.internet.defer import inlineCallbacks

from conversations import *
from session import SessionWrapper
from games.games import run_games


load_dotenv()
realm  = os.environ["REALM"]

@inlineCallbacks
def main(session, details):
    """driver code.

    Models one full session between the robot and a human, consisting of the following:
        1) pleasantries; the goal of which is to get the human comfortable
        2) a number of language learning games; the difficulty and number of games is personalized to each human
        3) wrap-up, consisting of final encouragement and goodbyes
    """

    # setup
    manager = SessionWrapper(session, "alex")
    yield manager.setup()

    # conversational flow
    # yield pleasantries(manager)

    manager.enthousiasm = 2
    manager.conversation_history = []
    yield run_games(manager)

    logging.warning("games done")
    manager.conversation_history = []
    yield wrapup(manager)
    logging.warning("wrapup done")

    yield manager.shut_down()

wamp = Component(
    transports=[
        {
            "url": "wss://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"],
            "max_retries": -1,
        }
    ],
    realm=realm,
)
wamp.on_join(main)


if __name__ == "__main__":
    settings.init()

    if settings.debug:
        print("running debug")
        main(None, None)
    else:
        run([wamp])

