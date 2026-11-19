import statistics

import yaml

from src.anger_meter import LexiconAngerMeter
from src.config import CONTENT_DIR
from src.safety import SafetyFilter


def test_meter_follows_intended_levels():
    meter = LexiconAngerMeter()
    pairs = yaml.safe_load((CONTENT_DIR / "rewriting" / "seed_pairs.yaml").read_text(encoding="utf-8"))["pairs"]
    by_level = {}
    hits = total = 0
    for pair in pairs:
        for level, text in pair["levels"].items():
            reading = meter.measure(text)
            by_level.setdefault(level, []).append(reading.score)
            hits += abs(reading.level - level) <= 1
            total += 1
    means = [statistics.mean(by_level[level]) for level in sorted(by_level)]
    assert means == sorted(means)
    assert hits / total >= 0.9


def test_reflection_is_not_the_speakers_anger():
    meter = LexiconAngerMeter()
    assert meter.measure("I can hear that you are really angry about the grade.").score < 1
    assert meter.measure("So you feel the grade is unfair.").score < 1
    assert meter.measure("I am really angry about this!").score > 3


def test_safety_blocks_abuse_but_allows_criticism():
    safety = SafetyFilter()
    assert safety.is_safe("This grade is ridiculous and the school is incompetent!")
    assert not safety.is_safe("You are an idiot.")
    assert not safety.is_safe("Damn it, fix this.")
    assert SafetyFilter(allow_mild_profanity=True).is_safe("Damn it, fix this.")
    assert not safety.is_safe("I will hurt you if this happens again.")
