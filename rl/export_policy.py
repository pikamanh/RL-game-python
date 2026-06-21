from __future__ import annotations

import argparse

try:
    from .common import ensure_ray, load_algorithm, save_policy_weights
except ImportError:
    from common import ensure_ray, load_algorithm, save_policy_weights


def parse_args():
    parser = argparse.ArgumentParser(description="Export RLlib policy weights to a portable npz file.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--shared-policy", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_ray()
    algo = load_algorithm(args.checkpoint)
    try:
        output = save_policy_weights(algo, args.output, args.shared_policy)
        print(f"policy_weights={output}")
    finally:
        algo.stop()


if __name__ == "__main__":
    main()
