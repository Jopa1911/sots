"""Safety of generated sentences: the parent may be harsh, but never abusive.

Allowed: strong criticism (unfair, ridiculous, incompetent, useless), rhetorical questions, ultimatums.
Blocked by default: profanity, slurs and sexual words (better-profanity word list), personal insults (idiot,
stupid...), threats of violence. Mild swear words (damn, hell, crap) can be allowed with ALLOW_MILD_PROFANITY.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .textutil import normalize

MILD_PROFANITY = {"damn", "damned", "hell", "crap", "crappy", "darn", "bloody"}
PERSONAL_INSULTS = {"idiot", "idiots", "idiotic", "moron", "morons", "moronic", "stupid", "dumb", "imbecile",
                    "loser", "losers", "fool", "fools", "retard", "retarded"}
ALLOWED_CRITICISM = {"incompetent", "clueless", "useless", "ridiculous", "nonsense", "pathetic", "joke",
                     "disgrace", "disgraceful", "outrageous", "unacceptable", "shameful", "lazy"}
VIOLENCE = [
    r"\b(kill|hurt|beat|punch|slap|shoot|stab|smash)\b\s+(you|him|her|them|your)\b",
    r"\bburn\b.*\bschool\b", r"\bi will (find|get|come for) you\b", r"\byou will (regret|pay)\b",
    r"\bwatch your back\b",
]
# Topics that do not belong in a parent-teacher call; used to filter example pairs from external datasets.
SENSITIVE_TOPICS = re.compile(
    r"\b(biden|trump|putin|clinton|obama|hillary|israel|palestin\w*|republicans?|democrats?|liberals?|"
    r"conservatives?|leftists?|muslims?|islam\w*|christians?|jews?|jewish|gays?|lesbians?|trans|immigrants?|"
    r"refugees?|racists?|racism|nazis?|abortion|guns?|police|cops?|election|vote|voters?|president|congress|"
    r"senate|canada|america|americans?|china|chinese|russia\w*|ukrain\w*|hawaii|australian?)\b", re.IGNORECASE)
URL = re.compile(r"https?://|www\.", re.IGNORECASE)
_FALLBACK_STRONG = [r"\bf+u+c+k", r"\bs+h+i+t+\b", r"\bb+i+t+c+h", r"\ba+s+s+h+o+l+e", r"\bbastard",
                    r"\bdick\b", r"\bcunt", r"\bwhore", r"\bslut"]


@dataclass
class SafetyResult:
    allowed: bool
    reasons: list[str] = field(default_factory=list)


class SafetyFilter:
    def __init__(self, allow_mild_profanity: bool = False, allow_strong_insults: bool = False):
        self.allow_mild = allow_mild_profanity
        self.allow_insults = allow_strong_insults
        self._violence = [re.compile(p) for p in VIOLENCE]
        self._fallback = [re.compile(p) for p in _FALLBACK_STRONG]
        try:
            from better_profanity import profanity  # optional, recommended

            profanity.load_censor_words()
            self._profanity = profanity
        except Exception:
            self._profanity = None

    def check(self, text: str) -> SafetyResult:
        norm = normalize(text)
        words = set(re.findall(r"[a-z]+", norm))
        reasons = []
        if any(rx.search(norm) for rx in self._violence):
            reasons.append("pretnja nasiljem")
        if not self.allow_insults and words & PERSONAL_INSULTS:
            reasons.append("lična uvreda")
        if not self.allow_mild and words & MILD_PROFANITY:
            reasons.append("blaga psovka")
        handled = MILD_PROFANITY | PERSONAL_INSULTS | ALLOWED_CRITICISM
        masked = " ".join("x" if w in handled else w for w in re.findall(r"[a-z]+", norm))
        if any(rx.search(masked) for rx in self._fallback) or \
                (self._profanity is not None and self._profanity.contains_profanity(masked)):
            reasons.append("psovka ili neprikladna reč")
        return SafetyResult(allowed=not reasons, reasons=reasons)

    def is_safe(self, text: str) -> bool:
        return self.check(text).allowed
