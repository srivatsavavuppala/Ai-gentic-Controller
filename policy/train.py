"""Train a first Driving Policy on the fast custom simulator.

    python -m policy.train --timesteps 100000

This is deliberately the simplest thing that could work: PPO from
stable-baselines3 on a vectorized RacingEnv. Getting a policy that
completes laps without crashing is the Phase 2 milestone -- reward
shaping, richer observations, and algorithm choice are all fair game to
revisit once this loop is proven out (that's Phase 5's job: Experiment
Manager + Evaluation Agent comparing variants against this baseline).
"""

import argparse
import time
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env

from sim_env.racing_env import RacingEnv

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


class LapProgressCallback(BaseCallback):
    """Prints mean episode reward and lap-completion rate periodically, so a
    training run's progress is visible without digging into SB3's logger."""

    def __init__(self, print_every: int = 5_000):
        super().__init__()
        self.print_every = print_every
        self._last_print = 0
        self._completed_laps = 0
        self._finished_episodes = 0
        self._start_time = time.time()

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            if info.get("lap_completed"):
                self._completed_laps += 1
        for done in self.locals.get("dones", []):
            if done:
                self._finished_episodes += 1

        if self.num_timesteps - self._last_print >= self.print_every:
            self._last_print = self.num_timesteps
            rate = self._completed_laps / max(1, self._finished_episodes)
            elapsed = time.time() - self._start_time
            steps_per_sec = self.num_timesteps / elapsed
            remaining = (self.locals["total_timesteps"] - self.num_timesteps) / steps_per_sec
            print(
                f"[{self.num_timesteps}/{self.locals['total_timesteps']} steps, "
                f"{steps_per_sec:.0f} steps/sec, ~{remaining/60:.1f} min remaining] "
                f"episodes={self._finished_episodes} laps_completed={self._completed_laps} "
                f"lap_completion_rate={rate:.2%}",
                flush=True,
            )
        return True


def train(total_timesteps: int, n_envs: int, save_path: Path) -> PPO:
    vec_env = make_vec_env(RacingEnv, n_envs=n_envs)
    model = PPO("MlpPolicy", vec_env, verbose=0)
    model.learn(total_timesteps=total_timesteps, callback=LapProgressCallback())

    save_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(save_path)
    print(f"saved checkpoint to {save_path}")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--save-path", type=Path, default=CHECKPOINT_DIR / "ppo_baseline")
    args = parser.parse_args()

    train(args.timesteps, args.n_envs, args.save_path)
