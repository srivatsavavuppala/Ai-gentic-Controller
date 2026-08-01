"""Sanity-check that control input actually reaches the car:

    python -m trackmania.control_test

Sends a fixed sequence of steer/gas commands and holds each for a couple
seconds -- watch the car on screen to confirm it responds (wheels turn,
car accelerates) rather than checking telemetry, since our telemetry frame
doesn't include wheel angle or input echo.
"""

import time

from control.schema import ControlFrame
from trackmania.bridge_client import TrackmaniaBridge

SEQUENCE = [
    ("steer full right, no throttle", ControlFrame(steering=1.0, throttle=0.0, brake=0.0)),
    ("steer full left, no throttle", ControlFrame(steering=-1.0, throttle=0.0, brake=0.0)),
    ("center steering, full throttle", ControlFrame(steering=0.0, throttle=1.0, brake=0.0)),
    ("center steering, full brake", ControlFrame(steering=0.0, throttle=0.0, brake=1.0)),
    ("release everything", ControlFrame(steering=0.0, throttle=0.0, brake=0.0)),
]


def main():
    print("Connecting to ApexMindBridge.as on 127.0.0.1:9000 ...")
    bridge = TrackmaniaBridge()
    print("Connected.\n")

    try:
        for label, frame in SEQUENCE:
            print(f"Sending: {label} (steering={frame.steering}, throttle={frame.throttle}, brake={frame.brake})")
            end = time.time() + 3.0
            while time.time() < end:
                bridge.send_control(frame)
                bridge.read_state()  # drain telemetry so the socket buffer doesn't back up
                time.sleep(0.02)
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
