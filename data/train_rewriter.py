"""Fine-tune a separate seq2seq rewriter: "anger <level>: <neutral sentence>" -> harsh sentence (optional).

    pip install -r requirements-optional.txt
    python data/train_rewriter.py --dry-run                       # build and inspect the training data only
    python data/train_rewriter.py --model facebook/bart-base --epochs 8

Training data:
- our school pairs (content/rewriting/seed_pairs.yaml): every level of every sentence, oversampled;
- the filtered reversed ParaDetox/APPDIA pairs (data/processed/rewrite_pairs.jsonl, data/build_rewrite_pairs.py).
The model is saved to models/rewriter/; with REWRITER_BACKEND=auto the agent uses it before the rules.
After training, the held-out sentences are rewritten and checked with the anger meter and the safety filter.
A GPU is recommended (Google Colab is enough); the model is downloaded from Hugging Face.
"""

from __future__ import annotations

import argparse
import inspect
import json
import random
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.anger_meter import LexiconAngerMeter  # noqa: E402
from src.safety import SafetyFilter  # noqa: E402
from src.textutil import utf8_console  # noqa: E402

SEED = ROOT / "content" / "rewriting" / "seed_pairs.yaml"
EXTRA = ROOT / "data" / "processed" / "rewrite_pairs.jsonl"
OUT = ROOT / "models" / "rewriter"


def build_examples(oversample_seed: int = 5, extra_files: list[Path] | None = None) -> list[dict]:
    examples = []
    for pair in yaml.safe_load(SEED.read_text(encoding="utf-8"))["pairs"]:
        for level, text in pair["levels"].items():
            for _ in range(oversample_seed):
                examples.append({"input": f"anger {level}: {pair['vanilla']}", "target": text,
                                 "level": int(level), "source": "seed"})
    for path in [EXTRA, *(extra_files or [])]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            examples.append({"input": f"anger {item['level']}: {item['neutral']}", "target": item["harsh"],
                             "level": int(item["level"]), "source": item.get("source", path.stem)})
    return examples


def split(examples: list[dict], seed: int, valid_share: float = 0.1) -> tuple[list[dict], list[dict]]:
    """Hold out whole input sentences (all copies of one input go to the same side)."""
    inputs = sorted({e["input"] for e in examples})
    random.Random(seed).shuffle(inputs)
    valid_inputs = set(inputs[: max(1, int(len(inputs) * valid_share))])
    train = [e for e in examples if e["input"] not in valid_inputs]
    valid = [e for e in examples if e["input"] in valid_inputs]
    return train, list({e["input"]: e for e in valid}.values())


def _kwargs_for(cls, **wanted) -> dict:
    """transformers renamed some arguments between versions; pass whichever name this version accepts."""
    params = inspect.signature(cls.__init__).parameters
    out = {}
    for names, value in wanted.items():
        for name in names.split("|"):
            if name in params:
                out[name] = value
                break
    return out


def train(train_set: list[dict], valid_set: list[dict], model_name: str, epochs: int, batch: int, lr: float,
          seed: int) -> None:
    from datasets import Dataset
    from transformers import (
        AutoModelForSeq2SeqLM,
        AutoTokenizer,
        DataCollatorForSeq2Seq,
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
    )

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    def encode(batch_rows):
        enc = tokenizer(batch_rows["input"], max_length=128, truncation=True)
        enc["labels"] = tokenizer(text_target=batch_rows["target"], max_length=96, truncation=True)["input_ids"]
        return enc

    columns = ["input", "target"]
    train_ds = Dataset.from_list([{k: e[k] for k in columns} for e in train_set]).map(encode, batched=True,
                                                                                     remove_columns=columns)
    valid_ds = Dataset.from_list([{k: e[k] for k in columns} for e in valid_set]).map(encode, batched=True,
                                                                                     remove_columns=columns)
    args = Seq2SeqTrainingArguments(
        output_dir=str(OUT / "checkpoints"), per_device_train_batch_size=batch, per_device_eval_batch_size=batch,
        learning_rate=lr, num_train_epochs=epochs, weight_decay=0.01, seed=seed, logging_steps=20,
        save_strategy="no", report_to=[],
        **_kwargs_for(Seq2SeqTrainingArguments, **{"eval_strategy|evaluation_strategy": "epoch"}),
    )
    trainer = Seq2SeqTrainer(
        model=model, args=args, train_dataset=train_ds, eval_dataset=valid_ds,
        data_collator=DataCollatorForSeq2Seq(tokenizer, model=model),
        **_kwargs_for(Seq2SeqTrainer, **{"processing_class|tokenizer": tokenizer}),
    )
    trainer.train()
    OUT.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(OUT))
    tokenizer.save_pretrained(str(OUT))
    print(f"model sačuvan: {OUT.relative_to(ROOT)}")

    meter, safety = LexiconAngerMeter(), SafetyFilter()
    hits = safe = 0
    model.eval()
    for e in valid_set:
        ids = tokenizer([e["input"]], return_tensors="pt").to(model.device)
        out = model.generate(**ids, max_new_tokens=80, num_beams=4)
        text = tokenizer.decode(out[0], skip_special_tokens=True)
        hits += meter.measure(text).level == e["level"]
        safe += safety.is_safe(text)
    n = max(1, len(valid_set))
    report = {"valid_sentences": len(valid_set), "level_exact": round(hits / n, 3), "safe": round(safe / n, 3)}
    (OUT / "eval.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("provera na izdvojenim rečenicama:", report)


def main() -> None:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="facebook/bart-base")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--oversample-seed", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--extra", type=Path, nargs="*", default=[],
                        help="more pairs (JSONL with neutral, harsh, level), e.g. from python -m src.alternatives "
                             "--pairs-out with an LLM rewriter")
    parser.add_argument("--dry-run", action="store_true", help="only build the data and print statistics")
    args = parser.parse_args()

    examples = build_examples(args.oversample_seed, args.extra)
    train_set, valid_set = split(examples, args.seed)
    print(f"primera: {len(examples)} (učenje {len(train_set)}, provera {len(valid_set)} rečenica)")
    print("po izvoru:", dict(Counter(e["source"] for e in examples)))
    print("po nivou:", dict(sorted(Counter(e["level"] for e in examples).items())))
    for e in random.Random(args.seed).sample(train_set, min(4, len(train_set))):
        print(f"  {e['input']}  ->  {e['target']}")
    out = ROOT / "data" / "processed" / "rewriter_train.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in train_set), encoding="utf-8")
    if args.dry_run:
        print(f"samo priprema, bez učenja; podaci: {out.relative_to(ROOT)}")
        return
    try:
        train(train_set, valid_set, args.model, args.epochs, args.batch, args.lr, args.seed)
    except ImportError:
        sys.exit("Potrebni su transformers, datasets i torch: pip install -r requirements-optional.txt")


if __name__ == "__main__":
    main()
