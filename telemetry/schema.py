"""Game-agnostic telemetry frame.

Every game-specific reader (telemetry/readers/*.py) normalizes its native
format into this shape, so everything downstream (storage, agents, RL env)
never has to know which game produced the data.
"""

from dataclasses import dataclass


@dataclass
class TelemetryFrame:
    timestamp: float
    session_id: str
    lap_number: int
    lap_time_ms: int
    last_lap_time_ms: int
    best_lap_time_ms: int

    speed_kmh: float
    rpm: float
    gear: int

    throttle: float
    brake: float
    steer_angle: float

    pos_x: float
    pos_y: float
    pos_z: float
    normalized_car_position: float

    tyre_core_temp: tuple[float, float, float, float]
    fuel: float

    is_in_pit: bool
    is_off_track: bool
