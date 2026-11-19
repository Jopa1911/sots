"""Optional voice: speech-to-text for the teacher and text-to-speech for the parent.

STT_BACKEND=faster-whisper  local Whisper model (pip install faster-whisper); WHISPER_MODEL=base.en by default
TTS_BACKEND=gtts            Google Translate TTS, needs internet (pip install gTTS)
TTS_BACKEND=pyttsx3         offline system voice (pip install pyttsx3)
Without these packages the app works with text only.
"""

from __future__ import annotations

import io
import os
import tempfile

from .config import Settings

_whisper_cache: dict = {}


def stt_available(settings: Settings) -> bool:
    if settings.stt_backend != "faster-whisper":
        return False
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def tts_available(settings: Settings) -> bool:
    module = {"gtts": "gtts", "pyttsx3": "pyttsx3"}.get(settings.tts_backend)
    if not module:
        return False
    try:
        __import__(module)
    except ImportError:
        return False
    return True


def transcribe(audio: bytes, settings: Settings) -> str:
    """WAV/MP3 bytes -> English text."""
    from faster_whisper import WhisperModel

    model = _whisper_cache.get(settings.whisper_model)
    if model is None:
        model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
        _whisper_cache[settings.whisper_model] = model
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
        fh.write(audio)
        path = fh.name
    try:
        segments, _ = model.transcribe(path, language="en")
        return " ".join(s.text.strip() for s in segments).strip()
    finally:
        os.unlink(path)


def synthesize(text: str, settings: Settings) -> tuple[bytes, str] | None:
    """Text -> (audio bytes, mime type), or None if no voice backend is available."""
    if settings.tts_backend == "gtts":
        from gtts import gTTS

        buffer = io.BytesIO()
        gTTS(text=text, lang="en").write_to_fp(buffer)
        return buffer.getvalue(), "audio/mp3"
    if settings.tts_backend == "pyttsx3":
        import pyttsx3

        engine = pyttsx3.init()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as fh:
            path = fh.name
        try:
            engine.save_to_file(text, path)
            engine.runAndWait()
            with open(path, "rb") as fh:
                return fh.read(), "audio/wav"
        finally:
            os.unlink(path)
    return None
