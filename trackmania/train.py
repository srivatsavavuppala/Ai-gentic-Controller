"""Train a Driving Policy against the LIVE TrackMania game (not a fast
simulator) -- same PPO approach as policy/train.py, but a single env since
there's only one game instance, no vectorization possible.

    python -m trackmania.train --timesteps 50000

Requires TMInterface running with ApexMindBridge.as loaded and a live race
(see trackmania/README.md).
"""

import argparse
import time
from collections import deque
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor

from trackmania.env import TrackmaniaEnv

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


class ProgressCallback(BaseCallback):
    """No lap-completion concept here (no track geometry, no checkpoints in
    our telemetry) -- reports rolling episode reward (distance covered) and
    best race_time_ms reached instead."""

    def __init__(self, print_every: int = 1_000, window: int = 20, save_path: Path | None = None, save_every: int = 5_000):
        super().__init__()
        self.print_every = print_every
        self.save_path = save_path
        self.save_every = save_every
        self._last_print = 0
        self._last_save = 0
        self._episode_rewards = deque(maxlen=window)
        self._finished_episodes = 0
        self._best_race_time_ms = 0
        self._start_time = time.time()
        self._start_num_timesteps = 0

    def _on_training_start(self) -> None:
        self._start_num_timesteps = self.num_timesteps

    def _on_step(self) -> bool:
        for info, done in zip(self.locals.get("infos", []), self.locals.get("dones", [])):
            self._best_race_time_ms = max(self._best_race_time_ms, info.get("race_time_ms", 0))
            if done and "episode" in info:
                self._finished_episodes += 1
                self._episode_rewards.append(info["episode"]["r"])

        if self.num_timesteps - self._last_print >= self.print_every:
            self._last_print = self.num_timesteps
            elapsed = time.time() - self._start_time
            new_steps = self.num_timesteps - self._start_num_timesteps
            steps_per_sec = new_steps / max(elapsed, 1e-6)
            mean_reward = sum(self._episode_rewards) / len(self._episode_rewards) if self._episode_rewards else 0.0
            print(
                f"[{self.num_timesteps} steps, {steps_per_sec:.1f} steps/sec] "
                f"episodes={self._finished_episodes} "
                f"mean_reward(last {len(self._episode_rewards)})={mean_reward:.1f} "
                f"best_race_time={self._best_race_time_ms}ms",
                flush=True,
            )

        if self.save_path is not None and self.num_timesteps - self._last_save >= self.save_every:
            self._last_save = self.num_timesteps
            self.model.save(self.save_path)
            print(f"[{self.num_timesteps} steps] checkpoint saved to {self.save_path}", flush=True)
        return True


def train(total_timesteps: int, save_path: Path, resume_from: Path | None = None) -> PPO:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    # Monitor wraps the env to populate info["episode"] on done, which
    # ProgressCallback relies on -- PPO doesn't add this automatically for a
    # plain (non-vectorized) env the way make_vec_env does for Phase 2.
    env = Monitor(TrackmaniaEnv())
    if resume_from is not None:
        model = PPO.load(resume_from, env=env)
        print(f"resumed from {resume_from} at {model.num_timesteps} prior steps", flush=True)
    else:
        model = PPO("MlpPolicy", env, verbose=0)

    model.learn(
        total_timesteps=total_timesteps,
        callback=ProgressCallback(save_path=save_path),
        reset_num_timesteps=(resume_from is None),
    )

    model.save(save_path)
    print(f"saved checkpoint to {save_path}", flush=True)
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=50_000)
    parser.add_argument("--save-path", type=Path, default=CHECKPOINT_DIR / "trackmania_ppo")
    parser.add_argument("--resume-from", type=Path, default=None)
    args = parser.parse_args()

    train(args.timesteps, args.save_path, args.resume_from)
