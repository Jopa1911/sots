"""Turn detoxification datasets around (neutral -> harsh) and keep only pairs that suit the simulator.

    python data/build_rewrite_pairs.py

Input: data/raw/paradetox/paradetox.tsv, data/raw/appdia/original-*.tsv (data/download_rewrite_datasets.py).
Steps for every pair (offensive, neutral):
 1. reverse it: the neutral sentence is the input, the offensive one the target ("harsh");
 2. drop very short / very long sentences, links, and topics that do not belong in a school call
    (politics, religion, identity);
 3. drop the pair if the harsh side fails the safety filter (profanity, slurs, personal insults, violence),
    and pairs where the harsh side is not angrier than the neutral one;
 4. keep the pair only if every word the harsh side adds is an anger-lexicon word, an allowed criticism
    (ridiculous, useless, pathetic...), an intensifier or a function word: the change is then a change of tone
    that fits a parent-teacher call, not new (often offensive) content;
 5. label the anger level (2-5) with the anger meter.
Output: data/processed/rewrite_pairs.jsonl (not in git: derived from third-party data), used by the LLM rewriter
(few-shot examples) and data/train_rewriter.py.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS  # noqa: E402

from src.anger_meter import LexiconAngerMeter, load_lexicon  # noqa: E402
from src.safety import (  # noqa: E402
    ALLOWED_CRITICISM,  # noqa: E402
    SENSITIVE_TOPICS,
    URL,
    SafetyFilter,
)
from src.textutil import tokens, utf8_console, word_count  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "rewrite_pairs.jsonl"
csv.field_size_limit(10_000_000)
INTENSIFIERS = {"so", "really", "very", "totally", "completely", "absolutely", "utterly", "truly", "such", "just",
                "quite", "even", "ever", "at", "all", "again", "still", "seriously", "honestly", "clearly"}


def allowed_additions() -> set[str]:
    """Words the harsh side may add: anger lexicon, allowed criticism, intensifiers and function words."""
    lexicon_words = {w for phrase in load_lexicon() for w in phrase.split()}
    return lexicon_words | ALLOWED_CRITICISM | INTENSIFIERS | set(ENGLISH_STOP_WORDS)


def paradetox_pairs(path: Path):
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            for key in ("neutral1", "neutral2", "neutral3"):
                neutral = (row.get(key) or "").strip()
                if neutral:
                    yield row["toxic"].strip(), neutral, "paradetox"


def appdia_pairs(folder: Path):
    for path in sorted(folder.glob("original-*.tsv")):
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                offensive = (row.get("offensive-text") or "").strip()
                neutral = (row.get("style-transferred-text") or "").strip()
                if offensive and neutral:
                    yield offensive, neutral, "appdia"


def tidy_case(text: str) -> str:
    text = " ".join(text.split())
    text = text.replace(" ,", ",").replace(" .", ".").replace(" !", "!").replace(" ?", "?").replace(" '", "'")
    return text[:1].upper() + text[1:]


def main() -> None:
    utf8_console()
    sources = []
    if (RAW / "paradetox" / "paradetox.tsv").exists():
        sources.append(paradetox_pairs(RAW / "paradetox" / "paradetox.tsv"))
    if (RAW / "appdia").exists():
        sources.append(appdia_pairs(RAW / "appdia"))
    if not sources:
        sys.exit("Nema podataka. Pokrenite prvo: python data/download_rewrite_datasets.py")

    safety = SafetyFilter(allow_mild_profanity=False, allow_strong_insults=False)
    allowed = allowed_additions()
    meter = LexiconAngerMeter()
    stats, reasons, levels = Counter(), Counter(), Counter()
    kept = []
    for source in sources:
        for harsh, neutral, name in source:
            stats[f"{name}_all"] += 1
            harsh, neutral = tidy_case(harsh), tidy_case(neutral)
            if not (4 <= word_count(harsh) <= 40 and 3 <= word_count(neutral) <= 40):
                reasons["dužina"] += 1
                continue
            if URL.search(harsh + neutral) or SENSITIVE_TOPICS.search(harsh + " " + neutral):
                reasons["politika, identitet ili link"] += 1
                continue
            check = safety.check(harsh)
            if not check.allowed:
                reasons[check.reasons[0]] += 1
                continue
            added = set(tokens(harsh)) - set(tokens(neutral))
            if not added or not added <= allowed:
                reasons["dodate reči van rečnika ljutnje"] += 1
                continue
            if not safety.is_safe(neutral) or harsh.lower() == neutral.lower():
                reasons["neutralna strana"] += 1
                continue
            h, n = meter.measure(harsh), meter.measure(neutral)
            if h.score <= n.score or h.level < 2:
                reasons["nije ljuće od neutralne"] += 1
                continue
            kept.append({"neutral": neutral, "harsh": harsh, "level": h.level, "source": name,
                         "harsh_score": h.score, "neutral_score": n.score})
            stats[f"{name}_kept"] += 1
            levels[h.level] += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        for item in kept:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    for name in ("paradetox", "appdia"):
        if stats[f"{name}_all"]:
            print(f"{name}: {stats[f'{name}_all']} parova, zadržano {stats[f'{name}_kept']} "
                  f"({100 * stats[f'{name}_kept'] / stats[f'{name}_all']:.1f}%)")
    print("razlozi odbacivanja:", dict(reasons.most_common()))
    print("nivoi zadržanih parova:", dict(sorted(levels.items())))
    print(f"sačuvano: {OUT.relative_to(ROOT)} ({len(kept)} parova)")


if __name__ == "__main__":
    main()
