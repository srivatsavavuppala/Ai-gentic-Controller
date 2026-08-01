"""Gymnasium environment wrapping the live TrackMania bridge -- same shape
as sim_env/racing_env.py, but stepping the real game instead of our fake
physics. No track geometry available here (no centerline, no checkpoints
in our telemetry), so the observation is raw position + velocity + speed.
That's only sound because this is always the *same fixed track* every
episode -- the policy isn't being asked to generalize across tracks, just
to learn this one course through repetition, the same way the heuristic
driver always meets the same wall at the same point.

Only one live game instance exists, so there's no vectorization here the
way Phase 2's fast simulator had 8 parallel envs -- training throughput is
bounded by the game's own physics tick rate (~100Hz observed), not by us.
"""

from typing import ClassVar

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from control.schema import ControlFrame
from trackmania.bridge_client import TrackmaniaBridge

STALL_SPEED_THRESHOLD = 5.0  # km/h
STALL_DURATION_STEPS = 200  # ~2s at ~100Hz
RESPAWN_SETTLE_STEPS = 30  # drain stale telemetry after a reset before resuming

# A first live training run (2026-08-01) confirmed a real reward flaw: pure
# distance-moved reward with no time cost let the policy earn MORE total
# episode reward by crawling just above the stall threshold for a long time
# than by driving fast and eventually crashing (mean_reward fell from ~94
# to ~59 over 20 episodes while best_race_time froze, then never recovered
# with more training -- a converged degenerate strategy, not noise). The
# per-step time penalty below makes "survive slowly" net-negative while
# leaving genuine fast driving net-positive.
TIME_PENALTY_PER_MS = 0.01
MAX_DT_MS = 50  # cap so our own processing lag (e.g. a slow PPO gradient
# update between rollouts) doesn't get misattributed to the policy as an
# unfairly large time penalty for a gap it didn't cause


class TrackmaniaEnv(gym.Env):
    metadata: ClassVar[dict] = {"render_modes": []}

    def __init__(self, bridge: TrackmaniaBridge = None, max_steps: int = 3000):
        super().__init__()
        self.bridge = bridge or TrackmaniaBridge()
        self.max_steps = max_steps

        # [steering, throttle, brake] -- matches control.schema.ControlFrame's ranges
        self.action_space = spaces.Box(
            low=np.array([-1.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0], dtype=np.float32),
        )
        # [velX, velY, velZ, speed, posX, posY, posZ]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(7,), dtype=np.float32)

        self._steps = 0
        self._stall_steps = 0
        self._prev_pos = None
        self._prev_race_time_ms = None

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.bridge.send_reset()
        state = None
        for _ in range(RESPAWN_SETTLE_STEPS):
            state = self.bridge.read_state()
        self._steps = 0
        self._stall_steps = 0
        self._prev_pos = np.array([state.pos_x, state.pos_y, state.pos_z])
        self._prev_race_time_ms = state.race_time_ms
        return self._observe(state), {}

    def step(self, action):
        steering, throttle, brake = (float(a) for a in action)
        self.bridge.send_control(ControlFrame(steering=steering, throttle=throttle, brake=brake))
        state = self.bridge.read_state()
        self._steps += 1

        pos = np.array([state.pos_x, state.pos_y, state.pos_z])
        distance_moved = float(np.linalg.norm(pos - self._prev_pos))
        self._prev_pos = pos

        dt_ms = max(0, min(state.race_time_ms - self._prev_race_time_ms, MAX_DT_MS))
        self._prev_race_time_ms = state.race_time_ms
        reward = distance_moved - TIME_PENALTY_PER_MS * dt_ms

        if state.speed < STALL_SPEED_THRESHOLD and state.race_time_ms > 500:
            self._stall_steps += 1
        else:
            self._stall_steps = 0

        terminated = self._stall_steps >= STALL_DURATION_STEPS
        truncated = self._steps >= self.max_steps
        if terminated:
            reward -= 5.0

        return self._observe(state), reward, terminated, truncated, {"race_time_ms": state.race_time_ms}

    @staticmethod
    def _observe(state):
        return np.array(
            [
                state.vel_x,
                state.vel_y,
                state.vel_z,
                state.speed,
                state.pos_x,
                state.pos_y,
                state.pos_z,
            ],
            dtype=np.float32,
        )

    def close(self):
        self.bridge.close()
