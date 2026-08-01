"""A deliberately dumb driver, no training involved: full throttle, no
steering. It has zero notion of the track's shape, so expect it to crash
at the first real corner -- the point isn't to drive well, it's to prove
the whole read-telemetry -> decide -> send-control -> auto-respawn loop
runs live and continuously, before investing in real training.

    python -m trackmania.heuristic_driver

Auto-detects a stall (speed near zero for a bit while the race clock is
running) and sends a reset, so it keeps attempting laps unattended.
"""

import time

from control.schema import ControlFrame
from trackmania.bridge_client import TrackmaniaBridge

STALL_SPEED_THRESHOLD = 5.0  # km/h
STALL_DURATION_S = 2.0
DRIVE_FRAME = ControlFrame(steering=0.0, throttle=1.0, brake=0.0)


def main():
    print("Connecting to ApexMindBridge.as on 127.0.0.1:9000 ...", flush=True)
    bridge = TrackmaniaBridge()
    print("Connected. Driving full-throttle, straight, forever -- Ctrl+C to stop.\n", flush=True)

    attempt = 1
    best_time_ms = 0
    stall_since = None

    try:
        while True:
            state = bridge.read_state()
            bridge.send_control(DRIVE_FRAME)

            if state.race_time_ms > 0:
                best_time_ms = max(best_time_ms, state.race_time_ms)

            if state.speed < STALL_SPEED_THRESHOLD and state.race_time_ms > 500:
                stall_since = stall_since or time.time()
                if time.time() - stall_since > STALL_DURATION_S:
                    print(
                        f"attempt {attempt}: stalled/crashed at race_time={state.race_time_ms}ms "
                        f"(best so far: {best_time_ms}ms) -- resetting",
                        flush=True,
                    )
                    bridge.send_reset()
                    attempt += 1
                    stall_since = None
                    time.sleep(1.0)  # let the respawn settle before reading state again
            else:
                stall_since = None
    except KeyboardInterrupt:
        print(f"\nStopped after {attempt} attempts. Best race_time reached: {best_time_ms}ms", flush=True)
    finally:
        bridge.close()


if __name__ == "__main__":
    main()
