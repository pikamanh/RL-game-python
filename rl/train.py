from __future__ import annotations

import argparse
import math
from pathlib import Path

from common import build_ppo_config, ensure_ray


def parse_args():
    parser = argparse.ArgumentParser(description="Train MAPPO-style multi-agent PPO for Fireboy and Watergirl.")
    parser.add_argument("--level", type=int, choices=[1, 2], default=1)
    parser.add_argument("--max-steps", type=int, default=3000)
    parser.add_argument("--stop-iters", type=int, default=500)
    parser.add_argument("--stop-reward", type=float, default=90.0)
    parser.add_argument("--checkpoint-dir", type=Path, default=Path("checkpoints"))
    parser.add_argument("--checkpoint-every", type=int, default=50)
    parser.add_argument("--save-best", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--best-checkpoint-name", default="best")
    parser.add_argument("--shared-policy", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--num-gpus", type=float, default=0.0)
    parser.add_argument("--framework", choices=["torch", "tf2"], default="torch")
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--gamma", type=float, default=0.99)
    parser.add_argument("--gae-lambda", type=float, default=0.95)
    parser.add_argument("--entropy-coeff", type=float, default=0.02)
    parser.add_argument("--clip-param", type=float, default=0.2)
    parser.add_argument("--train-batch-size", type=int, default=4096)
    parser.add_argument("--minibatch-size", type=int, default=512)
    parser.add_argument("--num-epochs", type=int, default=10)
    parser.add_argument("--batch-mode", choices=["complete_episodes", "truncate_episodes"], default="complete_episodes")
    parser.add_argument("--rollout-fragment-length", default="auto")
    parser.add_argument("--step-size", type=float, default=5.0)
    parser.add_argument("--gravity", type=float, default=0.55)
    parser.add_argument("--jump-velocity", type=float, default=8.0)
    parser.add_argument("--ray-local-mode", action="store_true")
    return parser.parse_args()


def metric(result, *paths, default=float("nan")):
    for path in paths:
        value = result
        for key in path:
            if not isinstance(value, dict) or key not in value:
                value = None
                break
            value = value[key]
        if value is not None:
            return value
    return default


def is_number(value):
    return isinstance(value, (int, float)) and not math.isnan(float(value))


def main():
    args = parse_args()
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    ensure_ray(local_mode=args.ray_local_mode)
    config = build_ppo_config(args)
    algo = config.build_algo() if hasattr(config, "build_algo") else config.build()

    last_checkpoint = None
    best_reward = float("-inf")
    try:
        for iteration in range(1, args.stop_iters + 1):
            result = algo.train()
            reward_mean = metric(
                result,
                ("episode_reward_mean",),
                ("env_runners", "episode_reward_mean"),
                ("env_runners", "episode_return_mean"),
            )
            length_mean = metric(
                result,
                ("episode_len_mean",),
                ("env_runners", "episode_len_mean"),
                ("env_runners", "episode_duration_sec_mean"),
            )
            episodes_this_iter = metric(
                result,
                ("episodes_this_iter",),
                ("num_episodes",),
                ("env_runners", "num_episodes"),
                default=0,
            )
            reward_text = f"{reward_mean:.3f}" if is_number(reward_mean) else "pending"
            length_text = f"{length_mean:.1f}" if is_number(length_mean) else "pending"
            print(
                f"iter={iteration} reward_mean={reward_text} "
                f"episode_len_mean={length_text} episodes={episodes_this_iter}"
            )

            if args.save_best and is_number(reward_mean) and reward_mean > best_reward:
                best_reward = reward_mean
                checkpoint = algo.save(str(args.checkpoint_dir / args.best_checkpoint_name))
                last_checkpoint = checkpoint.checkpoint.path if hasattr(checkpoint, "checkpoint") else str(checkpoint)
                print(f"best_checkpoint={last_checkpoint} best_reward={best_reward:.3f}")

            should_save = iteration % args.checkpoint_every == 0 or (is_number(reward_mean) and reward_mean >= args.stop_reward)
            if should_save:
                checkpoint = algo.save(str(args.checkpoint_dir / f"iter_{iteration:05d}"))
                last_checkpoint = checkpoint.checkpoint.path if hasattr(checkpoint, "checkpoint") else str(checkpoint)
                print(f"checkpoint={last_checkpoint}")

            if is_number(reward_mean) and reward_mean >= args.stop_reward:
                break
    finally:
        if last_checkpoint is None:
            checkpoint = algo.save(str(args.checkpoint_dir / "latest"))
            last_checkpoint = checkpoint.checkpoint.path if hasattr(checkpoint, "checkpoint") else str(checkpoint)
            print(f"checkpoint={last_checkpoint}")
        algo.stop()


if __name__ == "__main__":
    main()
