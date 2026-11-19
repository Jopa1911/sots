"""Scenarios: what the parent knows and complains about (the agent's long-term memory)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import CONTENT_DIR

SCENARIO_DIR = CONTENT_DIR / "scenarios"


@dataclass
class Complaint:
    id: str
    text: str
    say: str
    condition: str
    main: bool = False
    ack_keywords: list[str] = field(default_factory=list)
    resolve_keywords: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    id: str
    title: str
    description: str
    parent: dict
    slots: dict
    details: list[str]
    complaints: list[Complaint]
    anger: dict
    limits: dict
    topic_keywords: list[str]

    @property
    def main_complaint(self) -> Complaint:
        return next((c for c in self.complaints if c.main), self.complaints[0])

    @property
    def initial_anger(self) -> float:
        return float(self.anger.get("initial", 7.0))

    @property
    def sensitivity(self) -> float:
        return float(self.anger.get("sensitivity", 1.0))

    @property
    def max_turns(self) -> int:
        return int(self.limits.get("max_turns", 16))


def list_scenarios() -> list[str]:
    return sorted(p.stem for p in SCENARIO_DIR.glob("*.yaml"))


def load_scenario(name_or_path: str | Path) -> Scenario:
    path = Path(name_or_path)
    if not path.suffix:
        path = SCENARIO_DIR / f"{name_or_path}.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    complaints = [
        Complaint(
            id=c["id"],
            text=c["text"],
            say=c.get("say", c["text"]),
            condition=c.get("condition", ""),
            main=bool(c.get("main", False)),
            ack_keywords=list(c.get("ack_keywords", [])),
            resolve_keywords=list(c.get("resolve_keywords", [])),
        )
        for c in data.get("complaints", [])
    ]
    if not complaints:
        raise ValueError(f"Scenario {path} has no complaints.")
    return Scenario(
        id=data.get("id", path.stem),
        title=data.get("title", path.stem),
        description=" ".join(str(data.get("description", "")).split()),
        parent=dict(data.get("parent", {})),
        slots=dict(data.get("slots", {})),
        details=list(data.get("details", [])),
        complaints=complaints,
        anger=dict(data.get("anger", {})),
        limits=dict(data.get("limits", {})),
        topic_keywords=[str(k) for k in data.get("topic_keywords", [])],
    )
