"""Train (or continue training) a Driving Policy on the fast custom simulator.

    python -m policy.train --timesteps 100000
    python -m policy.train --timesteps 200000 --resume-from policy/checkpoints/ppo_baseline --target-lap-rate 0.8

This is deliberately the simplest thing that could work: PPO from
stable-baselines3 on a vectorized RacingEnv. Getting a policy that
completes laps without crashing is the Phase 2 milestone -- reward
shaping, richer observations, and algorithm choice are all fair game to
revisit once this loop is proven out (that's Phase 5's job: Experiment
Manager + Evaluation Agent comparing variants against this baseline).
"""

import argparse
import time
from collections import deque
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env

from sim_env.racing_env import RacingEnv

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


class LapProgressCallback(BaseCallback):
    """Prints progress periodically using a ROLLING window of recent episode
    outcomes, not the cumulative rate since training started -- cumulative
    rate lags behind the policy's actual current performance because it's
    dragged down by early (bad) episodes. Can also stop training early once
    the rolling rate crosses a target, so a run doesn't overshoot a goal by
    hours of unnecessary extra training."""

    def __init__(
        self,
        print_every: int = 5_000,
        window: int = 50,
        target_lap_rate: float | None = None,
        save_path: Path | None = None,
        save_every: int = 25_000,
    ):
        super().__init__()
        self.print_every = print_every
        self.target_lap_rate = target_lap_rate
        self.save_path = save_path
        self.save_every = save_every
        self._last_print = 0
        self._last_save = 0
        self._completed_laps = 0
        self._finished_episodes = 0
        self._recent_outcomes = deque(maxlen=window)
        self._start_time = time.time()

    def _on_step(self) -> bool:
        for info, done in zip(self.locals.get("infos", []), self.locals.get("dones", [])):
            if done:
                self._finished_episodes += 1
                lap_completed = bool(info.get("lap_completed"))
                self._recent_outcomes.append(lap_completed)
                if lap_completed:
                    self._completed_laps += 1

        if self.num_timesteps - self._last_print >= self.print_every:
            self._last_print = self.num_timesteps
            rolling_rate = (
                sum(self._recent_outcomes) / len(self._recent_outcomes) if self._recent_outcomes else 0.0
            )
            elapsed = time.time() - self._start_time
            steps_per_sec = self.num_timesteps / elapsed
            remaining = (self.locals["total_timesteps"] - self.num_timesteps) / steps_per_sec
            print(
                f"[{self.num_timesteps}/{self.locals['total_timesteps']} steps, "
                f"{steps_per_sec:.0f} steps/sec, ~{remaining/60:.1f} min remaining] "
                f"episodes={self._finished_episodes} "
                f"rolling_lap_rate(last {len(self._recent_outcomes)})={rolling_rate:.1%} "
                f"cumulative_lap_rate={self._completed_laps / max(1, self._finished_episodes):.1%}",
                flush=True,
            )

            if (
                self.target_lap_rate is not None
                and len(self._recent_outcomes) == self._recent_outcomes.maxlen
                and rolling_rate >= self.target_lap_rate
            ):
                print(
                    f"target lap rate {self.target_lap_rate:.0%} reached "
                    f"(rolling rate {rolling_rate:.1%}) -- stopping early",
                    flush=True,
                )
                if self.save_path is not None:
                    self.model.save(self.save_path)
                    print(f"saved checkpoint to {self.save_path}", flush=True)
                return False

        if self.save_path is not None and self.num_timesteps - self._last_save >= self.save_every:
            self._last_save = self.num_timesteps
            self.model.save(self.save_path)
            print(f"[{self.num_timesteps} steps] checkpoint saved to {self.save_path}", flush=True)
        return True


def train(
    total_timesteps: int,
    n_envs: int,
    save_path: Path,
    resume_from: Path | None = None,
    target_lap_rate: float | None = None,
) -> PPO:
    save_path.parent.mkdir(parents=True, exist_ok=True)
    vec_env = make_vec_env(RacingEnv, n_envs=n_envs)
    if resume_from is not None:
        model = PPO.load(resume_from, env=vec_env)
        print(f"resumed from {resume_from} at {model.num_timesteps} prior steps")
    else:
        model = PPO("MlpPolicy", vec_env, verbose=0)

    model.learn(
        total_timesteps=total_timesteps,
        callback=LapProgressCallback(target_lap_rate=target_lap_rate, save_path=save_path),
        reset_num_timesteps=(resume_from is None),
    )

    model.save(save_path)
    print(f"saved checkpoint to {save_path}")
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--timesteps", type=int, default=100_000)
    parser.add_argument("--n-envs", type=int, default=8)
    parser.add_argument("--save-path", type=Path, default=CHECKPOINT_DIR / "ppo_baseline")
    parser.add_argument("--resume-from", type=Path, default=None)
    parser.add_argument("--target-lap-rate", type=float, default=None)
    args = parser.parse_args()

    train(args.timesteps, args.n_envs, args.save_path, args.resume_from, args.target_lap_rate)
