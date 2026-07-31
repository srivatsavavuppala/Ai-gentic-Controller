"""Virtual controller output -- how the Driving Policy's decisions reach the
game. Creates a virtual Xbox 360 pad via ViGEmBus, so from the game's point
of view the AI is indistinguishable from a person holding a controller. This
is also what makes human/AI hand-off cheap: both write the same ControlFrame
shape to the same kind of device.

Requires the ViGEmBus driver installed on Windows (a one-time, one-click
installer bundled with the `vgamepad` package -- run manually, not something
this codebase installs silently, since it's a system driver):
https://github.com/ViGEm/ViGEmBus/releases
"""

import vgamepad as vg

from control.schema import ControlFrame


class VirtualControllerOutput:
    def __init__(self):
        self._pad = vg.VX360Gamepad()

    def write(self, frame: ControlFrame) -> None:
        self._pad.left_joystick_float(x_value_float=frame.steering, y_value_float=0.0)
        self._pad.right_trigger_float(value_float=max(0.0, frame.throttle))
        self._pad.left_trigger_float(value_float=max(0.0, frame.brake))

        if frame.gear_up:
            self._pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)
        else:
            self._pad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER)

        if frame.gear_down:
            self._pad.press_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)
        else:
            self._pad.release_button(button=vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER)

        self._pad.update()

    def reset(self) -> None:
        self._pad.reset()
        self._pad.update()
