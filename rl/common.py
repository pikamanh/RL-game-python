from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

os.environ.setdefault("RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO", "0")
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
os.environ.setdefault("PYTORCH_JIT", "0")

import numpy as np
import ray
from gymnasium import spaces
from ray.rllib.algorithms.algorithm import Algorithm
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.policy.policy import PolicySpec
from ray.tune.registry import register_env

try:
    from .env import AGENTS, FireWaterEnv
except ImportError:
    from env import AGENTS, FireWaterEnv


ENV_NAME = "firewater_multi_agent"


def register_firewater_env():
    register_env(ENV_NAME, lambda config: FireWaterEnv(config))


def build_ppo_config(args: Any) -> PPOConfig:
    register_firewater_env()
    env_config = {
        "level": args.level,
        "max_steps": args.max_steps,
        "step_size": args.step_size,
        "gravity": args.gravity,
        "jump_velocity": args.jump_velocity,
    }
    probe_env = FireWaterEnv(env_config)
    obs_space: spaces.Space = probe_env.observation_space
    action_space: spaces.Space = probe_env.action_space
    probe_env.close()

    config = (
        PPOConfig()
        .environment(env=ENV_NAME, env_config=env_config)
        .framework(args.framework)
        .training(
            lr=args.lr,
            gamma=args.gamma,
            lambda_=args.gae_lambda,
            entropy_coeff=args.entropy_coeff,
            clip_param=args.clip_param,
            train_batch_size=args.batch_size,
            minibatch_size=args.minibatch_size,
            num_epochs=args.num_epochs,
        )
        .multi_agent(
            policies=_policies(obs_space, action_space, args.shared_policy),
            policy_mapping_fn=_policy_mapping_fn(args.shared_policy),
            policies_to_train=None,
        )
    )

    try:
        config = config.api_stack(
            enable_rl_module_and_learner=False,
            enable_env_runner_and_connector_v2=False,
        )
    except AttributeError:
        pass

    try:
        config = config.env_runners(
            num_env_runners=args.num_workers,
            batch_mode=args.batch_mode,
            rollout_fragment_length=args.rollout_fragment_length,
        )
    except AttributeError:
        config = config.rollouts(
            num_rollout_workers=args.num_workers,
            batch_mode=args.batch_mode,
            rollout_fragment_length=args.rollout_fragment_length,
        )

    if args.num_gpus is not None:
        config = config.resources(num_gpus=args.num_gpus)
    return config


def ensure_ray(local_mode: bool = False):
    if not ray.is_initialized():
        if local_mode:
            print("warning: --ray-local-mode is ignored on Ray versions that no longer support local_mode")
        ray.init(ignore_reinit_error=True, include_dashboard=False)


def load_algorithm(checkpoint: str) -> Algorithm:
    register_firewater_env()
    checkpoint_path = Path(checkpoint).expanduser().resolve()
    try:
        return Algorithm.from_checkpoint(str(checkpoint_path))
    except TypeError as exc:
        if "code expected at most" in str(exc):
            raise RuntimeError(
                "Cannot load this checkpoint in the current Python/Ray environment. "
                "Use the same Python version and Ray/RLlib version that created the checkpoint, "
                "or retrain/export the checkpoint in this environment."
            ) from exc
        raise


def build_inference_algorithm(args: Any) -> Algorithm:
    defaults = {
        "level": 1,
        "max_steps": 3000,
        "step_size": 5.0,
        "gravity": 0.55,
        "jump_velocity": 8.0,
        "framework": "torch",
        "lr": 3e-4,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "entropy_coeff": 0.02,
        "clip_param": 0.2,
        "batch_size": 4096,
        "minibatch_size": 512,
        "num_epochs": 10,
        "num_workers": 0,
        "num_gpus": 0.0,
        "batch_mode": "complete_episodes",
        "rollout_fragment_length": "auto",
    }
    values = vars(args).copy()
    defaults.update(values)
    config = build_ppo_config(SimpleNamespace(**defaults))
    return config.build_algo() if hasattr(config, "build_algo") else config.build()


def save_policy_weights(algo: Algorithm, output: str | Path, shared_policy: bool = True) -> Path:
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    policy_ids = ["shared_policy"] if shared_policy else ["fire_policy", "water_policy"]

    arrays = {}
    metadata = {"policy_ids": policy_ids, "weights": {}}
    index = 0
    for policy_id in policy_ids:
        metadata["weights"][policy_id] = []
        for weight_name, value in algo.get_policy(policy_id).get_weights().items():
            array_name = f"arr_{index}"
            arrays[array_name] = value
            metadata["weights"][policy_id].append([weight_name, array_name])
            index += 1

    arrays["metadata"] = np.array(json.dumps(metadata))
    np.savez_compressed(output, **arrays)
    return output


def load_algorithm_from_weights(weights: str | Path, args: Any) -> Algorithm:
    algo = build_inference_algorithm(args)
    data = np.load(Path(weights).expanduser().resolve(), allow_pickle=False)
    metadata = json.loads(str(data["metadata"]))
    for policy_id, entries in metadata["weights"].items():
        policy_weights = {weight_name: data[array_name] for weight_name, array_name in entries}
        algo.get_policy(policy_id).set_weights(policy_weights)
    return algo


def policy_id_for_agent(agent_id: str, shared_policy: bool) -> str:
    if shared_policy:
        return "shared_policy"
    return "fire_policy" if agent_id == AGENTS[0] else "water_policy"


def compute_action(algo: Algorithm, obs, agent_id: str, shared_policy: bool, explore: bool = False):
    return algo.compute_single_action(
        obs,
        policy_id=policy_id_for_agent(agent_id, shared_policy),
        explore=explore,
    )


def _policies(obs_space: spaces.Space, action_space: spaces.Space, shared_policy: bool):
    if shared_policy:
        return {"shared_policy": PolicySpec(None, obs_space, action_space, {})}
    return {
        "fire_policy": PolicySpec(None, obs_space, action_space, {}),
        "water_policy": PolicySpec(None, obs_space, action_space, {}),
    }


def _policy_mapping_fn(shared_policy: bool):
    if shared_policy:
        return lambda agent_id, episode=None, worker=None, **kwargs: "shared_policy"
    return lambda agent_id, episode=None, worker=None, **kwargs: "fire_policy" if agent_id == AGENTS[0] else "water_policy"
