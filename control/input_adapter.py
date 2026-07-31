"""Universal controller input via SDL2.

Two paths, because "any controller" splits into two real categories:

1. Gamepads SDL2 already knows how to map semantically (Xbox pads, PS4/PS5
   DualShock/DualSense, and anything else covered by the community-maintained
   gamecontrollerdb.txt) -- read via the GameController API, where "left
   stick X" etc. means the same thing on every device.
2. Wheels/pedals and anything else SDL2 only sees as a raw joystick with
   unlabeled axes -- read via the Joystick API, with an explicit axis-index
   mapping supplied by the caller (every wheel brand numbers its axes
   differently; there's no way around a one-time per-device config).

Drop a copy of the community gamecontrollerdb.txt at
control/gamecontrollerdb.txt (config.CONFIG.paths.gamecontrollerdb) to widen
GameController coverage -- see https://github.com/mdqinc/SDL_GameControllerDB.
"""

import sdl2

from config import CONFIG
from control.schema import ControlFrame


def _apply_deadzone(value: float, deadzone: float) -> float:
    if abs(value) < deadzone:
        return 0.0
    return value


class GamepadInputAdapter:
    """For devices SDL2 recognizes via its GameController mapping database."""

    def __init__(self, device_index: int = 0):
        sdl2.SDL_Init(sdl2.SDL_INIT_GAMECONTROLLER)
        if CONFIG.paths.gamecontrollerdb.exists():
            sdl2.SDL_GameControllerAddMappingsFromFile(
                str(CONFIG.paths.gamecontrollerdb).encode("utf-8")
            )

        if not sdl2.SDL_IsGameController(device_index):
            raise RuntimeError(
                f"Device {device_index} has no SDL2 GameController mapping; "
                "use JoystickInputAdapter with an explicit axis map instead."
            )
        self._controller = sdl2.SDL_GameControllerOpen(device_index)

    def read(self) -> ControlFrame:
        sdl2.SDL_GameControllerUpdate()
        deadzone = CONFIG.control.deadzone

        left_x = self._controller_axis(sdl2.SDL_CONTROLLER_AXIS_LEFTX)
        right_trigger = self._controller_axis(sdl2.SDL_CONTROLLER_AXIS_TRIGGERRIGHT)
        left_trigger = self._controller_axis(sdl2.SDL_CONTROLLER_AXIS_TRIGGERLEFT)

        return ControlFrame(
            steering=_apply_deadzone(left_x, deadzone),
            throttle=max(0.0, right_trigger),
            brake=max(0.0, left_trigger),
        )

    def _controller_axis(self, axis) -> float:
        raw = sdl2.SDL_GameControllerGetAxis(self._controller, axis)
        return raw / 32768.0

    def close(self):
        sdl2.SDL_GameControllerClose(self._controller)


class JoystickInputAdapter:
    """For wheels/pedals: raw joystick axes with a caller-supplied index map.

    axis_map example for a generic wheel: {"steering": 0, "throttle": 1, "brake": 2}
    """

    def __init__(self, device_index: int, axis_map: dict[str, int], invert: set[str] = frozenset()):
        sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK)
        self._joystick = sdl2.SDL_JoystickOpen(device_index)
        if not self._joystick:
            raise RuntimeError(f"Could not open joystick at device index {device_index}")
        self._axis_map = axis_map
        self._invert = invert

    def read(self) -> ControlFrame:
        sdl2.SDL_JoystickUpdate()
        deadzone = CONFIG.control.deadzone

        def axis_value(name: str, default: float = 0.0) -> float:
            if name not in self._axis_map:
                return default
            raw = sdl2.SDL_JoystickGetAxis(self._joystick, self._axis_map[name])
            value = raw / 32768.0
            return -value if name in self._invert else value

        return ControlFrame(
            steering=_apply_deadzone(axis_value("steering"), deadzone),
            throttle=max(0.0, axis_value("throttle")),
            brake=max(0.0, axis_value("brake")),
            clutch=max(0.0, axis_value("clutch")),
        )

    def close(self):
        sdl2.SDL_JoystickClose(self._joystick)


def list_devices() -> list[str]:
    """Enumerate connected controllers/wheels -- the plug-and-play smoke test."""
    sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_GAMECONTROLLER)
    count = sdl2.SDL_NumJoysticks()
    names = []
    for i in range(count):
        name = sdl2.SDL_JoystickNameForIndex(i)
        names.append(name.decode("utf-8") if name else f"Unknown device {i}")
    return names
