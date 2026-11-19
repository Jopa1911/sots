"""Conversation template (obrazac razgovora): the parent's moves, the flow rules and the rewriting material.

For every turn the template answers two questions:
- FLOW: which move does the parent make next? (`choose_move`, rules in `policy`)
- CONTENT: what does the move say? (`guidelines` for a language model, `vanilla` sentences without one)
"""

from __future__ import annotations

import operator
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import CONTENT_DIR

TEMPLATE_PATH = CONTENT_DIR / "templates" / "parent_call.yaml"

_OPS = [
    ("_not_in", lambda actual, expected: actual not in expected),
    ("_in", lambda actual, expected: actual in expected),
    ("_has_any", lambda actual, expected: any(x in actual for x in expected)),
    ("_has", lambda actual, expected: expected in actual),
    ("_gte", operator.ge),
    ("_lte", operator.le),
    ("_gt", operator.gt),
    ("_lt", operator.lt),
]


class _SafeDict(dict):
    def __missing__(self, key):
        return ""


def fill_slots(text: str, slots: dict) -> str:
    return " ".join(text.format_map(_SafeDict(slots)).split())


@dataclass
class Move:
    name: str
    phase: str
    intent: str
    guidelines: str
    levels: tuple[int, int]
    vanilla: list[str]
    harsh: dict[int, list[str]] = field(default_factory=dict)
    effects: dict = field(default_factory=dict)
    end_with: str = ""

    def harsh_for(self, level: int) -> list[str]:
        """Move-specific additions for a level; falls back to the nearest lower level that has some."""
        for lvl in range(level, 1, -1):
            if self.harsh.get(lvl):
                return list(self.harsh[lvl])
        return []


class ConversationTemplate:
    def __init__(self, data: dict):
        self.data = data
        self.levels = {int(k): v for k, v in data.get("levels", {}).items()}
        self.moves: dict[str, Move] = {}
        for name, m in data["moves"].items():
            low, high = m.get("levels", [1, 5])
            self.moves[name] = Move(
                name=name,
                phase=m.get("phase", "discussion"),
                intent=m.get("intent", ""),
                guidelines=m.get("guidelines", ""),
                levels=(int(low), int(high)),
                vanilla=list(m.get("vanilla", [])),
                harsh={int(k): list(v) for k, v in (m.get("harsh") or {}).items()},
                effects=dict(m.get("effects") or {}),
                end_with=m.get("end_with", ""),
            )
        self.policy: list[dict] = list(data.get("policy", []))
        self.generic_harsh = {int(k): list(v) for k, v in data.get("generic_harsh", {}).items()}
        self.openers = {int(k): list(v) for k, v in data.get("openers", {}).items()}
        self.emphasis_words = [w.lower() for w in data.get("emphasis_words", [])]
        self.rewrite_rules = [(int(r[0]), r[1], r[2]) for r in data.get("rewrite_rules", [])]
        unknown = {rule["move"] for rule in self.policy} - set(self.moves)
        if unknown:
            raise ValueError(f"Policy uses unknown moves: {sorted(unknown)}")

    @classmethod
    def load(cls, path: str | Path | None = None) -> "ConversationTemplate":
        return cls(yaml.safe_load(Path(path or TEMPLATE_PATH).read_text(encoding="utf-8")))

    # ---- flow -------------------------------------------------------------------------------
    @staticmethod
    def condition_holds(condition: dict, state: dict) -> bool:
        for key, expected in (condition or {}).items():
            for suffix, op in _OPS:
                if key.endswith(suffix):
                    actual = state.get(key[: -len(suffix)])
                    if actual is None:
                        return False
                    try:
                        if not op(actual, expected):
                            return False
                    except TypeError:
                        return False
                    break
            else:
                if state.get(key) != expected:
                    return False
        return True

    def choose_move(self, state: dict) -> tuple[str, int]:
        """Return (move name, index of the policy rule that fired)."""
        for index, rule in enumerate(self.policy):
            if self.condition_holds(rule.get("when", {}), state):
                return rule["move"], index
        return "ASK_FOR_PLAN", -1

    # ---- content and anger ------------------------------------------------------------------
    def move(self, name: str) -> Move:
        return self.moves[name]

    def clip_level(self, move: Move, level: int) -> int:
        low, high = move.levels
        return max(low, min(high, level))

    def level_style(self, level: int) -> str:
        info = self.levels.get(level, {})
        return f"{info.get('name', level)}: {info.get('style', '')}".strip()

    def vanilla_text(self, move: Move, slots: dict, rng: random.Random | None = None) -> str:
        options = move.vanilla or [move.intent]
        text = (rng or random).choice(options)
        return fill_slots(text, slots)
