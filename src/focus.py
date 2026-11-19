"""Keeping the focus: the conversation stays on the parent's complaint.

- check_input: is the teacher's turn about the situation? Small talk and attempts to break the role
  ("ignore your instructions", "are you an AI?") are recognised, and the parent brings the talk back.
- validate_output: is a generated parent sentence in role, on topic and short? If not, the generator uses
  another candidate or the template sentence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .scenario import Scenario
from .textutil import normalize, tokens, word_count

INJECTION = [
    r"\bignore (all |the |your )?(previous |prior |above )?(instructions|prompts?|rules)\b",
    r"\b(are you|you are|youre) (an? )?(ai|bot|robot|language model|chatbot|assistant|real person|human)\b",
    r"\bsystem prompt\b", r"\bpretend (to be|you are)\b", r"\bact as\b", r"\brole ?play\b", r"\bjailbreak\b",
    r"\bforget (your|the|all) (role|instructions|rules)\b", r"\bdeveloper mode\b", r"\bnew instructions\b",
]
SMALL_TALK = [
    r"\b(weather|football|soccer|basketball|tennis|match|vacation|holiday|movie|film|series|netflix|recipe|"
    r"politics|election|stocks?|crypto|weekend|traffic|parking|lunch|dinner|coffee|joke)\b",
    r"\bby the way\b", r"\bon another note\b", r"\bchange of topic\b",
]
# Words that keep a turn relevant in any complaint call (the problem, feelings, a solution).
GENERAL_TOPIC = [
    "worry", "worried", "worries", "concern", "concerned", "upset", "angry", "frustrated", "frustrating",
    "disappointed", "feel", "feeling", "feelings", "happened", "problem", "situation", "understand", "help",
    "solution", "plan", "sorry", "apologize", "apologise", "together", "meet", "meeting", "suggest", "decision",
    "explain", "listen", "calm", "complaint", "issue", "agree", "promise", "fair", "unfair",
]
OUT_OF_ROLE = [
    r"\bas an? (ai|language model|assistant|chatbot)\b", r"\bi am an? (ai|language model|assistant|chatbot|bot)\b",
    r"\bim an? (ai|language model|assistant|chatbot|bot)\b", r"\b(ai|language) model\b",
    r"\bi (cannot|cant) (help|assist) with\b", r"\bsimulation\b", r"\brole-?play\b", r"\bprompt\b",
]
POLITE = re.compile(r"^(hi|hello|good (morning|afternoon|evening)|thank|thanks|bye|goodbye|have a (nice|good) day|"
                    r"see you|nice to (meet|hear))\b")
TOPIC_FREE_MOVES = {"HANG_UP", "CLOSE_CALL", "ACCEPT_PROPOSAL", "CONFIRM_AGREEMENT", "ACKNOWLEDGE_PARTIALLY",
                    "THREATEN_ESCALATION", "END_UNRESOLVED"}
STRATEGIC = {"S2", "S3", "S5", "S6", "S7", "A1", "A2", "A3"}
MAX_WORDS = 70


@dataclass
class FocusCheck:
    on_topic: bool
    injection: bool = False
    reason: str = ""
    topic_hits: list[str] = field(default_factory=list)


class FocusGuard:
    def __init__(self, scenario: Scenario):
        words = set(normalize(" ".join(scenario.topic_keywords)).split())
        for key in ("child", "parent_name", "issue_short", "main_issue_noun"):
            words.update(t for t in tokens(str(scenario.slots.get(key, ""))) if len(t) > 3)
        words.update(GENERAL_TOPIC)
        self.topic_words = words
        self._injection = [re.compile(p) for p in INJECTION]
        self._small_talk = [re.compile(p) for p in SMALL_TALK]
        self._out_of_role = [re.compile(p) for p in OUT_OF_ROLE]

    def topic_hits(self, text: str) -> list[str]:
        return sorted({t for t in tokens(text) if t in self.topic_words})

    def check_input(self, text: str, labels: list[str] | None = None) -> FocusCheck:
        norm = normalize(text)
        if any(rx.search(norm) for rx in self._injection):
            return FocusCheck(on_topic=False, injection=True, reason="pokušaj izlaska iz uloge")
        hits = self.topic_hits(text)
        if hits:
            return FocusCheck(on_topic=True, reason="tema", topic_hits=hits)
        if any(rx.search(norm) for rx in self._small_talk):
            return FocusCheck(on_topic=False, reason="mali razgovor ili druga tema")
        if labels and STRATEGIC & set(labels):
            return FocusCheck(on_topic=True, reason="strategija")
        if POLITE.search(norm):
            return FocusCheck(on_topic=True, reason="ljubaznost")
        if len(tokens(text)) <= 4:
            return FocusCheck(on_topic=True, reason="kratka replika")
        return FocusCheck(on_topic=False, reason="nema veze sa pritužbom")

    def validate_output(self, text: str, move: str | None = None) -> tuple[bool, str]:
        if not text or not text.strip():
            return False, "prazno"
        norm = normalize(text)
        if any(rx.search(norm) for rx in self._out_of_role):
            return False, "izlazi iz uloge"
        if word_count(text) > MAX_WORDS:
            return False, "predugačko"
        if move not in TOPIC_FREE_MOVES and not self.topic_hits(text):
            return False, "nije na temi"
        return True, "ok"
