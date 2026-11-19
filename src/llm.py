"""Optional language model behind an OpenAI-compatible /chat/completions API (OpenAI, Groq, Gemini, local Ollama...).

Only the standard library is used. With LLM_PROVIDER=mock, get_llm() returns None and every component falls back
to templates and rules. ScriptedLLM returns prepared replies and is used in the tests.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any, Callable, Iterable

from .config import Settings

DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
}


class LLMError(RuntimeError):
    """A model call failed; the caller falls back to the offline backend."""


def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read()[:400].decode("utf-8", "replace")
        raise LLMError(f"HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise LLMError(str(exc)) from exc


class BaseLLM:
    name = "base"

    def complete(self, system: str, messages: list[dict], max_tokens: int = 300,
                 temperature: float | None = None) -> str:
        raise NotImplementedError


class OpenAICompatClient(BaseLLM):
    name = "openai-compatible"

    def __init__(self, model: str, api_key: str = "", base_url: str = DEFAULT_BASE_URLS["openai"],
                 temperature: float = 0.7, timeout: float = 30.0):
        if not model:
            raise ValueError("LLM_MODEL is required.")
        self.model, self.api_key, self.base_url = model, api_key, base_url.rstrip("/")
        self.temperature, self.timeout = temperature, timeout

    def complete(self, system: str, messages: list[dict], max_tokens: int = 300,
                 temperature: float | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, *messages],
            "max_tokens": max_tokens,
            "temperature": self.temperature if temperature is None else temperature,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = _post_json(f"{self.base_url}/chat/completions", payload, headers, self.timeout)
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected response: {str(data)[:200]}") from exc
        if not text.strip():
            raise LLMError("Empty response from the model.")
        return text.strip()


class ScriptedLLM(BaseLLM):
    """Returns prepared replies in order (or from a function) and records every prompt it receives."""

    name = "scripted"

    def __init__(self, replies: Iterable[str] | Callable[[str, list[dict]], str]):
        self._fn = replies if callable(replies) else None
        self._replies = None if callable(replies) else list(replies)
        self.calls: list[tuple[str, list[dict]]] = []

    def complete(self, system: str, messages: list[dict], max_tokens: int = 300,
                 temperature: float | None = None) -> str:
        self.calls.append((system, messages))
        if self._fn is not None:
            return self._fn(system, messages)
        if not self._replies:
            raise LLMError("No scripted replies left.")
        return self._replies.pop(0)


def get_llm(settings: Settings, model: str | None = None) -> BaseLLM | None:
    """The configured client, or None without a model (LLM_PROVIDER=mock).

    `model` overrides LLM_MODEL; it is used for a separate rewriter model (REWRITER_LLM_MODEL)."""
    if not settings.llm_enabled:
        return None
    provider = settings.llm_provider.lower()
    if provider not in {"openai", *DEFAULT_BASE_URLS}:
        raise ValueError(f"Unknown LLM_PROVIDER: {settings.llm_provider}")
    return OpenAICompatClient(
        model=model or settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url or DEFAULT_BASE_URLS.get(provider, DEFAULT_BASE_URLS["openai"]),
        temperature=settings.llm_temperature,
        timeout=settings.llm_timeout,
    )


def parse_json(text: str) -> Any:
    """Parse the first JSON object or list in a model reply (models sometimes add text around it)."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    candidates = []
    for opener, closer in (("[", "]"), ("{", "}")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            candidates.append((start, text[start:end + 1]))
    for _, chunk in sorted(candidates):  # the structure that starts first is the outer one
        try:
            return json.loads(chunk)
        except json.JSONDecodeError:
            continue
    raise ValueError("No JSON found in the model reply.")


def parse_number(text: str) -> float:
    match = re.search(r"-?\d+(?:\.\d+)?", text or "")
    if not match:
        raise ValueError("No number found in the model reply.")
    return float(match.group())
