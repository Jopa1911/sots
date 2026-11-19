"""Download the parallel datasets used (in reverse) for the harsh rewriter into data/raw/.

    python data/download_rewrite_datasets.py

- ParaDetox (Logacheva et al., ACL 2022): toxic sentence + 1-3 neutral paraphrases (19,743 pairs).
  github.com/s-nlp/paradetox; the repository LICENSE is CC0 1.0 (the Hugging Face card lists OpenRAIL++).
- APPDIA (Atwell, Hassan, Alikhani, COLING 2022): offensive Reddit comment + inoffensive rewrite (1,981 pairs).
  github.com/sabithsn/APPDIA-Discourse-Style-Transfer; no license file in the repository, so the data is
  used only for research and is not redistributed here.

WARNING: both datasets contain very offensive language. data/build_rewrite_pairs.py filters it out.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.textutil import utf8_console  # noqa: E402

RAW = ROOT / "data" / "raw"
SOURCES = {
    "paradetox/paradetox.tsv": "https://raw.githubusercontent.com/s-nlp/paradetox/main/paradetox/paradetox.tsv",
    **{f"appdia/original-{part}.tsv":
       "https://raw.githubusercontent.com/sabithsn/APPDIA-Discourse-Style-Transfer/main/data/"
       f"original-annotated-data/original-{part}.tsv" for part in ("train", "dev", "test")},
}


def main() -> None:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    for rel, url in SOURCES.items():
        target = RAW / rel
        if target.exists() and not args.force:
            print(f"postoji: {target.relative_to(ROOT)}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                target.write_bytes(response.read())
        except OSError as exc:
            sys.exit(f"Preuzimanje {url} nije uspelo: {exc}")
        print(f"preuzeto: {target.relative_to(ROOT)} ({target.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
