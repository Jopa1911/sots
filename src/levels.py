"""Anger levels shared by the anger model, the anger meter and the conversation template.

Anger is a number from 0 to 10. For generation it is grouped into five levels:
1 calm (0-2), 2 dissatisfied (3-4), 3 angry (5-6), 4 very angry (7-8), 5 about to hang up (9-10).
"""

from __future__ import annotations

THRESHOLDS = (2.5, 4.5, 6.5, 8.5)

NAMES_EN = {1: "calm", 2: "dissatisfied", 3: "angry", 4: "very angry", 5: "about to hang up"}
NAMES_SR = {1: "smiren", 2: "nezadovoljan", 3: "ljut", 4: "jako ljut", 5: "pred prekidom"}
BANDS = {1: (0.0, 2.5), 2: (2.5, 4.5), 3: (4.5, 6.5), 4: (6.5, 8.5), 5: (8.5, 10.0)}


def level_for(anger: float) -> int:
    """Map anger 0-10 to level 1-5."""
    return 1 + sum(anger >= t for t in THRESHOLDS)


def band_center(level: int) -> float:
    low, high = BANDS[level]
    return (low + high) / 2


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
