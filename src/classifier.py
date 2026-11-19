"""Recognising the teacher's strategies in a turn (several labels per turn are possible).

Backends:
- RuleClassifier: weighted regular expressions (content/classifier_patterns.yaml). Offline, always available.
- MLClassifier: TF-IDF + logistic regression trained on ESConv (data/train_strategy_classifier.py), S1-S8 only.
- LLMClassifier: asks a language model; escalating behaviours (A1-A3) always come from the rules.
- HybridClassifier ("auto"): rules first; the ESConv model decides when the rules find no strategy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import CONTENT_DIR, Settings
from .llm import BaseLLM, parse_json
from .strategies import ESCALATING, SUPPORT, load_cards
from .textutil import normalize, sentences

PATTERNS_PATH = CONTENT_DIR / "classifier_patterns.yaml"
SUPPORT_THRESHOLD = 2.0
# "How about...?" is a suggestion phrased as a question: it counts as S6, not as S1.
SUGGESTION_QUESTION = re.compile(r"^(how about|what if|shall we|could we|can we|why dont we|would you like|"
                                 r"would it help if|what do you think about|do you want to)\b")


@dataclass
class Classification:
    labels: list[str]
    primary: str
    scores: dict[str, float] = field(default_factory=dict)
    source: str = "rules"

    @property
    def escalating(self) -> bool:
        return any(label in ESCALATING for label in self.labels)


class RuleClassifier:
    name = "rules"

    def __init__(self, path: str | Path | None = None):
        data = yaml.safe_load(Path(path or PATTERNS_PATH).read_text(encoding="utf-8"))
        self.anti_threshold = float(data.get("anti_threshold", 2.5))
        self.priority = list(data.get("priority", SUPPORT))
        self.patterns = {
            label: [(re.compile(p), float(w)) for p, w in pats]
            for label, pats in data["patterns"].items()
        }

    def sentence_scores(self, sentence: str) -> dict[str, float]:
        norm = normalize(sentence)
        scores = {label: sum(w for rx, w in pats if rx.search(norm)) for label, pats in self.patterns.items()}
        if SUGGESTION_QUESTION.search(norm) and scores.get("S6", 0) > 0:
            scores["S6"] = max(scores["S6"], SUPPORT_THRESHOLD)
            scores["S1"] = 0.0
        return scores

    def scores(self, text: str) -> dict[str, float]:
        """Maximum score of each label over the sentences of the turn."""
        total = {label: 0.0 for label in self.patterns}
        for sentence in sentences(text) or [text]:
            for label, score in self.sentence_scores(sentence).items():
                total[label] = max(total[label], score)
        return total

    def classify(self, text: str) -> Classification:
        scores = self.scores(text)
        anti = [a for a in ESCALATING if scores.get(a, 0) >= self.anti_threshold]
        support = [s for s in self.priority if s != "S8" and scores.get(s, 0) >= SUPPORT_THRESHOLD]
        if not anti and not support and scores.get("S8", 0) > 0:
            support = ["S8"]
        labels = anti + support or ["S8"]
        return Classification(labels=labels, primary=labels[0], scores=scores, source=self.name)


class MLClassifier:
    """Wraps the model saved by data/train_strategy_classifier.py (a dict with a sklearn pipeline)."""

    name = "esconv-ml"

    def __init__(self, path: str | Path):
        import joblib  # optional dependency, imported only when the model is used

        bundle = joblib.load(path)
        self.pipeline = bundle["pipeline"]
        self.labels = list(bundle["labels"])
        self.metrics = bundle.get("metrics", {})

    def proba(self, text: str) -> dict[str, float]:
        probs = self.pipeline.predict_proba([text])[0]
        classes = list(self.pipeline.classes_)
        return {c: float(p) for c, p in zip(classes, probs)}

    def classify(self, text: str) -> Classification:
        probs = self.proba(text)
        best = max(probs, key=probs.get)
        return Classification(labels=[best], primary=best, scores=probs, source=self.name)


class HybridClassifier:
    """Rules for escalating behaviours and clear strategies; the ESConv model when the rules are unsure."""

    name = "rules+ml"

    def __init__(self, rules: RuleClassifier, ml: MLClassifier | None = None, min_prob: float = 0.5):
        self.rules, self.ml, self.min_prob = rules, ml, min_prob

    def classify(self, text: str) -> Classification:
        result = self.rules.classify(text)
        if self.ml is None or result.labels != ["S8"] or len(text.split()) < 4:
            return result
        probs = self.ml.proba(text)
        best = max(probs, key=probs.get)
        if best != "S8" and probs[best] >= self.min_prob:
            scores = dict(result.scores)
            scores[f"ml:{best}"] = probs[best]
            return Classification(labels=[best], primary=best, scores=scores, source=self.name)
        return result


LLM_SYSTEM = """You label what a TEACHER says to an angry PARENT on the phone.
Choose every label that applies:
{definitions}
Reply with JSON only, for example {{"labels": ["S3", "S1"]}}. Use S8 when nothing else applies."""


class LLMClassifier:
    name = "llm"

    def __init__(self, llm: BaseLLM, rules: RuleClassifier):
        self.llm, self.rules = llm, rules
        cards = load_cards()
        lines = [f"{sid}: {cards[sid].name} - {cards[sid].definition}" for sid in SUPPORT + ESCALATING]
        self.system = LLM_SYSTEM.format(definitions="\n".join(lines))

    def classify(self, text: str) -> Classification:
        rule_result = self.rules.classify(text)
        try:
            reply = self.llm.complete(self.system, [{"role": "user", "content": f'Teacher: "{text}"'}],
                                      max_tokens=60, temperature=0.0)
            labels = [str(x).upper() for x in parse_json(reply).get("labels", [])]
            labels = [x for x in labels if x in SUPPORT + ESCALATING]
        except Exception:
            return rule_result
        for anti in rule_result.labels:
            if anti in ESCALATING and anti not in labels:
                labels.insert(0, anti)
        if not labels:
            return rule_result
        ordered = [x for x in ESCALATING if x in labels] + [x for x in self.rules.priority if x in labels]
        return Classification(labels=ordered, primary=ordered[0], scores=rule_result.scores, source=self.name)


def get_classifier(settings: Settings, llm: BaseLLM | None = None):
    rules = RuleClassifier()
    backend = settings.classifier_backend.lower()
    model_path = Path(settings.classifier_model_path)
    if backend == "rules":
        return rules
    if backend == "llm" and llm is not None:
        return LLMClassifier(llm, rules)
    if backend in {"ml", "auto"} and model_path.exists():
        try:
            ml = MLClassifier(model_path)
        except Exception:
            return rules
        return ml if backend == "ml" else HybridClassifier(rules, ml)
    return rules
