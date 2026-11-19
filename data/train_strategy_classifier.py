"""Train the ESConv strategy classifier (TF-IDF + logistic regression) for the teacher's sentences.

    python data/train_strategy_classifier.py [--esconv data/raw/esconv/ESConv.json]

- Data: supporter utterances of ESConv with their strategy (S1-S8).
- Split: by dialogue (80% / 20%), so that utterances of one dialogue are never in both parts.
- Reports accuracy and macro-F1 on the held-out dialogues and on our labelled teacher sentences
  (content/eval/teacher_sentences.yaml, school domain), then retrains on all data and saves
  models/strategy_clf.joblib. With CLASSIFIER_BACKEND=auto the agent uses it when the rules find no strategy.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import FeatureUnion, Pipeline

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.classifier import RuleClassifier  # noqa: E402
from src.strategies import ESCONV_LABELS, SUPPORT  # noqa: E402
from src.textutil import utf8_console  # noqa: E402


def load(path: Path) -> tuple[list[str], list[str], list[int]]:
    texts, labels, groups = [], [], []
    for i, dialogue in enumerate(json.loads(path.read_text(encoding="utf-8"))):
        for turn in dialogue["dialog"]:
            strategy = turn.get("annotation", {}).get("strategy")
            if turn["speaker"] == "supporter" and strategy in ESCONV_LABELS and turn["content"].strip():
                texts.append(turn["content"].strip())
                labels.append(ESCONV_LABELS[strategy])
                groups.append(i)
    return texts, labels, groups


def build_pipeline(c: float) -> Pipeline:
    features = FeatureUnion([
        ("words", TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, sublinear_tf=True)),
    ])
    return Pipeline([("features", features),
                     ("clf", LogisticRegression(C=c, max_iter=2000, class_weight="balanced"))])


def main() -> None:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--esconv", type=Path, default=ROOT / "data" / "raw" / "esconv" / "ESConv.json")
    parser.add_argument("--C", type=float, default=2.0)
    parser.add_argument("--out", type=Path, default=ROOT / "models" / "strategy_clf.joblib")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not args.esconv.exists():
        sys.exit(f"Nema {args.esconv}. Pokrenite prvo: python data/download_esconv.py")

    texts, labels, groups = load(args.esconv)
    X, y, g = np.array(texts, dtype=object), np.array(labels), np.array(groups)
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=args.seed).split(X, y, g))
    print(f"{len(texts)} replika: {len(train_idx)} za učenje, {len(test_idx)} za proveru "
          f"({len(set(g[test_idx]))} razgovora)")

    model = build_pipeline(args.C).fit(X[train_idx], y[train_idx])
    pred = model.predict(X[test_idx])
    acc, f1 = accuracy_score(y[test_idx], pred), f1_score(y[test_idx], pred, average="macro")
    majority = max(set(y[train_idx]), key=list(y[train_idx]).count)
    print(f"\nESConv (izdvojeni razgovori): tačnost={acc:.3f}  makro-F1={f1:.3f}  "
          f"(većinska klasa {majority}: {np.mean(y[test_idx] == majority):.3f})")
    print(classification_report(y[test_idx], pred, digits=3))

    eval_path = ROOT / "content" / "eval" / "teacher_sentences.yaml"
    eval_items = yaml.safe_load(eval_path.read_text(encoding="utf-8"))["sentences"]
    school = [(it["text"], it["labels"][0]) for it in eval_items
              if len(it["labels"]) == 1 and it["labels"][0] in SUPPORT]
    school_pred = model.predict([t for t, _ in school])
    school_acc = float(np.mean([p == gold for p, (_, gold) in zip(school_pred, school)]))
    rules = RuleClassifier()
    rules_acc = float(np.mean([rules.classify(t).primary == gold for t, gold in school]))
    print(f"Naše rečenice nastavnika (S1-S8, {len(school)}): ESConv model={school_acc:.3f}  pravila={rules_acc:.3f}")

    final = build_pipeline(args.C).fit(X, y)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    metrics = {"esconv_test_accuracy": round(acc, 3), "esconv_test_macro_f1": round(f1, 3),
               "school_accuracy": round(school_acc, 3), "rules_school_accuracy": round(rules_acc, 3),
               "n_train": int(len(train_idx)), "n_test": int(len(test_idx))}
    joblib.dump({"pipeline": final, "labels": SUPPORT, "metrics": metrics}, args.out)
    metrics_path = ROOT / "content" / "esconv" / "classifier_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"\nsačuvano: {args.out.relative_to(ROOT)} i content/esconv/classifier_metrics.json")


if __name__ == "__main__":
    main()
