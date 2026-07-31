"""Shared control-frame shape used by both the human input adapter and the
AI's virtual-controller output, so the rest of the system (and the Driving
Policy) never has to know whether a frame came from a person or a policy.
"""

from dataclasses import dataclass


@dataclass
class ControlFrame:
    steering: float  # -1.0 (full left) .. 1.0 (full right)
    throttle: float  # 0.0 .. 1.0
    brake: float  # 0.0 .. 1.0
    clutch: float = 0.0  # 0.0 .. 1.0
    gear_up: bool = False
    gear_down: bool = False
