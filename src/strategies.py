"""Teacher strategies (S1-S8 from ESConv, A1-A3 escalating, OFF off-topic) and learning cards."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from .config import CONTENT_DIR

CARDS_PATH = CONTENT_DIR / "cards" / "strategies.yaml"
RELATION_PATH = CONTENT_DIR / "esconv" / "relation.json"

SUPPORT = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
ESCALATING = ["A1", "A2", "A3"]
OFF = "OFF"
CALMING = ["S1", "S2", "S3", "S5", "S6", "S7"]

ESCONV_LABELS = {
    "Question": "S1",
    "Restatement or Paraphrasing": "S2",
    "Reflection of feelings": "S3",
    "Self-disclosure": "S4",
    "Affirmation and Reassurance": "S5",
    "Providing Suggestions": "S6",
    "Information": "S7",
    "Others": "S8",
}

# Pairs (a, b): "a usually comes before b" in ESConv, used to score the order of strategies.
# Only pairs that lead to the action stage (suggestions, information) are scored; see DNEVNIK.md, section 4.
KEY_ORDER = [("S3", "S6"), ("S3", "S7"), ("S5", "S7")]


@dataclass
class Card:
    id: str
    name: str
    kind: str
    delta: float
    definition: str = ""
    learning_goal: str = ""
    explanation: str = ""
    school_example: str = ""
    counterexample: str = ""
    esconv_example: dict = field(default_factory=dict)
    check: dict = field(default_factory=dict)
    practice: dict = field(default_factory=dict)
    delta_if_anger_above: dict | None = None

    def delta_at(self, anger: float) -> float:
        """Effect on the parent's anger, before sensitivity. S6 depends on the current anger."""
        rule = self.delta_if_anger_above
        if rule and anger > float(rule["threshold"]):
            return float(rule["delta"])
        return float(self.delta)


@lru_cache(maxsize=4)
def load_cards(path: str | None = None) -> dict[str, Card]:
    data = yaml.safe_load(Path(path or CARDS_PATH).read_text(encoding="utf-8"))
    cards = {}
    for sid, c in data["strategies"].items():
        cards[sid] = Card(
            id=sid,
            name=c["name"],
            kind=c.get("kind", "neutral"),
            delta=float(c.get("delta", 0.0)),
            definition=" ".join(str(c.get("definition", "")).split()),
            learning_goal=c.get("learning_goal", ""),
            explanation=" ".join(str(c.get("explanation", "")).split()),
            school_example=c.get("school_example", ""),
            counterexample=c.get("counterexample", ""),
            esconv_example=c.get("esconv_example", {}) or {},
            check=c.get("check", {}) or {},
            practice=c.get("practice", {}) or {},
            delta_if_anger_above=c.get("delta_if_anger_above"),
        )
    return cards


def label_name(label: str) -> str:
    cards = load_cards()
    return cards[label].name if label in cards else label


@lru_cache(maxsize=2)
def load_relation(path: str | None = None) -> dict:
    """Precedence relation computed from ESConv by data/build_esconv_resources.py."""
    p = Path(path or RELATION_PATH)
    if not p.exists():
        return {"threshold": 70, "edges": [], "matrix": {}}
    return json.loads(p.read_text(encoding="utf-8"))
