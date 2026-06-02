import cv2
import numpy as np


def show_camera_stream(frame):
    """
    Display the robot's camera stream (Msgpack)
    This function is the exact same as in alpha_mini_rug's show_camera_stream,
    but it actually works.

    Args:
        frame (dictionary):
            The frame dictionary from the robot's camera stream
    Returns:
        None
    """
    # check if the frame is not empty
    if frame is None:
        raise ValueError("The frame is empty")
    # check if the frame is a dictionary
    if not isinstance(frame, dict):
        raise TypeError("The frame is not a dictionary")

    frame_single = frame["data"]["body.head.eyes"]

    # Convert the raw bytes to a numpy array
    nparr = np.frombuffer(frame_single, np.uint8)

    # Decode the numpy array into an image
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Display the image
    cv2.imshow("Camera Stream", image)
    cv2.waitKey(1)
    # yield sleep(0.2)
    pass
