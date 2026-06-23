from __future__ import annotations

import argparse

import pygame

try:
    from .env import (
        ACTION_JUMP,
        ACTION_LEFT,
        ACTION_LEFT_JUMP,
        ACTION_NOOP,
        ACTION_RIGHT,
        ACTION_RIGHT_JUMP,
        FIREBOY,
        WATERGIRL,
        FireWaterEnv,
    )
except ImportError:
    from env import (
        ACTION_JUMP,
        ACTION_LEFT,
        ACTION_LEFT_JUMP,
        ACTION_NOOP,
        ACTION_RIGHT,
        ACTION_RIGHT_JUMP,
        FIREBOY,
        WATERGIRL,
        FireWaterEnv,
    )


def action_from_keys(keys, left_key: int, right_key: int, jump_key: int) -> int:
    left = keys[left_key] and not keys[right_key]
    right = keys[right_key] and not keys[left_key]
    jump = keys[jump_key]
    if left and jump:
        return ACTION_LEFT_JUMP
    if right and jump:
        return ACTION_RIGHT_JUMP
    if left:
        return ACTION_LEFT
    if right:
        return ACTION_RIGHT
    if jump:
        return ACTION_JUMP
    return ACTION_NOOP


def main() -> None:
    parser = argparse.ArgumentParser(description="Manually drive the RL training environment.")
    parser.add_argument("--level", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()

    env = FireWaterEnv({"level": args.level, "render_mode": "human"})
    env.reset()
    reset_was_pressed = False
    fire_action_count = 0
    water_action_count = 0

    while True:
        env.render()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            break

        reset_pressed = keys[pygame.K_r]
        if reset_pressed and not reset_was_pressed:
            env.reset()
            fire_action_count = 0
            water_action_count = 0
        reset_was_pressed = reset_pressed

        fire_action = action_from_keys(keys, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP)
        water_action = action_from_keys(keys, pygame.K_a, pygame.K_d, pygame.K_w)
        if fire_action != ACTION_NOOP:
            fire_action_count += 1
        if water_action != ACTION_NOOP:
            water_action_count += 1
        actions = {FIREBOY: fire_action, WATERGIRL: water_action}
        _, _, terminateds, truncateds, infos = env.step(actions)

        fire_info = infos[FIREBOY]
        pygame.display.set_caption(
            "RL manual env | "
            f"level={args.level} env_steps={fire_info['steps']} "
            f"fire={fire_action_count} water={water_action_count} "
            f"ground=({int(env.fire.on_ground)},{int(env.water.on_ground)}) "
            f"arm={env.arm_opened} button={env.button_opened} "
            f"death={fire_info['death']} win={fire_info['win']} | "
            "Esc quit, R reset"
        )

        if terminateds["__all__"] or truncateds["__all__"]:
            env.reset()
            fire_action_count = 0
            water_action_count = 0

    env.close()


if __name__ == "__main__":
    main()
