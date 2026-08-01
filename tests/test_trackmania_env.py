import numpy as np

from trackmania.bridge_client import TrackmaniaState
from trackmania.env import RESPAWN_SETTLE_STEPS, STALL_DURATION_STEPS, TrackmaniaEnv


class _FakeBridge:
    """Replays a scripted sequence of states, recording what was sent --
    lets us test the env's logic without a live game."""

    def __init__(self, states):
        self._states = iter(states)
        self.controls_sent = []
        self.reset_count = 0

    def read_state(self) -> TrackmaniaState:
        return next(self._states)

    def send_control(self, frame):
        self.controls_sent.append(frame)

    def send_reset(self):
        self.reset_count += 1

    def close(self):
        pass


def _state(pos=(0.0, 0.0, 0.0), vel=(0.0, 0.0, 0.0), speed=50.0, race_time_ms=1000):
    return TrackmaniaState(
        pos_x=pos[0], pos_y=pos[1], pos_z=pos[2],
        vel_x=vel[0], vel_y=vel[1], vel_z=vel[2],
        speed=speed, race_time_ms=race_time_ms,
    )


def test_reset_drains_settle_steps_and_returns_valid_observation():
    states = [_state()] * (RESPAWN_SETTLE_STEPS + 5)
    bridge = _FakeBridge(states)
    env = TrackmaniaEnv(bridge=bridge)

    obs, _info = env.reset()

    assert bridge.reset_count == 1
    assert env.observation_space.contains(obs)


def test_step_reward_is_distance_moved():
    states = [_state(pos=(0, 0, 0))] * RESPAWN_SETTLE_STEPS + [_state(pos=(3, 4, 0), speed=50.0)]
    bridge = _FakeBridge(states)
    env = TrackmaniaEnv(bridge=bridge)
    env.reset()

    _obs, reward, terminated, truncated, _info = env.step(np.array([0.0, 1.0, 0.0]))

    assert reward == 5.0  # 3-4-5 triangle
    assert not terminated
    assert not truncated
    assert len(bridge.controls_sent) == 1


def test_stall_for_enough_steps_terminates_episode():
    settle = [_state()] * RESPAWN_SETTLE_STEPS
    stall = [_state(speed=0.0, race_time_ms=2000)] * (STALL_DURATION_STEPS + 1)
    bridge = _FakeBridge(settle + stall)
    env = TrackmaniaEnv(bridge=bridge)
    env.reset()

    terminated = False
    for _ in range(STALL_DURATION_STEPS + 1):
        _obs, _reward, terminated, _truncated, _info = env.step(np.array([0.0, 0.0, 0.0]))
        if terminated:
            break

    assert terminated


def test_truncates_at_max_steps_if_never_stalled():
    settle = [_state()] * RESPAWN_SETTLE_STEPS
    moving = [_state(pos=(i, 0, 0), speed=50.0) for i in range(20)]
    bridge = _FakeBridge(settle + moving)
    env = TrackmaniaEnv(bridge=bridge, max_steps=10)
    env.reset()

    truncated = False
    for _ in range(10):
        _obs, _reward, terminated, truncated, _info = env.step(np.array([0.0, 1.0, 0.0]))
        if terminated:
            break

    assert truncated
