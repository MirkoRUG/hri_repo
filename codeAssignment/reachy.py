import time

from reachy_mini import ReachyMini

mini = ReachyMini(
    connection_mode="network", host="192.168.1.19", media_backend="no_media"
)
print("Successfully connected!")

mini.goto_target(antennas=[0.5, -0.5], duration=0.5)
time.sleep(0.75)  # wait for motion to complete
mini.goto_target(antennas=[-0.5, 0.5], duration=0.5)
time.sleep(0.75)
mini.goto_target(antennas=[0, 0], duration=0.5)
time.sleep(0.75)

# https://huggingface.co/docs/reachy_mini/SDK/quickstart
