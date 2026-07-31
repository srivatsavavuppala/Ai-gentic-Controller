import numpy as np

from sim_env.racing_env import RacingEnv


def test_reset_returns_valid_observation():
    env = RacingEnv()
    obs, _info = env.reset()
    assert env.observation_space.contains(obs)


def test_driving_straight_ahead_gains_positive_reward():
    env = RacingEnv()
    env.reset()
    total_reward = 0.0
    for _ in range(50):
        _obs, reward, terminated, truncated, _info = env.step(np.array([0.0, 1.0, 0.0]))
        total_reward += reward
        if terminated or truncated:
            break
    assert total_reward > 0


def test_driving_hard_left_immediately_goes_off_track_and_terminates():
    env = RacingEnv()
    env.reset()
    terminated = False
    for _ in range(200):
        _obs, _reward, terminated, _truncated, _info = env.step(np.array([1.0, 1.0, 0.0]))
        if terminated:
            break
    assert terminated


def test_episode_truncates_at_max_steps_if_never_terminated():
    env = RacingEnv(max_steps=10)
    env.reset()
    truncated = False
    for _ in range(10):
        _obs, _reward, terminated, truncated, _info = env.step(np.array([0.0, 0.0, 0.0]))
        if terminated:
            break
    assert truncated
