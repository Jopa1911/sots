"""Alternatives: the same parent move (same content) at every anger level 1-5.

This is how the anger is controlled: the conversation template fixes WHAT the parent says, the level decides HOW.

    python -m src.alternatives                    # all scenarios and moves -> content/generated/alternatives.md
    python -m src.alternatives --scenario bad_grade --move DEMAND_ACTION --variants 3
    python -m src.alternatives --pairs-out data/processed/generated_pairs.jsonl   # pairs for train_rewriter.py
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

from .config import CONTENT_DIR, DATA_DIR, Settings
from .generator import AngerPipeline
from .levels import NAMES_EN
from .scenario import Scenario, list_scenarios, load_scenario
from .template import ConversationTemplate, fill_slots
from .textutil import utf8_console

OUT_DIR = CONTENT_DIR / "generated"
JSONL_PATH = DATA_DIR / "processed" / "alternatives.jsonl"


def example_slots(scenario: Scenario) -> dict:
    slots = dict(scenario.slots)
    slots["next_detail"] = scenario.details[0] if scenario.details else ""
    other = next((c for c in scenario.complaints if not c.main), scenario.complaints[0])
    slots["next_complaint"] = other.say
    slots["next_condition"] = other.condition
    return slots


def generate(scenarios: list[str], moves: list[str] | None = None, variants: int = 1, seed: int = 1,
             settings: Settings | None = None, llm=None) -> list[dict]:
    settings = settings or Settings(llm_provider="mock", seed=seed)
    template = ConversationTemplate.load()
    rows = []
    for scenario_id in scenarios:
        scenario = load_scenario(scenario_id)
        pipeline = AngerPipeline(template, scenario, settings, llm=llm, rng=random.Random(seed))
        slots = example_slots(scenario)
        for move_name in moves or list(template.moves):
            move = template.move(move_name)
            for v in range(variants):
                vanilla = None
                if llm is None and move.vanilla:
                    vanilla = fill_slots(move.vanilla[v % len(move.vanilla)], slots)
                results = pipeline.alternatives(move_name, slots, vanilla=vanilla)
                if not results:
                    continue
                rows.append({
                    "scenario": scenario.id, "move": move_name, "phase": move.phase, "variant": v,
                    "guidelines": results[0].guidelines, "vanilla": results[0].vanilla,
                    "levels": {r.target_level: {"text": r.text, "score": r.score, "measured_level": r.level,
                                                "source": r.source} for r in results},
                })
    return rows


def to_markdown(rows: list[dict]) -> str:
    lines = ["# Alternativne replike roditelja po nivou ljutnje", "",
             "Generisano komandom `python -m src.alternatives` (pravila, bez jezičkog modela). Isti potez i isti "
             "sadržaj, različit nivo ljutnje; u zagradi je izmereni nivo.", ""]
    for scenario in sorted({r["scenario"] for r in rows}):
        lines += [f"## {scenario}", ""]
        for row in (r for r in rows if r["scenario"] == scenario and r["variant"] == 0):
            lines += [f"### {row['move']} ({row['phase']})", "", f"*Smernica:* {row['guidelines']}", "",
                      f"*Vanila rečenica:* {row['vanilla']}", ""]
            for level, item in sorted(row["levels"].items()):
                lines.append(f"- **{level} – {NAMES_EN[int(level)]}** ({item['measured_level']}): {item['text']}")
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", nargs="*", default=None)
    parser.add_argument("--move", nargs="*", default=None)
    parser.add_argument("--variants", type=int, default=2)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--use-llm", action="store_true",
                        help="jezički model iz .env za vanila rečenicu i prepisivanje")
    parser.add_argument("--pairs-out", type=Path, default=None)
    args = parser.parse_args()

    llm, settings = None, Settings(llm_provider="mock", seed=args.seed)
    if args.use_llm:
        from .llm import get_llm

        settings = Settings.from_env()
        llm = get_llm(settings)
    rows = generate(args.scenario or list_scenarios(), args.move, args.variants, args.seed, settings, llm)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "alternatives.md").write_text(to_markdown(rows), encoding="utf-8")
    JSONL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSONL_PATH, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    diffs = Counter(abs(int(level) - item["measured_level"]) for r in rows for level, item in r["levels"].items())
    total = sum(diffs.values())
    print(f"{len(rows)} poteza, {total} rečenica; izmereni nivo = ciljni: {diffs[0] / total:.0%}, "
          f"razlika 1: {diffs[1] / total:.0%}, više: {(total - diffs[0] - diffs[1]) / total:.0%}")
    print(f"sačuvano: {OUT_DIR / 'alternatives.md'} (i {JSONL_PATH})")
    if args.pairs_out:
        with open(args.pairs_out, "w", encoding="utf-8") as fh:
            for r in rows:
                for level, item in r["levels"].items():
                    if int(level) > 1 and item["measured_level"] == int(level):
                        fh.write(json.dumps({"neutral": r["vanilla"], "harsh": item["text"], "level": int(level),
                                             "source": f"generated-{item['source']}"}, ensure_ascii=False) + "\n")
        print(f"parovi za učenje: {args.pairs_out}")


if __name__ == "__main__":
    main()
