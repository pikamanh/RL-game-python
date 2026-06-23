from __future__ import annotations

import argparse
import time

try:
    from .common import compute_action, ensure_ray, load_algorithm, load_algorithm_from_weights
    from .env import AGENTS, FireWaterEnv
except ImportError:
    from common import compute_action, ensure_ray, load_algorithm, load_algorithm_from_weights
    from env import AGENTS, FireWaterEnv

# python3 rl/eval.py --render --level 1 --checkpoint checkpoints/best/

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a trained Fireboy/Watergirl multi-agent checkpoint.")
    parser.add_argument("--checkpoint")
    parser.add_argument("--weights")
    parser.add_argument("--level", type=int, choices=[1, 2], default=1)
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=3000)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--explore", action="store_true")
    parser.add_argument("--rl-realtime", action="store_true")
    parser.add_argument("--shared-policy", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--step-size", type=float, default=5.0)
    parser.add_argument("--gravity", type=float, default=0.55)
    parser.add_argument("--jump-velocity", type=float, default=8.0)
    return parser.parse_args()


def main():
    args = parse_args()
    if bool(args.checkpoint) == bool(args.weights):
        raise SystemExit("Use exactly one of --checkpoint or --weights.")
    ensure_ray()
    algo = load_algorithm_from_weights(args.weights, args) if args.weights else load_algorithm(args.checkpoint)
    env = FireWaterEnv(vars(args))

    try:
        wins = 0
        for episode in range(1, args.episodes + 1):
            obs, _ = env.reset()
            total_reward = 0.0
            done = False
            info = {}
            step_count = 0
            while not done:
                actions = {
                    agent: compute_action(algo, obs[agent], agent, args.shared_policy, explore=args.explore)
                    for agent in AGENTS
                }
                obs, rewards, terminateds, truncateds, infos = env.step(actions)
                total_reward += sum(rewards.values()) / len(rewards)
                done = terminateds["__all__"] or truncateds["__all__"]
                info = infos[AGENTS[0]]
                step_count += 1
                if args.rl_realtime:
                    print(f"\rstep={step_count}", end="", flush=True)
                if args.render:
                    env.render()
                if args.sleep > 0:
                    time.sleep(args.sleep)
            if args.rl_realtime:
                print()
            wins += int(bool(info.get("win")))
            print(
                f"episode={episode} reward={total_reward:.3f} "
                f"steps={info.get('steps')} win={info.get('win')} death={info.get('death')}"
            )
        print(f"wins={wins}/{args.episodes}")
    finally:
        env.close()
        algo.stop()


if __name__ == "__main__":
    main()
