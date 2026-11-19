"""One practice conversation: the per-turn pipeline that connects all layers.

For every teacher turn:
 1. classify the teacher's strategies (S1-S8, A1-A3)          -> classifier.py
 2. keep the focus: is the turn about the complaint?          -> focus.py
 3. measure the teacher's anger (layer 3)                     -> anger_meter.py
 4. update the complaints (acknowledged, resolved, proposal)
 5. update the parent's anger (layer 2)                       -> anger_model.py
 6. check the end of the call (resolved, hung up, timeout)
 7. choose the parent's next move (layer 1: flow)             -> template.py
 8. write the move: guidelines -> vanilla -> harsh -> check   -> generator.py
 9. log everything for the evaluator (role 2)                 -> evaluator.py
"""

from __future__ import annotations

import dataclasses
import json
import random
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from .anger_meter import get_meter
from .anger_model import AngerModel
from .classifier import get_classifier
from .config import LOGS_DIR, Settings
from .focus import FocusGuard
from .generator import AngerPipeline, GenerationResult
from .levels import level_for
from .llm import get_llm
from .scenario import Complaint, Scenario, load_scenario
from .strategies import CALMING, ESCALATING
from .template import ConversationTemplate
from .textutil import has_phrase, normalize

ACK_STRATEGIES = {"S2", "S3", "S5"}
OUTCOMES_SR = {"resolved": "dogovor postignut", "hung_up": "roditelj je prekinuo razgovor",
               "timeout": "isteklo vreme bez dogovora", None: "razgovor u toku"}


@dataclass
class ComplaintState:
    complaint: Complaint
    raised: bool = False
    acknowledged: bool = False
    resolved: bool = False
    ack_turn: int | None = None
    resolved_turn: int | None = None

    def to_dict(self) -> dict:
        return {"id": self.complaint.id, "text": self.complaint.text, "main": self.complaint.main,
                "raised": self.raised, "acknowledged": self.acknowledged, "resolved": self.resolved,
                "ack_turn": self.ack_turn, "resolved_turn": self.resolved_turn}


