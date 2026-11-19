"""Build the ESConv resources used by the agent: statistics and the precedence relation of strategies.

    python data/build_esconv_resources.py [--esconv data/raw/esconv/ESConv.json] [--threshold 70]

Writes:
- content/esconv/relation.json  matrix "a first appears before b" (% of dialogues with both), edges >= threshold,
                                 Hasse edges (transitive reduction), and the same matrix for anger dialogues;
- content/esconv/stats.json      counts used in DNEVNIK.md, section 2.
The relation is used by the evaluator (src/evaluator.py) to score the order of the teacher's strategies.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.strategies import ESCONV_LABELS  # noqa: E402
from src.textutil import utf8_console  # noqa: E402

ORDER = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
EXAMPLES = {"S1": (22, 3), "S2": (124, 6), "S3": (1268, 3), "S4": (858, 3), "S5": (124, 17), "S6": (249, 33),
            "S7": (449, 42), "S8": (22, 1)}


def precedence(dialogues: list[dict]) -> tuple[dict, dict]:
    both, before = Counter(), Counter()
    for dialogue in dialogues:
        first: dict[str, int] = {}
        for i, turn in enumerate(dialogue["dialog"]):
            if turn["speaker"] == "supporter" and turn.get("annotation", {}).get("strategy") in ESCONV_LABELS:
                first.setdefault(ESCONV_LABELS[turn["annotation"]["strategy"]], i)
        for a, b in permutations(first, 2):
            both[a, b] += 1
            before[a, b] += first[a] < first[b]
    matrix = {b: {a: (round(100 * before[a, b] / both[a, b]) if a != b and both[a, b] else None) for a in ORDER}
              for b in ORDER}
    counts = {f"{a}>{b}": both[a, b] for a in ORDER for b in ORDER if a != b}
    return matrix, counts


def hasse(edges: set[tuple[str, str]]) -> list[tuple[str, str]]:
    """Transitive reduction: drop a->c when a->b and b->c exist."""
    reduced = set(edges)
    for a, c in edges:
        if any((a, b) in edges and (b, c) in edges for b in ORDER if b not in (a, c)):
            reduced.discard((a, c))
    return sorted(reduced)


def main() -> None:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--esconv", type=Path, default=ROOT / "data" / "raw" / "esconv" / "ESConv.json")
    parser.add_argument("--threshold", type=int, default=70)
    args = parser.parse_args()
    if not args.esconv.exists():
        sys.exit(f"Nema {args.esconv}. Pokrenite prvo: python data/download_esconv.py")

    dialogues = json.loads(args.esconv.read_text(encoding="utf-8"))
    matrix, counts = precedence(dialogues)
    edges = {(a, b) for b in ORDER for a in ORDER if matrix[b][a] is not None and matrix[b][a] >= args.threshold}
    anger = [d for d in dialogues if d.get("emotion_type") == "anger"]
    anger_matrix, _ = precedence(anger)

    strategies = Counter(ESCONV_LABELS[t["annotation"]["strategy"]] for d in dialogues for t in d["dialog"]
                         if t["speaker"] == "supporter" and t.get("annotation", {}).get("strategy") in ESCONV_LABELS)
    pairs = []
    for d in dialogues:
        seeker = d.get("survey_score", {}).get("seeker", {})
        try:
            pairs.append((int(seeker["initial_emotion_intensity"]), int(seeker["final_emotion_intensity"])))
        except (KeyError, TypeError, ValueError):
            continue
    stats = {
        "dialogues": len(dialogues),
        "utterances": sum(len(d["dialog"]) for d in dialogues),
        "supporter_labelled": sum(strategies.values()),
        "strategies": {k: strategies[k] for k in ORDER},
        "anger_dialogues": len(anger),
        "intensity_pairs": len(pairs),
        "intensity_before": round(statistics.mean(p[0] for p in pairs), 2) if pairs else None,
        "intensity_after": round(statistics.mean(p[1] for p in pairs), 2) if pairs else None,
        "problem_types": dict(Counter(d.get("problem_type") for d in dialogues).most_common()),
        "examples": {sid: {"text": dialogues[i]["dialog"][j]["content"].strip(), "ref": f"{i}/{j}"}
                     for sid, (i, j) in EXAMPLES.items()},
    }
    relation = {
        "source": "ESConv.json (Liu et al., 2021)",
        "description": "matrix[b][a] = % of dialogues (with both strategies) in which a is first used before b",
        "threshold": args.threshold,
        "labels": ORDER,
        "matrix": matrix,
        "pair_counts": counts,
        "edges_all": sorted(edges),
        "edges": hasse(edges),
        "anger": {"dialogues": len(anger), "matrix": anger_matrix},
    }
    out = ROOT / "content" / "esconv"
    out.mkdir(parents=True, exist_ok=True)
    (out / "relation.json").write_text(json.dumps(relation, indent=2), encoding="utf-8")
    (out / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"{stats['dialogues']} razgovora, {stats['utterances']} replika, {stats['supporter_labelled']} označenih")
    print("Tabela odnosa (red = kasnija, kolona = ranija strategija):")
    print("     " + " ".join(f"{a:>4}" for a in ORDER))
    for b in ORDER:
        print(f"{b:>4} " + " ".join(f"{'-' if matrix[b][a] is None else matrix[b][a]:>4}" for a in ORDER))
    print("Haseove veze (>= {}%):".format(args.threshold), ", ".join(f"{a}->{b}" for a, b in relation["edges"]))
    print(f"Ljutnja ({len(anger)} razgovora): S3 pre S6 u {anger_matrix['S6']['S3']}% razgovora")
    print("sačuvano: content/esconv/relation.json, content/esconv/stats.json")


if __name__ == "__main__":
    main()
