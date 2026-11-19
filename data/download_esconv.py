"""Download ESConv (Liu et al., 2021) from GitHub into data/raw/esconv/.

    python data/download_esconv.py

License: CC BY-NC 4.0 (academic, non-commercial use). The files are not stored in this repository.
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.textutil import utf8_console  # noqa: E402

BASE = "https://raw.githubusercontent.com/thu-coai/Emotional-Support-Conversation/main/"
FILES = ["ESConv.json", "FailedESConv.json", "strategy.json", "LICENSE"]


def download(dest: Path, force: bool = False) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = dest / name
        if target.exists() and not force:
            print(f"postoji: {target.relative_to(ROOT)}")
            continue
        print(f"preuzimam {name} ...", end=" ", flush=True)
        with urllib.request.urlopen(BASE + name, timeout=60) as response:
            target.write_bytes(response.read())
        print(f"{target.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    utf8_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=ROOT / "data" / "raw" / "esconv")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        download(args.dest, args.force)
    except OSError as exc:
        sys.exit(f"Preuzimanje nije uspelo ({exc}). Alternativa: "
                 "git clone https://github.com/thu-coai/Emotional-Support-Conversation data/raw/esconv")


if __name__ == "__main__":
    main()