@dataclass
class TurnRecord:
    turn: int
    teacher_text: str
    labels: list[str]
    primary: str
    classifier_source: str
    off_topic: bool
    injection: bool
    focus_reason: str
    teacher_anger: float
    teacher_anger_level: int
    anger_before: float
    anger_after: float
    anger_components: list
    acknowledged: list[str]
    resolved: list[str]
    proposal: str
    ignored: int
    move: str
    policy_rule: int
    target_level: int
    guidelines: str
    vanilla: str
    vanilla_source: str
    parent_text: str
    parent_score: float
    parent_level: int
    rewrite_source: str
    outcome: str | None
    candidates: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class Session:
    def __init__(self, scenario: Scenario | str = "bad_grade", settings: Settings | None = None, *,
                 template: ConversationTemplate | None = None, llm=None, classifier=None, meter=None,
                 pipeline: AngerPipeline | None = None, initial_anger: float | None = None,
                 sensitivity: float | None = None, seed: int | None = None, use_llm: bool = True):
        settings = dataclasses.replace(settings) if settings else Settings.from_env()
        if seed is not None:
            settings.seed = seed
        self.settings = settings
        self.scenario = load_scenario(scenario) if isinstance(scenario, (str, Path)) else scenario
        self.template = template or ConversationTemplate.load()
        self.rng = random.Random(settings.seed)
        self.warnings: list[str] = []

        self.llm = llm
        rewriter_llm = None
        if self.llm is None and use_llm and settings.llm_enabled:
            try:
                self.llm = get_llm(settings)
                if settings.rewriter_llm_model:
                    rewriter_llm = get_llm(settings, settings.rewriter_llm_model)
            except Exception as exc:
                self.warnings.append(f"Jezički model nije dostupan ({exc}); koriste se šabloni i pravila.")
                self.llm = None

        self.classifier = classifier or get_classifier(settings, self.llm)
        self.meter = meter or get_meter(settings, self.llm)
        self.focus = FocusGuard(self.scenario)
        self.pipeline = pipeline or AngerPipeline(self.template, self.scenario, settings, self.llm, rewriter_llm,
                                                  meter=self.meter, focus=self.focus, rng=self.rng)

        self.initial_anger = float(self.scenario.initial_anger if initial_anger is None else initial_anger)
        self.sensitivity = float(self.scenario.sensitivity if sensitivity is None else sensitivity)
        self.anger = self.initial_anger
        self.model = AngerModel(sensitivity=self.sensitivity, teacher_threshold=settings.teacher_anger_threshold)
        self.complaints = [ComplaintState(c, raised=c.main) for c in self.scenario.complaints]
        self.details_revealed = 0
        self.hidden_need_revealed = False
        self.ignored = 0
        self.high_anger_turns = 0
        self.turn = 0
        self.outcome: str | None = None
        self.history: list[dict] = []
        self.records: list[TurnRecord] = []
        self.opening: GenerationResult | None = None
        self.started = time.monotonic()
        self.started_at = datetime.now().isoformat(timespec="seconds")

    # ---- state ------------------------------------------------------------------------------------
    @property
    def finished(self) -> bool:
        return self.outcome is not None

    @property
    def anger_curve(self) -> list[float]:
        return [self.initial_anger] + [r.anger_after for r in self.records]

    def _first(self, predicate) -> ComplaintState | None:
        return next((c for c in self.complaints if predicate(c)), None)

    def slots(self) -> dict:
        slots = dict(self.scenario.slots)
        details = self.scenario.details
        slots["next_detail"] = details[self.details_revealed] if self.details_revealed < len(details) else ""
        unraised = self._first(lambda c: not c.raised and not c.resolved)
        slots["next_complaint"] = unraised.complaint.say if unraised else ""
        open_ = self._first(lambda c: not c.resolved and not c.complaint.main) or self._first(lambda c: not c.resolved)
        slots["next_condition"] = open_.complaint.condition if open_ else ""
        return slots

    def policy_state(self, labels=(), primary: str = "", proposal: str = "none", off_topic: bool = False) -> dict:
        main = self._first(lambda c: c.complaint.main)
        return {
            "turn": self.turn,
            "outcome": self.outcome,
            "off_topic": off_topic,
            "anger": self.anger,
            "strategies": list(labels),
            "last_strategy": primary,
            "proposal": proposal,
            "open_complaints": sum(not c.resolved for c in self.complaints),
            "unraised_complaints": sum(not c.raised and not c.resolved for c in self.complaints),
            "main_acknowledged": bool(main and (main.acknowledged or main.resolved)),
            "details_left": len(self.scenario.details) - self.details_revealed,
            "details_revealed": self.details_revealed,
            "hidden_need_revealed": self.hidden_need_revealed,
            "ignored": self.ignored,
        }

    def _apply_effects(self, move_name: str) -> None:
        effects = self.template.move(move_name).effects
        if effects.get("reveal_detail") and self.details_revealed < len(self.scenario.details):
            self.details_revealed += 1
        if effects.get("raise_complaint"):
            unraised = self._first(lambda c: not c.raised and not c.resolved)
            if unraised:
                unraised.raised = True
        if effects.get("set", {}).get("hidden_need_revealed"):
            self.hidden_need_revealed = True

    # ---- conversation -----------------------------------------------------------------------------
    def start(self) -> GenerationResult:
        """The parent opens the call."""
        if self.opening is None:
            move, _ = self.template.choose_move(self.policy_state())
            self.opening = self.pipeline.realize(move, self.anger, self.slots(), self.history)
            self._apply_effects(move)
            self.history.append({"role": "parent", "text": self.opening.text})
        return self.opening

    def _update_complaints(self, text: str, labels: list[str], anger: float, off_topic: bool):
        if off_topic:
            return [], [], "none"
        norm = normalize(text)
        escalating = any(label in ESCALATING for label in labels)
        acknowledged, resolved = [], []
        if not escalating and ACK_STRATEGIES & set(labels):
            for cs in self.complaints:
                if not cs.acknowledged and not cs.resolved and \
                        any(has_phrase(norm, k) for k in cs.complaint.ack_keywords):
                    cs.acknowledged, cs.raised, cs.ack_turn = True, True, self.turn
                    acknowledged.append(cs.complaint.id)
        proposal = "none"
        if "S6" in labels and not escalating:
            matched = [cs for cs in self.complaints
                       if not cs.resolved and any(has_phrase(norm, k) for k in cs.complaint.resolve_keywords)]
            if not matched:
                proposal = "vague"
            elif anger > 5:
                proposal = "rejected"
            else:
                ready = [cs for cs in matched if cs.acknowledged or not cs.raised]
                for cs in ready:
                    cs.resolved, cs.raised, cs.resolved_turn = True, True, self.turn
                    resolved.append(cs.complaint.id)
                proposal = "accepted" if ready else "rejected"
        return acknowledged, resolved, proposal

    def _check_end(self) -> None:
        anger_cfg = self.scenario.anger
        if self.anger >= float(anger_cfg.get("hang_up_threshold", 9.0)):
            self.high_anger_turns += 1
        else:
            self.high_anger_turns = 0
        minutes = (time.monotonic() - self.started) / 60
        if self.high_anger_turns >= int(anger_cfg.get("hang_up_turns", 2)):
            self.outcome = "hung_up"
        elif all(c.resolved for c in self.complaints) and \
                self.anger <= float(anger_cfg.get("resolve_threshold", 3.0)):
            self.outcome = "resolved"
        elif self.turn >= self.scenario.max_turns or (self.settings.max_minutes > 0 and
                                                      minutes >= self.settings.max_minutes):
            self.outcome = "timeout"

    def respond(self, teacher_text: str) -> TurnRecord:
        if self.opening is None:
            self.start()
        if self.finished:
            raise RuntimeError("Razgovor je završen; započnite novi.")
        text = " ".join((teacher_text or "").split())
        if not text:
            raise ValueError("Prazna replika.")
        self.turn += 1
        self.history.append({"role": "teacher", "text": text})

        classification = self.classifier.classify(text)
        focus = self.focus.check_input(text, classification.labels)
        off_topic = not focus.on_topic
        labels = list(classification.labels)
        if off_topic:
            labels = [label for label in labels if label in ESCALATING] + ["OFF"]
        primary = labels[0]

        reading = self.meter.measure(text)
        anger_before = self.anger
        acknowledged, resolved, proposal = self._update_complaints(text, labels, anger_before, off_topic)
        engaged = bool(set(labels) & set(CALMING)) or bool(acknowledged or resolved)
        self.ignored = 0 if engaged else self.ignored + 1

        update = self.model.update(anger_before, [x for x in labels if x != "OFF"], reading.score,
                                   off_topic=off_topic, ignored_turns=self.ignored)
        self.anger = update.after
        self._check_end()

        move, rule = self.template.choose_move(self.policy_state(labels, primary, proposal, off_topic))
        result = self.pipeline.realize(move, self.anger, self.slots(), self.history)
        self._apply_effects(move)
        self.history.append({"role": "parent", "text": result.text})

        record = TurnRecord(
            turn=self.turn, teacher_text=text, labels=labels, primary=primary,
            classifier_source=classification.source, off_topic=off_topic, injection=focus.injection,
            focus_reason=focus.reason, teacher_anger=reading.score, teacher_anger_level=reading.level,
            anger_before=anger_before, anger_after=self.anger, anger_components=update.components,
            acknowledged=acknowledged, resolved=resolved, proposal=proposal, ignored=self.ignored,
            move=move, policy_rule=rule, target_level=result.target_level, guidelines=result.guidelines,
            vanilla=result.vanilla, vanilla_source=result.vanilla_source, parent_text=result.text,
            parent_score=result.score, parent_level=result.level, rewrite_source=result.source,
            outcome=self.outcome,
            candidates=[{"text": c.text, "source": c.source, "score": c.score, "level": c.level,
                         "ok": c.acceptable, "notes": c.notes} for c in result.candidates],
        )
        self.records.append(record)
        return record

    # ---- results ----------------------------------------------------------------------------------
    def report(self, llm_narrative: bool = False) -> dict:
        from .evaluator import Evaluator

        evaluator = Evaluator(teacher_threshold=self.settings.teacher_anger_threshold,
                              llm=self.llm if llm_narrative else None)
        return evaluator.evaluate(self)

    def to_dict(self, with_report: bool = True) -> dict:
        data = {
            "scenario": self.scenario.id,
            "started_at": self.started_at,
            "settings": self.settings.public_dict(),
            "initial_anger": self.initial_anger,
            "sensitivity": self.sensitivity,
            "opening": self.opening.to_dict() if self.opening else None,
            "turns": [r.to_dict() for r in self.records],
            "complaints": [c.to_dict() for c in self.complaints],
            "outcome": self.outcome,
            "warnings": self.warnings,
        }
        if with_report:
            data["report"] = self.report()
        return data

    def save(self, path: str | Path | None = None) -> Path:
        if path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = LOGS_DIR / "sessions" / f"{stamp}_{self.scenario.id}.json"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    @property
    def level(self) -> int:
        return level_for(self.anger)

    @property
    def outcome_sr(self) -> str:
        return OUTCOMES_SR.get(self.outcome, str(self.outcome))
