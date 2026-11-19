"""Paths and settings. Settings come from environment variables or a local .env file (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
LOGS_DIR = ROOT / "logs"


def load_dotenv(path: Path | None = None) -> None:
    """Read KEY=VALUE lines from .env. Variables that are already set in the environment win."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if value[:1] in {'"', "'"}:
            value = value[1:].split(value[0], 1)[0]
        else:
            value = value.split(" #", 1)[0].strip()
        os.environ.setdefault(key.strip(), value)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int | None) -> int | None:
    value = os.environ.get(name)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "da"}


@dataclass
class Settings:
    # Language model (optional). "mock" = no model: templates and rules are used instead.
    llm_provider: str = "mock"            # mock | openai | groq | gemini | ollama (OpenAI-compatible APIs)
    llm_model: str = ""
    llm_base_url: str = ""
    llm_api_key: str = field(default="", repr=False)
    llm_temperature: float = 0.7
    llm_timeout: float = 30.0

    # Components. "auto" = best available backend, with an offline fallback.
    vanilla_backend: str = "auto"         # auto | template | llm
    rewriter_backend: str = "auto"        # auto | rules | llm | seq2seq
    rewriter_llm_model: str = ""          # optional separate model for the harsh rewrite (same provider)
    rewriter_model_dir: str = str(MODELS_DIR / "rewriter")
    classifier_backend: str = "auto"      # auto | rules | ml | llm
    classifier_model_path: str = str(MODELS_DIR / "strategy_clf.joblib")
    meter_backend: str = "lexicon"        # lexicon | hf | llm
    hf_emotion_model: str = "j-hartmann/emotion-english-distilroberta-base"

    # Safety of generated sentences.
    allow_mild_profanity: bool = False    # damn, hell, crap
    allow_strong_insults: bool = False    # idiot, stupid, moron

    # Generation and conversation.
    rewrite_candidates: int = 4
    teacher_anger_threshold: float = 5.0
    max_minutes: float = 8.0              # 0 = no time limit
    seed: int | None = None

    # Voice (optional).
    stt_backend: str = "none"             # none | faster-whisper
    tts_backend: str = "none"             # none | gtts | pyttsx3
    whisper_model: str = "base.en"

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            llm_provider=_env("LLM_PROVIDER", "mock").lower() or "mock",
            llm_model=_env("LLM_MODEL"),
            llm_base_url=_env("LLM_BASE_URL"),
            llm_api_key=_env("LLM_API_KEY"),
            llm_temperature=_env_float("LLM_TEMPERATURE", 0.7),
            llm_timeout=_env_float("LLM_TIMEOUT", 30.0),
            vanilla_backend=_env("VANILLA_BACKEND", "auto"),
            rewriter_backend=_env("REWRITER_BACKEND", "auto"),
            rewriter_llm_model=_env("REWRITER_LLM_MODEL"),
            rewriter_model_dir=_env("REWRITER_MODEL_DIR", str(MODELS_DIR / "rewriter")),
            classifier_backend=_env("CLASSIFIER_BACKEND", "auto"),
            classifier_model_path=_env("CLASSIFIER_MODEL_PATH", str(MODELS_DIR / "strategy_clf.joblib")),
            meter_backend=_env("METER_BACKEND", "lexicon"),
            hf_emotion_model=_env("HF_EMOTION_MODEL", "j-hartmann/emotion-english-distilroberta-base"),
            allow_mild_profanity=_env_bool("ALLOW_MILD_PROFANITY", False),
            allow_strong_insults=_env_bool("ALLOW_STRONG_INSULTS", False),
            rewrite_candidates=_env_int("REWRITE_CANDIDATES", 4) or 4,
            teacher_anger_threshold=_env_float("TEACHER_ANGER_THRESHOLD", 5.0),
            max_minutes=_env_float("MAX_MINUTES", 8.0),
            seed=_env_int("SEED", None),
            stt_backend=_env("STT_BACKEND", "none"),
            tts_backend=_env("TTS_BACKEND", "none"),
            whisper_model=_env("WHISPER_MODEL", "base.en"),
        )

    @property
    def llm_enabled(self) -> bool:
        return self.llm_provider not in {"", "mock", "none", "off"}

    def describe_llm(self) -> str:
        if not self.llm_enabled:
            return "isključen (šabloni i pravila)"
        return f"{self.llm_provider} {self.llm_model}".strip()

    def public_dict(self) -> dict:
        """Settings without the API key (for logs and the app)."""
        data = asdict(self)
        data["llm_api_key"] = "***" if self.llm_api_key else ""
        return data
