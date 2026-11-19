"""Small text helpers shared by the modules (no external dependencies)."""

from __future__ import annotations

import re
from functools import lru_cache

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "`": "'"})
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_TOKEN = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    """Lower-case, unify quotes, drop apostrophes ("don't" -> "dont") and collapse spaces."""
    text = (text or "").translate(_APOSTROPHES).lower().replace("'", "")
    return re.sub(r"\s+", " ", text).strip()


def tokens(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text))


def sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split((text or "").strip())]
    return [p for p in parts if p]


@lru_cache(maxsize=4096)
def _phrase_regex(phrase: str) -> re.Pattern:
    words = [re.escape(w) for w in normalize(phrase).split()]
    return re.compile(r"\b" + r"\s+".join(words) + r"\b")


def has_phrase(normalized_text: str, phrase: str) -> bool:
    """True if `phrase` occurs in an already normalized text as whole words."""
    return bool(_phrase_regex(phrase).search(normalized_text))


def tidy(text: str) -> str:
    """Clean up spacing and punctuation after rule-based edits; capitalise sentence starts."""
    text = re.sub(r"\s+", " ", text or "").strip()
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r",\s*([.!?])", r"\1", text)
    text = re.sub(r"([.!?])\s*\.", r"\1", text)
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = re.sub(r"^[,.;:\s]+", "", text)

    def cap(match: re.Match) -> str:
        return match.group(1) + match.group(2).upper()

    text = re.sub(r"(^|[.!?]\s+)([a-z])", cap, text)
    return text


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def utf8_console() -> None:
    """Print Serbian letters and arrows also in consoles that default to another encoding (Windows, Git Bash)."""
    import sys

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
