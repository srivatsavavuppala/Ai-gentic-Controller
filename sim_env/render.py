"""Visualize a trained Driving Policy's lap on the fast training track.

Not part of the training loop (which stays render-free on purpose, for
speed) -- this is purely a human sanity-check tool, run on demand:

    python -m sim_env.render policy/checkpoints/ppo_baseline
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from stable_baselines3 import PPO

from sim_env.racing_env import RacingEnv
from sim_env.track import Track


def run_episode(model: PPO, env: RacingEnv):
    obs, _ = env.reset()
    positions = [(env.state.x, env.state.y, env.state.speed)]
    info = {}
    for _ in range(env.max_steps):
        action, _ = model.predict(obs, deterministic=True)
        obs, _reward, terminated, truncated, info = env.step(action)
        positions.append((env.state.x, env.state.y, env.state.speed))
        if terminated or truncated:
            break
    return positions, info


def _track_boundaries(track: Track):
    normals = np.stack([-track.segment_dirs[:, 1], track.segment_dirs[:, 0]], axis=1)
    outer = track.centerline + normals * (track.width / 2)
    inner = track.centerline - normals * (track.width / 2)
    return np.vstack([outer, outer[0]]), np.vstack([inner, inner[0]])


def plot_lap(track: Track, positions, save_path: Path, info=None):
    outer, inner = _track_boundaries(track)
    xs = [p[0] for p in positions]
    ys = [p[1] for p in positions]
    speeds = [p[2] for p in positions]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(outer[:, 0], outer[:, 1], color="black", linewidth=1)
    ax.plot(inner[:, 0], inner[:, 1], color="black", linewidth=1)
    ax.fill(outer[:, 0], outer[:, 1], color="#dddddd", zorder=0)
    ax.fill(inner[:, 0], inner[:, 1], color="white", zorder=1)

    scatter = ax.scatter(xs, ys, c=speeds, cmap="viridis", s=6, zorder=2)
    ax.scatter([xs[0]], [ys[0]], color="red", marker="x", s=100, label="start", zorder=3)
    fig.colorbar(scatter, ax=ax, label="speed (m/s)")

    title = "Trained policy lap"
    if info is not None:
        title += f" -- lap_completed={info.get('lap_completed', False)}"
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.legend()

    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    print(f"saved to {save_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path", type=Path)
    parser.add_argument("--save-path", type=Path, default=Path("experiments/runs/lap.png"))
    args = parser.parse_args()

    model = PPO.load(args.model_path)
    env = RacingEnv()
    trajectory, episode_info = run_episode(model, env)
    plot_lap(env.track, trajectory, args.save_path, episode_info)
