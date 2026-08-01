"""Isolated test: send ONLY a fixed positive gas value, nothing else, for a
few seconds, to unambiguously determine whether positive gas means forward
or reverse in TrackMania's InputType::Gas convention.

    python -m trackmania.gas_direction_test
"""

import struct
import time

from trackmania.bridge_client import _CONTROL_FORMAT, TrackmaniaBridge

GAS_VALUE = 32768  # half throttle, positive


def main():
    print("Connecting...", flush=True)
    bridge = TrackmaniaBridge()
    print(f"Connected. Sending ONLY gas={GAS_VALUE}, steer=0, for 5 seconds. Watch the car.", flush=True)

    end = time.time() + 5.0
    try:
        while time.time() < end:
            bridge.read_state()
            bridge._sock.sendall(struct.pack(_CONTROL_FORMAT, 0, GAS_VALUE, 0))
    finally:
        bridge.close()
    print("Done.", flush=True)


if __name__ == "__main__":
    main()
