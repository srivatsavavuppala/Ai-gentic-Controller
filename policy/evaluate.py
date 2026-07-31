"""Deterministic evaluation of a saved checkpoint over N episodes -- a
rigorous number to report, distinct from the rolling window training uses
to decide when to stop (which is noisier and non-deterministic).

    python -m policy.evaluate policy/checkpoints/ppo_baseline --episodes 100
"""

import argparse
from pathlib import Path

from stable_baselines3 import PPO

from sim_env.racing_env import RacingEnv


def evaluate(model_path: Path, episodes: int):
    model = PPO.load(model_path)
    env = RacingEnv()

    completed = 0
    rewards = []
    lap_steps = []
    for _ in range(episodes):
        obs, _ = env.reset()
        total_reward = 0.0
        for step in range(env.max_steps):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            if terminated or truncated:
                if info.get("lap_completed"):
                    completed += 1
                    lap_steps.append(step + 1)
                break
        rewards.append(total_reward)

    return {
        "episodes": episodes,
        "completed": completed,
        "completion_rate": completed / episodes,
        "mean_reward": sum(rewards) / len(rewards),
        "mean_lap_time_s": (sum(lap_steps) / len(lap_steps) * env.dt) if lap_steps else None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path", type=Path)
    parser.add_argument("--episodes", type=int, default=100)
    args = parser.parse_args()

    results = evaluate(args.model_path, args.episodes)
    print(
        f"completion_rate={results['completion_rate']:.1%} "
        f"({results['completed']}/{results['episodes']}) "
        f"mean_reward={results['mean_reward']:.1f} "
        f"mean_lap_time={results['mean_lap_time_s']}"
    )
