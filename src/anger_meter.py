"""Anger in text (0-10): measures the teacher's turns and checks the generated parent sentences.

Backends:
- LexiconAngerMeter (default, offline): anger lexicon + cues of anger in writing (exclamations, capitals,
  accusations, threats, demands, rhetorical questions) minus politeness markers. The weights are set by hand;
  data/calibrate_meter.py compares them with weights fitted on our vanilla -> harsh pairs.
- HFAngerMeter: the "anger" probability of a Hugging Face emotion classifier, mixed with the lexicon score.
- LLMAngerMeter: asks a language model for a 0-10 rating and falls back to the lexicon.
Only anger is measured.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import CONTENT_DIR, Settings
from .levels import level_for
from .llm import BaseLLM, parse_number
from .textutil import normalize, sentences

LEXICON_PATH = CONTENT_DIR / "lexicon" / "anger_seed_lexicon.tsv"
WEIGHTS_PATH = CONTENT_DIR / "lexicon" / "meter_weights.json"
SCALE = 4.0  # score = 10 * (1 - exp(-raw / SCALE))

# Emotion words: when they describe the OTHER person ("you must be angry") they are a reflection, not anger.
EMOTION_LABELS = {"angry", "upset", "frustrated", "annoyed", "mad", "furious", "irritated", "disappointed",
                  "worried", "unhappy", "frustrating", "upsetting", "livid", "outraged", "disappointing"}
FIRST_PERSON = {"i", "im", "me", "we", "ive", "my", "id", "ill"}
# Paraphrases and reflections ("so you feel the grade is unfair") repeat the other person's words; the part of the
# clause after such a frame is not counted as the speaker's anger. The scope ends at "but" / "however".
REFLECTION_FRAME = re.compile(
    r"\b(you (feel|felt|think|thought|believe|mean|said|say|are saying|were saying|must be|must feel|might be|"
    r"seem)|youre (saying|feeling)|sounds like|it sounds|it seems|i can (hear|see|imagine)|i hear|i see that|"
    r"i understand (that|why|how|you)|if i understand|in other words|what (i am|im) hearing)\b")
CLAUSE_SPLIT = re.compile(r"([.!?;]|\bbut\b|\bhowever\b)")
SECOND_PERSON = {"you", "youre", "your", "youve", "must", "sounds", "sound", "seem", "seems", "hear", "imagine"}

CUES = {
    "accusation": [r"\byou (never|always)\b", r"\byour (fault|job|responsibility)\b", r"\bwhat kind of\b",
                   r"\bhow (could|can|dare) you\b", r"\byou people\b", r"\bblame\b", r"\bthat is your job\b",
                   r"\byou kept\b", r"\bnobody (seems to|ever) care"],
    "threat": [r"\bprincipal\b", r"\blawyer\b", r"\breport (you|this)\b", r"\bministry\b", r"\binspector\b",
               r"\bor else\b", r"\bthis call is over\b", r"\byou will hear from\b", r"\bi mean it\b"],
    "demand": [r"\bi demand\b", r"\bright now\b", r"\bimmediately\b", r"\bi want (answers|a solution|an answer)\b",
               r"\banswer (me|my question)\b", r"\bexplain (it|this) to me\b", r"\byou need to\b", r"\btoday\b",
               r"\bfix this\b", r"\bnot next month\b", r"\bi expect\b"],
    "rhetorical": [r"\bdo you even\b", r"\bare you even\b", r"\bare you (kidding|serious)\b", r"\bhow is that\b",
                   r"\bwhat on earth\b", r"\bwhat is going on\b", r"\byou think\b[^.!]*\?", r"\bwhy (on earth|would)\b",
                   r"\bwhat kind of\b[^.!]*\?", r"\bthe day before\?"],
    "dismissal": [r"\bwaste of (my )?time\b", r"\bdont insult\b", r"\bbrush me off\b", r"\bstop (hiding|dodging)\b",
                  r"\bdont (you dare|try|change the subject|think)\b", r"\bi am done\b", r"\bim done\b",
                  r"\benough\b", r"\bnot enough\b", r"\bi have had enough\b"],
    "dissatisfaction": [r"\bfrankly\b", r"\bexpected better\b", r"\b(does not|doesnt) (add up|really help)\b",
                        r"\bleast you can do\b", r"\bnot how it should (work|be)\b", r"\bhope this is the last time\b",
                        r"\bi mean that\b", r"\bnot happy\b", r"\bstill (dont|do not) have an answer\b",
                        r"\bi need to (see|hear)\b", r"\breally bothers me\b", r"\bi will say it again\b",
                        r"\bsomething (is wrong|does not add up|doesnt add up)\b", r"\bi expected a call\b",
                        r"\bkeep your word\b", r"\bhold you to that\b", r"\bnot okay\b", r"\bnot over\b"],
    "opener": [r"^(listen|look|seriously|enough|no|stop right there|well)\b[,.!?]"],
    "imperative": [r"(^|[.!?] )(explain|fix|answer|stop|tell|give|show|listen) (me|this|it|my|to|the)\b"],
}
POLITENESS = [r"\bplease\b", r"\bthank you\b", r"\bthanks\b", r"\bi understand\b", r"\bi appreciate\b",
              r"\bcould you\b", r"\bwould you\b", r"\bwould it be possible\b", r"\bsorry\b",
              r"\bif you have a moment\b",
              r"\bi would like\b", r"\bthat sounds fair\b", r"\btogether\b", r"\bi wish\b", r"\bmay need\b",
              r"\bi am not sure\b", r"\ba bit\b"]
CAPS = {"lexicon": 3.0, "exclamation": 3, "caps": 2, "politeness": 3, "profanity": 1, "opener": 1}

DEFAULT_WEIGHTS = {"lexicon": 2.2, "exclamation": 0.7, "caps": 1.4, "accusation": 1.4, "threat": 1.2,
                   "demand": 0.9, "rhetorical": 1.4, "dismissal": 1.1, "dissatisfaction": 1.3, "opener": 1.0,
                   "imperative": 0.9, "profanity": 3.0, "politeness": -0.9}
FEATURES = list(DEFAULT_WEIGHTS)


@dataclass
class AngerReading:
    score: float
    level: int
    features: dict = field(default_factory=dict)
    source: str = "lexicon"


def load_lexicon(path: str | Path = LEXICON_PATH) -> dict[str, float]:
    lexicon: dict[str, float] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            try:
                lexicon[normalize(parts[0])] = float(parts[1])
            except ValueError:
                continue
    return lexicon


def load_weights(path: str | Path = WEIGHTS_PATH) -> dict[str, float]:
    weights = dict(DEFAULT_WEIGHTS)
    p = Path(path)
    if p.exists():
        stored = json.loads(p.read_text(encoding="utf-8")).get("weights", {})
        weights.update({k: float(v) for k, v in stored.items() if k in weights})
    return weights


class LexiconAngerMeter:
    name = "lexicon"

    def __init__(self, lexicon: dict[str, float] | None = None, weights: dict[str, float] | None = None):
        self.lexicon = dict(lexicon or load_lexicon())
        self.phrase_patterns = [
            (re.compile(r"\b" + r"\s+".join(map(re.escape, p.split())) + r"\b"), p)
            for p in sorted((p for p in self.lexicon if " " in p), key=len, reverse=True)
        ]
        self.words = {w: v for w, v in self.lexicon.items() if " " not in w}
        self.weights = dict(weights or load_weights())
        self._cues = {k: [re.compile(p) for p in v] for k, v in CUES.items()}
        self._polite = [re.compile(p) for p in POLITENESS]
        try:
            from better_profanity import profanity  # optional
            profanity.load_censor_words()
            self._profanity = profanity
        except Exception:
            self._profanity = None

    @staticmethod
    def _is_reflection(words: list[str], i: int) -> bool:
        """'you must be angry' / 'how frustrated you are' describe the listener, not the speaker."""
        for w in reversed(words[max(0, i - 4):i]):
            if w in FIRST_PERSON:
                return False
            if w in SECOND_PERSON:
                return True
        following = words[i + 1:i + 3]
        return bool(following) and following[0] in {"you", "youre", "for"}

    def lexicon_score(self, norm: str) -> tuple[float, list[str]]:
        hits, total, text = [], 0.0, f" {norm} "
        for pattern, phrase in self.phrase_patterns:
            if pattern.search(text):
                total += self.lexicon[phrase]
                hits.append(phrase)
                text = pattern.sub(" ", text)
        words = re.findall(r"[a-z]+", text)
        for i, word in enumerate(words):
            value = self.words.get(word)
            if not value:
                continue
            if word in EMOTION_LABELS and self._is_reflection(words, i):
                continue
            if i > 0 and words[i - 1] in {"not", "no", "never", "dont"} and word in EMOTION_LABELS:
                continue
            total += value
            hits.append(word)
        return total, hits

    @staticmethod
    def strip_reflections(norm: str) -> str:
        parts = CLAUSE_SPLIT.split(norm)
        kept = []
        for part in parts:
            match = REFLECTION_FRAME.search(part)
            kept.append(part[:match.end()] if match else part)
        return "".join(kept)

    def features(self, text: str) -> dict:
        text = text or ""
        norm = self.strip_reflections(normalize(text))
        lex, hits = self.lexicon_score(norm)
        caps = [w for w in re.findall(r"\b[A-Z]{3,}\b", text) if w not in {"OK", "TV", "AI"}]
        feats = {"lexicon": lex, "lexicon_hits": hits, "exclamation": text.count("!"), "caps": len(caps),
                 "politeness": sum(1 for rx in self._polite if rx.search(norm)), "profanity": 0}
        sentence_norms = [normalize(s) for s in sentences(text)] or [norm]
        for cue, patterns in self._cues.items():
            if cue == "opener":
                feats[cue] = sum(1 for s in sentence_norms if any(rx.search(s) for rx in patterns))
            else:
                feats[cue] = sum(1 for rx in patterns if rx.search(norm))
        if self._profanity is not None and self._profanity.contains_profanity(text):
            feats["profanity"] = 1
        for key in FEATURES:
            feats[key] = min(feats.get(key, 0), CAPS.get(key, 2))
        return feats

    def raw_score(self, feats: dict) -> float:
        return max(sum(self.weights[k] * feats.get(k, 0) for k in FEATURES), 0.0)

    def measure(self, text: str) -> AngerReading:
        feats = self.features(text)
        raw = self.raw_score(feats)
        score = round(10 * (1 - math.exp(-raw / SCALE)), 2)
        feats["raw"] = round(raw, 3)
        return AngerReading(score=score, level=level_for(score), features=feats, source=self.name)


class HFAngerMeter:
    """Mixes the lexicon score with the 'anger' probability of a transformers emotion classifier."""

    name = "hf"

    def __init__(self, model_name: str, lexicon_meter: LexiconAngerMeter | None = None, weight: float = 0.5):
        from transformers import pipeline  # optional dependency

        self.classifier = pipeline("text-classification", model=model_name, top_k=None)
        self.lexicon = lexicon_meter or LexiconAngerMeter()
        self.weight = weight

    def measure(self, text: str) -> AngerReading:
        base = self.lexicon.measure(text)
        output = self.classifier(text[:512])
        scores = output[0] if output and isinstance(output[0], list) else output
        anger = next((s["score"] for s in scores if s["label"].lower() == "anger"), 0.0)
        score = round((1 - self.weight) * base.score + self.weight * 10 * anger, 2)
        feats = dict(base.features, hf_anger=round(anger, 3))
        return AngerReading(score=score, level=level_for(score), features=feats, source=self.name)


class LLMAngerMeter:
    name = "llm"
    system = ("Rate how ANGRY the speaker of the sentence sounds, from 0 (calm, polite) to 10 (furious, "
              "about to hang up). Reply with one number only.")

    def __init__(self, llm: BaseLLM, fallback: LexiconAngerMeter | None = None):
        self.llm, self.fallback = llm, fallback or LexiconAngerMeter()

    def measure(self, text: str) -> AngerReading:
        try:
            value = parse_number(self.llm.complete(self.system, [{"role": "user", "content": text}],
                                                   max_tokens=10, temperature=0.0))
            score = max(0.0, min(10.0, value))
            return AngerReading(score=score, level=level_for(score), features={}, source=self.name)
        except Exception:
            return self.fallback.measure(text)


def get_meter(settings: Settings, llm: BaseLLM | None = None):
    backend = settings.meter_backend.lower()
    base = LexiconAngerMeter()
    if backend == "hf":
        try:
            return HFAngerMeter(settings.hf_emotion_model, base)
        except Exception:
            return base
    if backend == "llm" and llm is not None:
        return LLMAngerMeter(llm, base)
    return base
