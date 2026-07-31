"""Direct raw-HID input path for the Sony DualSense (PS5 controller), USB mode.

Why this exists instead of going through SDL2 (control/input_adapter.py):
on this dev machine, SDL2's HIDAPI-based PS5 joystick driver (as bundled by
the `pysdl2-dll` wheel) enumerates the device and reports its name
correctly, but its analog-state polling stops updating after the very first
read -- reproduced with SDL_JoystickUpdate() and with SDL's event queue
drained via SDL_PollEvent(). The third-party `pydualsense` library was also
tried and rejected: its parsed stick values didn't match the sane, stable
resting-state values this module's own raw-HID reads consistently produced.
Talking to the device directly via `hidapi` (the `hidapi` PyPI package,
imported as `hid`) reads correctly and continuously, so that's what this
module does.

Byte layout below is for the USB (wired) basic input report (report ID
0x01, 64 bytes) and was confirmed empirically against this hardware, not
just transcribed from docs: resting-state reads consistently produced
sane centered values (~128-133 for each stick axis, 0 for both triggers).
Button bits were NOT independently verified this session (attempts to
correlate a specific button press with a specific bit were inconclusive,
most likely a timing/coordination artifact of testing interactively rather
than a parsing bug) -- only steering/throttle/brake are implemented here.
Bluetooth mode uses a different report (0x31) and isn't handled by this
module.
"""

import hid

from config import CONFIG
from control.schema import ControlFrame

SONY_VENDOR_ID = 0x054C
DUALSENSE_PRODUCT_ID = 0x0CE6

_AXIS_CENTER = 128
_AXIS_SCALE = 127.0


def _center(raw_byte: int, deadzone: float) -> float:
    value = (raw_byte - _AXIS_CENTER) / _AXIS_SCALE
    if abs(value) < deadzone:
        return 0.0
    return max(-1.0, min(1.0, value))


def parse_report(report: bytes) -> ControlFrame:
    """Pure parsing function, kept separate from the HID I/O so it's unit-testable
    without a physical controller (see tests/test_dualsense_hid.py)."""
    deadzone = CONFIG.control.deadzone
    return ControlFrame(
        steering=_center(report[1], deadzone),
        throttle=report[6] / 255.0,
        brake=report[5] / 255.0,
    )


class DualSenseHidAdapter:
    def __init__(self):
        self._dev = hid.device()
        self._dev.open(SONY_VENDOR_ID, DUALSENSE_PRODUCT_ID)
        self._dev.set_nonblocking(True)

    def read(self) -> ControlFrame:
        report = self._latest_report()
        if report is None:
            return ControlFrame(steering=0.0, throttle=0.0, brake=0.0)
        return parse_report(report)

    def _latest_report(self):
        """Drain everything the OS has buffered and return only the newest
        report -- the device streams ~250 reports/sec; reading one-at-a-time
        without draining falls further behind real time on every call."""
        newest = None
        while True:
            report = self._dev.read(64)
            if not report:
                break
            newest = report
        return newest

    def close(self):
        self._dev.close()


def is_dualsense_connected() -> bool:
    return any(
        d["vendor_id"] == SONY_VENDOR_ID and d["product_id"] == DUALSENSE_PRODUCT_ID
        for d in hid.enumerate()
    )
