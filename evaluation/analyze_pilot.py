"""Pilot study analysis: self-confidence before/after, realism, SUS and the simulator results.

    python evaluation/analyze_pilot.py evaluation/pilot_podaci.csv [--out evaluation/rezultati.md]

The columns are described in evaluation/upitnici.md (template: evaluation/pilot_sablon.csv).
- SUS: odd items (x - 1), even items (5 - x), sum x 2.5 -> 0-100.
- Self-confidence: mean of items A1-A6 before and after; Wilcoxon signed-rank test (small sample, ordinal scale)
  and effect size r = |Z| / sqrt(N).
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd
from scipy.stats import wilcoxon

SE = [f"se{i}" for i in range(1, 7)]
REALISM = [f"real{i}" for i in range(1, 6)]


def sus_score(row: pd.Series) -> float:
    total = sum((row[f"sus{i}"] - 1) if i % 2 else (5 - row[f"sus{i}"]) for i in range(1, 11))
    return total * 2.5


def analyze(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["pre_se"] = df[[f"pre_{c}" for c in SE]].mean(axis=1)
    df["post_se"] = df[[f"post_{c}" for c in SE]].mean(axis=1)
    df["sus"] = df.apply(sus_score, axis=1)
    df["realism"] = df[REALISM].mean(axis=1)
    n = len(df)
    result = {
        "n": n,
        "pre_se_mean": round(df["pre_se"].mean(), 2), "post_se_mean": round(df["post_se"].mean(), 2),
        "se_change_mean": round((df["post_se"] - df["pre_se"]).mean(), 2),
        "realism_mean": round(df["realism"].mean(), 2),
        "realism_items": {c: round(df[c].mean(), 2) for c in REALISM},
        "sus_mean": round(df["sus"].mean(), 1), "sus_sd": round(df["sus"].std(ddof=1), 1) if n > 1 else None,
    }
    diff = df["post_se"] - df["pre_se"]
    if n >= 5 and (diff != 0).any():
        test = wilcoxon(df["post_se"], df["pre_se"], method="approx")
        z = getattr(test, "zstatistic", None)
        result.update({"wilcoxon_W": float(test.statistic), "p_value": round(float(test.pvalue), 4),
                       "effect_r": round(abs(z) / math.sqrt(n), 2) if z is not None else None})
    for sim in ("sim1", "sim2"):
        if f"{sim}_score" in df:
            result[f"{sim}_score_mean"] = round(df[f"{sim}_score"].mean(), 1)
        if f"{sim}_outcome" in df:
            result[f"{sim}_resolved_share"] = round((df[f"{sim}_outcome"] == "resolved").mean(), 2)
    return result


def to_markdown(r: dict) -> str:
    lines = ["# Rezultati pilot-studije", "", f"Broj učesnika: {r['n']}", "",
             "| Mera | Vrednost |", "|---|---|",
             f"| Samopouzdanje pre (1-5) | {r['pre_se_mean']} |",
             f"| Samopouzdanje posle (1-5) | {r['post_se_mean']} |",
             f"| Prosečna promena | {r['se_change_mean']:+} |"]
    if "p_value" in r:
        lines.append(f"| Wilcoxon W, p, r | {r['wilcoxon_W']}, {r['p_value']}, {r['effect_r']} |")
    lines += [f"| Realističnost (1-5) | {r['realism_mean']} |", f"| SUS (0-100) | {r['sus_mean']} (SD {r['sus_sd']}) |"]
    for sim in ("sim1", "sim2"):
        if f"{sim}_score_mean" in r:
            lines.append(f"| Simulator {sim[-1]}: poeni / udeo dogovora | {r[f'{sim}_score_mean']} / "
                         f"{r.get(f'{sim}_resolved_share', '-')} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    for stream in (sys.stdout, sys.stderr):  # Serbian letters also in Windows consoles
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    if df.empty:
        sys.exit("Tabela nema redova (popunite podatke prema evaluation/upitnici.md).")
    result = analyze(df)
    md = to_markdown(result)
    print(md)
    if args.out:
        args.out.write_text(md, encoding="utf-8")
        print(f"sačuvano: {args.out}")


if __name__ == "__main__":
    main()
