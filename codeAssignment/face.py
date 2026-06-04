import os

import cv2
import numpy as np
from autobahn.twisted.component import Component, run
from autobahn.twisted.util import sleep
from deepface import DeepFace
from dotenv import load_dotenv
from twisted.internet.defer import inlineCallbacks

load_dotenv()
realm = os.environ.get("REALM")

# Analyse emotion every N frames (1 = every frame, 5 = every 5th frame, etc.)
EMOTION_FRAME_SKIP = 15

frame_counter = 0
last_emotion = None


def analyse_camera_stream(frame):
    global frame_counter, last_emotion

    if frame is None or not isinstance(frame, dict):
        return

    raw = frame["data"]["body.head.eyes"]
    nparr = np.frombuffer(raw, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    frame_counter += 1
    if frame_counter % EMOTION_FRAME_SKIP == 0:
        try:
            result = DeepFace.analyze(image, actions=["emotion"], enforce_detection=True)
            dominant = result[0]["dominant_emotion"]
            confidence = result[0]["emotion"][dominant]
            if confidence >= 70:
                last_emotion = dominant
                print(f"Detected emotion: {last_emotion} ({confidence:.1f}%)")
        except Exception as e:
            print(f"DeepFace error: {e}")

    if last_emotion:
        cv2.putText(image, last_emotion, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Camera Stream", image)
    cv2.waitKey(1)


@inlineCallbacks
def main(session, details):
    yield session.call("rom.optional.behavior.play", name="BlocklyStand")

    yield session.subscribe(analyse_camera_stream, "rom.sensor.sight.stream")
    yield session.call("rom.sensor.sight.stream")

    yield sleep(60)

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
