import os

import cv2
from autobahn.twisted.component import Component, run
from autobahn.twisted.util import sleep
from dotenv import load_dotenv
from twisted.internet.defer import inlineCallbacks

from utils import show_camera_stream

load_dotenv()
realm = os.environ.get("REALM")


@inlineCallbacks
def main(session, details):
    yield session.call("rom.optional.behavior.play", name="BlocklyStand")

    # Subscribe to the camera stream
    yield session.subscribe(show_camera_stream, "rom.sensor.sight.stream")
    yield session.call("rom.sensor.sight.stream")

    yield sleep(30)  # Show the camera stream for 1 minute

    cv2.destroyAllWindows()
    yield session.call("rom.sensor.sight.close")
    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    session.leave()


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
