"""The fast training simulator the Driving Policy actually learns on.

Deliberately not the real target sim game -- consumer racing sims only run
in real time, which makes bulk RL training on a laptop impractical (see
PROJECT_APEXMIND_PLAN.md, section 1). This runs an entire lap in a few
milliseconds, so training can iterate thousands of laps in the time one
real lap would take. A trained policy gets deployed into the real game
(Phase 3) via the same control.schema.ControlFrame the human controller
path uses.
"""

from typing import ClassVar

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from sim_env.car_model import CarParams, CarState
from sim_env.car_model import step as car_step
from sim_env.track import Track, generate_oval_track


def _wrap_to_pi(angle):
    return (angle + np.pi) % (2 * np.pi) - np.pi


class RacingEnv(gym.Env):
    metadata: ClassVar[dict] = {"render_modes": []}

    def __init__(
        self,
        track: Track = None,
        dt: float = 0.05,
        max_steps: int = 2000,
        car_params: CarParams = None,
    ):
        super().__init__()
        self.track = track or generate_oval_track()
        self.dt = dt
        self.max_steps = max_steps
        self.car_params = car_params or CarParams()

        # [steering, throttle, brake] -- matches control.schema.ControlFrame's ranges
        self.action_space = spaces.Box(
            low=np.array([-1.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0], dtype=np.float32),
        )
        # [lateral_offset_norm, heading_error, speed_norm]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(3,), dtype=np.float32)

        self._state = None
        self._steps = 0
        self._progress = 0.0
        self._total_distance = 0.0

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        start = self.track.centerline[0]
        heading = self.track.segment_headings[0]
        self._state = CarState(x=float(start[0]), y=float(start[1]), yaw=float(heading), speed=0.0)
        self._steps = 0
        self._total_distance = 0.0
        obs, progress, _, _ = self._locate_and_observe()
        self._progress = progress
        return obs, {}

    def step(self, action):
        steering, throttle, brake = (float(a) for a in action)
        self._state = car_step(self._state, steering, throttle, brake, self.dt, self.car_params)
        self._steps += 1

        obs, progress, lateral, _ = self._locate_and_observe()
        progress_delta = self._progress_delta(progress)
        self._progress = progress
        self._total_distance += progress_delta

        off_track = abs(lateral) > self.track.width / 2.0
        lap_completed = self._total_distance >= self.track.total_length

        reward = progress_delta - (5.0 if off_track else 0.0) + (100.0 if lap_completed else 0.0)
        terminated = off_track or lap_completed
        truncated = self._steps >= self.max_steps

        return obs, reward, terminated, truncated, {"progress": progress, "lap_completed": lap_completed}

    def _locate_and_observe(self):
        progress, lateral, heading, _ = self.track.locate((self._state.x, self._state.y))
        heading_error = _wrap_to_pi(heading - self._state.yaw)
        obs = np.array(
            [
                lateral / (self.track.width / 2.0),
                heading_error,
                self._state.speed / self.car_params.max_speed,
            ],
            dtype=np.float32,
        )
        return obs, progress, lateral, heading

    def _progress_delta(self, new_progress):
        delta = new_progress - self._progress
        if delta < -self.track.total_length / 2:
            delta += self.track.total_length
        elif delta > self.track.total_length / 2:
            delta -= self.track.total_length
        return delta
