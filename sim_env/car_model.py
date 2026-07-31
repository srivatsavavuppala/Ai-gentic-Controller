"""Kinematic bicycle model -- the car dynamics for the fast training sim.

Deliberately simple (no tire slip, no weight transfer, no suspension) since
Phase 2's job is proving the RL training loop works end-to-end, not
physical realism. Swap in a richer model later without changing
racing_env.py's interface if fidelity turns out to matter for sim-to-game
transfer (Phase 3).
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class CarParams:
    wheelbase: float = 2.5  # meters
    max_steering_angle: float = 0.6  # radians (~34 degrees)
    max_speed: float = 60.0  # m/s (~216 km/h)
    max_accel: float = 8.0  # m/s^2
    max_brake_decel: float = 12.0  # m/s^2
    drag_coefficient: float = 0.02  # simple v^2 drag term, caps top speed


@dataclass
class CarState:
    x: float
    y: float
    yaw: float  # radians
    speed: float  # m/s, always >= 0


def step(state: CarState, steering: float, throttle: float, brake: float, dt: float, params: CarParams) -> CarState:
    """steering/throttle/brake follow control.schema.ControlFrame's ranges:
    steering in [-1, 1], throttle/brake in [0, 1]."""
    steering = np.clip(steering, -1.0, 1.0) * params.max_steering_angle
    throttle = np.clip(throttle, 0.0, 1.0)
    brake = np.clip(brake, 0.0, 1.0)

    accel = throttle * params.max_accel - brake * params.max_brake_decel
    accel -= params.drag_coefficient * state.speed**2

    new_speed = float(np.clip(state.speed + accel * dt, 0.0, params.max_speed))
    new_yaw = state.yaw + (new_speed / params.wheelbase) * np.tan(steering) * dt
    new_x = state.x + new_speed * np.cos(new_yaw) * dt
    new_y = state.y + new_speed * np.sin(new_yaw) * dt

    return CarState(x=new_x, y=new_y, yaw=new_yaw, speed=new_speed)
