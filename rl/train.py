from __future__ import annotations

from pathlib import Path

import ray

from mappo import build_algo


def main():
    ray.init(ignore_reinit_error=True, include_dashboard=False)
    algo = build_algo()
    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 2001):
        result = algo.train()
        metrics = {
            "iter": i,
            "reward_mean": result.get("episode_reward_mean", result.get("env_runners", {}).get("episode_return_mean")),
            "len_mean": result.get("episode_len_mean", result.get("env_runners", {}).get("episode_len_mean")),
            "keys": [k for k in result.keys() if "reward" in k or "episode" in k or "env_runner" in k or "learner" in k][:12],
        }
        print(metrics)
        if i % 50 == 0:
            save_dir = (checkpoint_dir / f"iter_{i:05d}").resolve()
            ckpt = algo.save_to_path(save_dir.as_uri())
            print(f"saved={ckpt}")


if __name__ == "__main__":
    main()
