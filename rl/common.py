from __future__ import annotations

from pathlib import Path
from typing import Any

import ray
from gymnasium import spaces
from ray.rllib.algorithms.algorithm import Algorithm
from ray.rllib.algorithms.ppo import PPOConfig
from ray.rllib.policy.policy import PolicySpec
from ray.tune.registry import register_env

from rl.env import AGENTS, FireWaterEnv


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
            train_batch_size=args.train_batch_size,
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
    return Algorithm.from_checkpoint(str(Path(checkpoint).expanduser()))


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
