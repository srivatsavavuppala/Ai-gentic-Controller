"""Run this to sanity-check the bridge once TMInterface is running with
ApexMindBridge.as loaded and a race is live:

    python -m trackmania.live_test

Prints incoming telemetry for a few seconds -- confirms the plugin is
listening, the connection handshake works, and the wire format decodes
correctly, before wiring this into any real driving logic.
"""

import time

from trackmania.bridge_client import TrackmaniaBridge


def main():
    print("Connecting to ApexMindBridge.as on 127.0.0.1:9000 ...")
    bridge = TrackmaniaBridge()
    print("Connected. Drive a lap -- printing telemetry for 10 seconds.\n")

    end = time.time() + 10.0
    try:
        while time.time() < end:
            state = bridge.read_state()
            print(
                f"pos=({state.pos_x:7.2f}, {state.pos_y:7.2f}, {state.pos_z:7.2f}) "
                f"speed={state.speed:6.1f} race_time={state.race_time_ms}ms",
                flush=True,
            )
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
