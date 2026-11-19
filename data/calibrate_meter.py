"""Calibrate the anger meter weights on our vanilla -> harsh pairs (content/rewriting/seed_pairs.yaml).

Each sentence has an intended anger level (vanilla = level 1). The meter turns text features into a raw score;
here the feature weights are fitted so that the raw score lands in the band of the intended level.
Method: non-negative least squares with a pull towards the hand-set default weights (ridge, lambda),
evaluated with leave-one-pair-out cross-validation (all versions of one sentence are held out together).

    python data/calibrate_meter.py          # report: default weights vs fitted weights (CV)
    python data/calibrate_meter.py --save   # also write the fitted weights to content/lexicon/meter_weights.json

Result on 62 sentences (see DNEVNIK.md): the fitted weights do not beat the hand-set default weights in
cross-validation, so the meter keeps the defaults (no meter_weights.json). Rerun after adding more pairs.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import nnls
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anger_meter import DEFAULT_WEIGHTS, FEATURES, SCALE, WEIGHTS_PATH, LexiconAngerMeter  # noqa: E402
from src.levels import band_center, level_for  # noqa: E402
from src.textutil import utf8_console  # noqa: E402

PAIRS_PATH = ROOT / "content" / "rewriting" / "seed_pairs.yaml"
# Politeness lowers the score: it is fitted as a positive weight on the negative count.
SIGN = {k: (-1.0 if DEFAULT_WEIGHTS[k] < 0 else 1.0) for k in FEATURES}


def raw_target(level: int) -> float:
    score = band_center(level)
    return -SCALE * math.log(1 - score / 10)


def load_examples() -> list[tuple[int, str, int]]:
    pairs = yaml.safe_load(PAIRS_PATH.read_text(encoding="utf-8"))["pairs"]
    rows = []
    for group, pair in enumerate(pairs):
        rows.append((group, pair["vanilla"], 1))
        for level, text in pair["levels"].items():
            rows.append((group, text, int(level)))
    return rows


def fit(X: np.ndarray, y: np.ndarray, lam: float) -> np.ndarray:
    w0 = np.array([abs(DEFAULT_WEIGHTS[k]) for k in FEATURES])
    A = np.vstack([X, math.sqrt(lam) * np.eye(len(FEATURES))])
    b = np.concatenate([y, math.sqrt(lam) * w0])
    w, _ = nnls(A, b)
    return w


def predict_levels(X: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    raw = np.clip(X @ w, 0, None)
    score = 10 * (1 - np.exp(-raw / SCALE))
    return score, np.array([level_for(s) for s in score])


def report(name: str, gold: np.ndarray, pred: np.ndarray, score: np.ndarray) -> dict:
    exact = float(np.mean(gold == pred))
    within1 = float(np.mean(np.abs(gold - pred) <= 1))
    rho = float(spearmanr(gold, score).correlation)
    print(f"{name:<46} tačan nivo={exact:.3f}  ±1 nivo={within1:.3f}  Spearman={rho:.3f}")
    return {"exact": round(exact, 3), "within1": round(within1, 3), "spearman": round(rho, 3)}


def main() -> None:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--lam", type=float, default=0.5, help="pull towards the default weights")
    parser.add_argument("--save", action="store_true", help="write the fitted weights (used by the meter)")
    args = parser.parse_args()

    meter = LexiconAngerMeter(weights=DEFAULT_WEIGHTS)
    rows = load_examples()
    groups = np.array([g for g, _, _ in rows])
    gold = np.array([lvl for _, _, lvl in rows])
    X = np.array([[SIGN[k] * meter.features(text)[k] for k in FEATURES] for _, text, _ in rows], dtype=float)
    y = np.array([raw_target(lvl) for lvl in gold])
    print(f"{len(rows)} rečenica u {len(set(groups))} parova\n")

    w_default = np.array([abs(DEFAULT_WEIGHTS[k]) for k in FEATURES])
    score, pred = predict_levels(X, w_default)
    before = report("ručne težine (sve rečenice)", gold, pred, score)

    cv_pred, cv_score = np.zeros_like(gold), np.zeros(len(gold))
    for g in sorted(set(groups)):
        test = groups == g
        w = fit(X[~test], y[~test], args.lam)
        cv_score[test], cv_pred[test] = predict_levels(X[test], w)
    cv = report("naučene težine, unakrsna provera po parovima", gold, cv_pred, cv_score)

    w_all = fit(X, y, args.lam)
    score, pred = predict_levels(X, w_all)
    train = report("naučene težine (sve rečenice, optimistično)", gold, pred, score)

    weights = {k: round(float(SIGN[k] * w), 3) for k, w in zip(FEATURES, w_all)}
    print("\nnaučene težine:", json.dumps(weights))
    confusion = np.zeros((5, 5), dtype=int)
    for g_, p_ in zip(gold, cv_pred):
        confusion[g_ - 1, p_ - 1] += 1
    print("\nmatrica konfuzije, unakrsna provera (red = zadati nivo 1-5, kolona = izmereni nivo 1-5):")
    for i, row in enumerate(confusion, 1):
        print(f"  {i}: {' '.join(f'{v:3d}' for v in row)}")

    report_path = ROOT / "content" / "lexicon" / "meter_report.json"
    report_path.write_text(json.dumps({
        "n_sentences": len(rows), "lambda": args.lam,
        "metrics": {"default_weights": before, "fitted_cv": cv, "fitted_train": train},
        "fitted_weights": weights, "confusion_cv": confusion.tolist(),
    }, indent=2), encoding="utf-8")
    print(f"\nsačuvano: {report_path.relative_to(ROOT)}")
    if args.save:
        WEIGHTS_PATH.write_text(json.dumps({
            "weights": weights,
            "lambda": args.lam,
            "n_sentences": len(rows),
            "metrics": {"default": before, "cv": cv, "train": train},
            "confusion_cv": confusion.tolist(),
        }, indent=2), encoding="utf-8")
        print(f"sačuvano: {WEIGHTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
