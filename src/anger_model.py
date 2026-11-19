"""The chatbot's emotion: the parent's anger (0-10) and how each teacher turn changes it.

    anger(t+1) = clamp(anger(t) + clamp(sensitivity * sum(effects), -2, +2), 0, 10)

Effects of one teacher turn:
- every recognised strategy adds its delta from the cards (S3 -1.5, S6 -1.0 or +0.5 if anger > 5, A3 +2.0 ...);
- "I understand, but...": if the turn also contains an escalating behaviour, calming deltas count half;
- the teacher's own measured anger: +0.5 from 5/10, +1.0 from 7/10;
- off-topic turn +0.5; the complaint ignored for 3 or more turns in a row +0.5.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .levels import clamp
from .strategies import ESCALATING, OFF, Card, load_cards

REASONS_SR = {
    "OFF": "skretanje sa teme",
    "TEACHER_ANGER": "ljutnja u tonu nastavnika",
    "IGNORED": "pritužba ignorisana 3+ replike zaredom",
}


@dataclass
class AngerUpdate:
    before: float
    after: float
    raw: float
    applied: float
    components: list[tuple[str, float, str]] = field(default_factory=list)  # (source, delta, note)


class AngerModel:
    def __init__(self, cards: dict[str, Card] | None = None, sensitivity: float = 1.0, max_step: float = 2.0,
                 teacher_threshold: float = 5.0, teacher_high: float = 7.0, ignored_after: int = 3):
        self.cards = cards or load_cards()
        self.sensitivity = sensitivity
        self.max_step = max_step
        self.teacher_threshold = teacher_threshold
        self.teacher_high = teacher_high
        self.ignored_after = ignored_after

    def update(self, anger: float, labels: list[str], teacher_anger: float = 0.0, off_topic: bool = False,
               ignored_turns: int = 0) -> AngerUpdate:
        components: list[tuple[str, float, str]] = []
        escalating = any(label in ESCALATING for label in labels)
        for label in labels:
            card = self.cards.get(label)
            if card is None or label == OFF:
                continue
            delta = card.delta_at(anger)
            note = card.name
            if label == "S6" and delta > 0:
                note += " (predlog dok je ljutnja > 5)"
            if delta < 0 and escalating:
                delta *= 0.5
                note += " (upola: 'razumem, ali...')"
            components.append((label, delta, note))
        if off_topic:
            components.append(("OFF", self.cards[OFF].delta if OFF in self.cards else 0.5, REASONS_SR["OFF"]))
        if teacher_anger >= self.teacher_high:
            components.append(("TEACHER_ANGER", 1.0, REASONS_SR["TEACHER_ANGER"]))
        elif teacher_anger >= self.teacher_threshold:
            components.append(("TEACHER_ANGER", 0.5, REASONS_SR["TEACHER_ANGER"]))
        if ignored_turns >= self.ignored_after:
            components.append(("IGNORED", 0.5, REASONS_SR["IGNORED"]))
        raw = sum(delta for _, delta, _ in components)
        applied = clamp(self.sensitivity * raw, -self.max_step, self.max_step)
        after = round(clamp(anger + applied, 0.0, 10.0), 2)
        return AngerUpdate(before=anger, after=after, raw=round(raw, 2), applied=round(after - anger, 2),
                           components=components)
