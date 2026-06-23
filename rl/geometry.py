from __future__ import annotations

import pygame

FIREBOY = "fireboy"
WATERGIRL = "watergirl"

LEVEL1_HAZARD_SPECS = (
    ("fire", (528, 784, 100, 28)),
    ("water", (758, 784, 100, 28)),
    ("poison", (706, 616, 100, 24)),
)

PLAYER_HAZARD_INSETS = {
    FIREBOY: (15, 8, 15, 2),
    WATERGIRL: (20, 8, 20, 2),
}

LETHAL_HAZARDS = {
    FIREBOY: {"water", "poison"},
    WATERGIRL: {"fire", "poison"},
}


def make_hazard_rects(level: int) -> list[tuple[str, pygame.Rect]]:
    if level != 1:
        return []
    return [(kind, pygame.Rect(*rect_args)) for kind, rect_args in LEVEL1_HAZARD_SPECS]


def is_lethal_hazard(agent: str, hazard_kind: str) -> bool:
    return hazard_kind in LETHAL_HAZARDS[agent]
