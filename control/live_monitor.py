"""Run this yourself, at your own pace, to watch live values:

    python -m control.live_monitor

Exists because verifying live analog tracking over a back-and-forth chat
turned out to be unreliable (the round trip of "I say move it now" -> a
tool call runs -> you physically react is too slow and unsynchronized to
catch real movement reliably). Running this directly, you control the
timing yourself. Ctrl+C to stop.
"""

import time

from control.dualsense_hid import DualSenseHidAdapter, is_dualsense_connected


def main():
    if not is_dualsense_connected():
        print("No DualSense detected. Plug one in via USB and try again.")
        return

    adapter = DualSenseHidAdapter()
    print("Move the left stick and squeeze the triggers. Ctrl+C to stop.\n", flush=True)
    try:
        while True:
            frame = adapter.read()
            print(
                f"steering={frame.steering:+.2f}  throttle={frame.throttle:.2f}  "
                f"brake={frame.brake:.2f}",
                end="\r",
                flush=True,
            )
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
