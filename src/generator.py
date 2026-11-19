"""Anger generation: rough guidelines -> neutral (vanilla) sentence -> harsh rewrite -> check.

1. VanillaGenerator writes WHAT the parent says: a language model follows the move's rough guidelines and writes
   a neutral sentence; without a model, a template sentence is filled with the scenario facts.
2. A rewriter changes only HOW it is said, for the target anger level 1-5:
   - RuleRewriter (offline): level-specific word changes, openers and move-specific additions;
   - LLMRewriter: a prompt with examples (our pairs + similar reversed ParaDetox/APPDIA pairs);
   - Seq2SeqRewriter: a fine-tuned model "anger <level>: <vanilla>" -> harsh (data/train_rewriter.py).
3. AngerPipeline measures every candidate with the anger meter, drops unsafe or off-topic ones and keeps the one
   whose measured level is closest to the target and that does not repeat what the parent already said.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from .anger_meter import LexiconAngerMeter
from .config import CONTENT_DIR, DATA_DIR, Settings
from .focus import FocusGuard
from .levels import band_center, level_for
from .llm import BaseLLM, LLMError, parse_json
from .safety import SafetyFilter
from .scenario import Scenario
from .template import ConversationTemplate, Move, fill_slots
from .textutil import normalize, sentences, tidy

SEED_PAIRS_PATH = CONTENT_DIR / "rewriting" / "seed_pairs.yaml"
EXTRA_PAIRS_PATH = DATA_DIR / "processed" / "rewrite_pairs.jsonl"
REWRITER_NAMES_SR = {"rules": "pravila", "llm": "jezički model", "seq2seq": "seq2seq model"}


@dataclass
class Candidate:
    text: str
    source: str
    score: float = 0.0
    level: int = 1
    safe: bool = True
    focused: bool = True
    notes: list[str] = field(default_factory=list)

    @property
    def acceptable(self) -> bool:
        return self.safe and self.focused


@dataclass
class GenerationResult:
    move: str
    target_level: int
    guidelines: str
    vanilla: str
    vanilla_source: str
    text: str
    source: str
    score: float
    level: int
    candidates: list[Candidate] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------------------------------------
# 1. Vanilla sentence
# ---------------------------------------------------------------------------------------------------------
VANILLA_SYSTEM = """You play {parent_name}, the {relation} of {child}, in a phone call with {child}'s teacher.
This is a training simulator for teachers.
Situation: {description}
Facts you can use: {facts}
What really worries you (say it only when the guideline asks for it): {hidden_need}

Rules:
- Stay in this role and talk only about this situation. Never say that you are an AI, a model or a simulation.
- Write what you say next: one to three short spoken sentences.
- Write a NEUTRAL version: no emotion words, no insults, no exclamation marks. Another model adds the anger later.
- Follow the guideline for this turn. Do not invent facts that are not listed above.
Return only the sentence(s), without quotes."""


def format_history(history: list[dict], limit: int = 6) -> str:
    lines = []
    for item in history[-limit:]:
        who = "Teacher" if item.get("role") == "teacher" else "You"
        lines.append(f"{who}: {item.get('text', '')}")
    return "\n".join(lines) or "(the call is starting)"


def _clean_reply(text: str) -> str:
    text = (text or "").strip().strip('"').strip()
    text = re.sub(r"^(you|parent|me|[A-Z][a-z]+ [A-Z][a-z]+)\s*:\s*", "", text)
    return " ".join(text.split())


class VanillaGenerator:
    def __init__(self, template: ConversationTemplate, scenario: Scenario, llm: BaseLLM | None = None,
                 focus: FocusGuard | None = None, safety: SafetyFilter | None = None,
                 rng: random.Random | None = None, mode: str = "auto"):
        self.template, self.scenario, self.llm = template, scenario, llm
        self.focus = focus or FocusGuard(scenario)
        self.safety = safety or SafetyFilter()
        self.rng = rng or random.Random()
        self.mode = mode

    def system_prompt(self) -> str:
        s, p = self.scenario, self.scenario.parent
        facts = " ".join(s.details) + " Complaints: " + " ".join(c.text for c in s.complaints)
        return VANILLA_SYSTEM.format(parent_name=p.get("name", "the parent"), relation=p.get("relation", "parent"),
                                     child=p.get("child", "the child"), description=s.description, facts=facts,
                                     hidden_need=p.get("hidden_need", ""))

    def guidelines(self, move: Move, slots: dict) -> str:
        return fill_slots(move.guidelines or move.intent, slots)

    def from_llm(self, move: Move, slots: dict, history: list[dict]) -> str | None:
        if self.llm is None or self.mode == "template":
            return None
        user = (f"Conversation so far:\n{format_history(history)}\n\n"
                f"Guideline for your next turn ({move.name}): {self.guidelines(move, slots)}\n"
                f"Your next turn (neutral):")
        for _ in range(2):
            try:
                text = _clean_reply(self.llm.complete(self.system_prompt(), [{"role": "user", "content": user}],
                                                      max_tokens=150))
            except LLMError:
                return None
            ok, _ = self.focus.validate_output(text, move.name)
            if ok and self.safety.is_safe(text):
                return text.replace("!", ".")
        return None

    def generate(self, move: Move, slots: dict, history: list[dict] | None = None) -> tuple[str, str]:
        text = self.from_llm(move, slots, history or [])
        if text:
            return text, "llm"
        return self.template.vanilla_text(move, slots, self.rng), "template"


# ---------------------------------------------------------------------------------------------------------
# 2. Rewriters: vanilla -> harsh
# ---------------------------------------------------------------------------------------------------------
class RuleRewriter:
    """Offline rewriter driven by the template: rewrite rules, openers, harsh additions, punctuation, capitals."""

    name = "rules"

    def __init__(self, template: ConversationTemplate, rng: random.Random | None = None):
        self.template = template
        self.rng = rng or random.Random()
        self._rules = [(lvl, re.compile(rx), repl) for lvl, rx, repl in template.rewrite_rules]

    def base(self, text: str, level: int) -> str:
        for min_level, rx, repl in self._rules:
            if level >= min_level:
                text = rx.sub(repl, text)
        text = tidy(text)
        if level >= 4:
            text = re.sub(r"\.$", "!", text)
        return text

    def emphasise(self, text: str) -> str:
        """Level 5: write one emphasis word in capitals (if the sentence has none yet)."""
        if re.search(r"\b[A-Z]{3,}\b", text):
            return text
        for word in self.template.emphasis_words:
            pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
            if pattern.search(text):
                return pattern.sub(word.upper(), text, count=1)
        return text

    def rewrite(self, text: str, level: int, move: Move, n: int = 4) -> list[str]:
        if level <= 1:
            return [tidy(text)]
        base = self.base(text, level)
        additions = move.harsh_for(level)
        generic = list(self.template.generic_harsh.get(level, []))
        openers = list(self.template.openers.get(level, []))
        self.rng.shuffle(generic)
        self.rng.shuffle(openers)
        options = []
        for add in additions:
            options.append(f"{base} {add}")
        if generic:
            options.append(f"{base} {generic[0]}")
        greeting = re.match(r"^(hello|hi|good (morning|afternoon|evening))\b", base, re.IGNORECASE)
        if openers and additions and not greeting:
            options.append(f"{openers[0]} {self._lower_first(base)} {additions[0]}")
        if level >= 4 and generic and additions:
            options.append(f"{base} {generic[-1]} {additions[-1]}")
        if not options:
            options.append(base)
        out = []
        for option in options:
            option = tidy(option)
            if level >= 5:
                option = self.emphasise(option)
            if option not in out:
                out.append(option)
        self.rng.shuffle(out)
        return out[:n]

    @staticmethod
    def _lower_first(text: str) -> str:
        if len(text) > 1 and text[0].isupper() and not text[:2].isupper() and not text.startswith("I "):
            first = re.sub(r"[^\w']", "", text.split(" ", 1)[0])
            if first.lower() in {"this", "that", "the", "nobody", "you", "your", "and", "so", "what", "all",
                                 "well", "fine", "let's", "we", "if", "before", "hello", "good"}:
                return text[0].lower() + text[1:]
        return text


class PairStore:
    """Examples for the LLM rewriter: our seed pairs + (optionally) similar reversed pairs from ParaDetox/APPDIA."""

    def __init__(self, seed_path: Path = SEED_PAIRS_PATH, extra_path: Path = EXTRA_PAIRS_PATH):
        data = yaml.safe_load(Path(seed_path).read_text(encoding="utf-8"))
        self.seed = [(p["vanilla"], {int(k): v for k, v in p["levels"].items()}) for p in data["pairs"]]
        self.extra: list[dict] = []
        if Path(extra_path).exists():
            with open(extra_path, encoding="utf-8") as fh:
                self.extra = [json.loads(line) for line in fh if line.strip()]
        self._index = None
        if self.extra:
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer

                self._vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
                self._index = self._vectorizer.fit_transform([e["neutral"] for e in self.extra])
            except Exception:
                self._index = None

    def examples(self, text: str, level: int, k_seed: int = 3, k_extra: int = 3) -> list[tuple[str, str]]:
        out = [(v, levels[level]) for v, levels in self.seed if level in levels][:k_seed]
        if self._index is not None and k_extra:
            from sklearn.metrics.pairwise import linear_kernel

            sims = linear_kernel(self._vectorizer.transform([text]), self._index).ravel()
            for i in sims.argsort()[::-1]:
                item = self.extra[i]
                if abs(int(item.get("level", level)) - level) <= 1:
                    out.append((item["neutral"], item["harsh"]))
                if len(out) >= k_seed + k_extra:
                    break
        return out


REWRITE_SYSTEM = """You rewrite what an upset parent says to a teacher on the phone (a teacher-training simulator).
Keep the meaning and every fact. Change only the tone, to anger level {level} of 5: {style}.
Allowed: strong criticism, rhetorical questions, demands, ultimatums, mentioning the principal.
Not allowed: swear words, slurs, personal insults such as idiot or stupid, threats of violence, anything sexual.
Keep it short (at most three sentences) and on the topic of the call.

Examples (neutral -> level {level}):
{examples}

Reply with a JSON list of {n} different versions, nothing else."""


class LLMRewriter:
    name = "llm"

    def __init__(self, llm: BaseLLM, template: ConversationTemplate, store: PairStore | None = None):
        self.llm, self.template = llm, template
        self.store = store or PairStore()

    def prompt(self, text: str, level: int, n: int) -> str:
        examples = "\n".join(f'- "{a}" -> "{b}"' for a, b in self.store.examples(text, level))
        return REWRITE_SYSTEM.format(level=level, style=self.template.level_style(level), examples=examples, n=n)

    def rewrite(self, text: str, level: int, move: Move, n: int = 3) -> list[str]:
        if level <= 1:
            return [text]
        reply = self.llm.complete(self.prompt(text, level, n), [{"role": "user", "content": f'Neutral: "{text}"'}],
                                  max_tokens=400)
        items = parse_json(reply)
        if isinstance(items, dict):
            items = items.get("versions") or items.get("rewrites") or list(items.values())
        return [_clean_reply(str(x)) for x in items if str(x).strip()][:n]


class Seq2SeqRewriter:
    """Fine-tuned seq2seq model (input "anger <level>: <vanilla>"). Requires transformers + torch."""

    name = "seq2seq"

    def __init__(self, model_dir: str | Path):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer  # optional dependency

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_dir)

    def rewrite(self, text: str, level: int, move: Move, n: int = 4) -> list[str]:
        if level <= 1:
            return [text]
        inputs = self.tokenizer([f"anger {level}: {text}"], return_tensors="pt", truncation=True, max_length=128)
        outputs = self.model.generate(**inputs, do_sample=True, top_p=0.9, num_return_sequences=n,
                                      max_new_tokens=80)
        return [self.tokenizer.decode(o, skip_special_tokens=True).strip() for o in outputs]


# ---------------------------------------------------------------------------------------------------------
# 3. Pipeline with verification
# ---------------------------------------------------------------------------------------------------------
class AngerPipeline:
    def __init__(self, template: ConversationTemplate, scenario: Scenario, settings: Settings | None = None,
                 llm: BaseLLM | None = None, rewriter_llm: BaseLLM | None = None, meter=None,
                 safety: SafetyFilter | None = None, focus: FocusGuard | None = None,
                 rng: random.Random | None = None):
        self.settings = settings or Settings()
        self.template, self.scenario = template, scenario
        self.rng = rng or random.Random(self.settings.seed)
        self.meter = meter or LexiconAngerMeter()
        self.safety = safety or SafetyFilter(self.settings.allow_mild_profanity, self.settings.allow_strong_insults)
        self.focus = focus or FocusGuard(scenario)
        self.vanilla = VanillaGenerator(template, scenario, llm, self.focus, self.safety, self.rng,
                                        mode=self.settings.vanilla_backend)
        self.rewriters = self._build_rewriters(rewriter_llm or llm)

    def _build_rewriters(self, llm: BaseLLM | None) -> list:
        backend = self.settings.rewriter_backend.lower()
        chain: list = []
        if backend in {"auto", "seq2seq"} and Path(self.settings.rewriter_model_dir).exists():
            try:
                chain.append(Seq2SeqRewriter(self.settings.rewriter_model_dir))
            except Exception:
                pass
        if backend in {"auto", "llm"} and llm is not None:
            chain.append(LLMRewriter(llm, self.template))
        chain.append(RuleRewriter(self.template, self.rng))
        return chain

    @property
    def rewriter_names(self) -> list[str]:
        return [r.name for r in self.rewriters]

    def evaluate(self, text: str, source: str, move: Move) -> Candidate:
        reading = self.meter.measure(text)
        safety = self.safety.check(text)
        focused, why = self.focus.validate_output(text, move.name)
        notes = list(safety.reasons) + ([] if focused else [why])
        return Candidate(text=text, source=source, score=reading.score, level=reading.level,
                         safe=safety.allowed, focused=focused, notes=notes)

    def rewrite(self, vanilla: str, level: int, move: Move, vanilla_source: str = "given",
                guidelines: str = "", recent: set[str] | None = None) -> GenerationResult:
        n = max(1, self.settings.rewrite_candidates)
        candidates: list[Candidate] = []
        for rewriter in self.rewriters:
            try:
                texts = rewriter.rewrite(vanilla, level, move, n)
            except Exception as exc:  # a failing backend never stops the conversation
                candidates.append(Candidate(text="", source=rewriter.name, safe=False, focused=False,
                                            notes=[f"greška: {exc}"]))
                continue
            for text in texts:
                candidates.append(self.evaluate(text, rewriter.name, move))
            if any(c.acceptable and c.level == level for c in candidates):
                break
        good = [c for c in candidates if c.acceptable]
        recent = recent or set()

        def repeats(c: Candidate) -> int:  # sentences the parent already said in the last turns
            return sum(normalize(s) in recent for s in sentences(c.text))

        if good:
            best = min(good, key=lambda c: (abs(c.level - level), repeats(c), abs(c.score - band_center(level))))
        else:
            best = self.evaluate(vanilla, "vanilla", move)
        text = best.text
        if move.end_with and not text.rstrip("!. ").endswith(move.end_with.rstrip("!. ")):
            ending = move.end_with.rstrip(".") + ("!" if level >= 4 else ".")
            text = f"{text} {ending}"
        return GenerationResult(move=move.name, target_level=level, guidelines=guidelines, vanilla=vanilla,
                                vanilla_source=vanilla_source, text=text, source=best.source,
                                score=best.score, level=best.level, candidates=candidates)

    def realize(self, move_name: str, anger: float, slots: dict, history: list[dict] | None = None,
                level: int | None = None) -> GenerationResult:
        move = self.template.move(move_name)
        target = self.template.clip_level(move, level if level is not None else level_for(anger))
        guidelines = self.vanilla.guidelines(move, slots)
        recent = {normalize(s) for item in (history or [])[-6:] if item.get("role") == "parent"
                  for s in sentences(item.get("text", ""))}
        text = self.vanilla.from_llm(move, slots, history or [])
        if text:
            return self.rewrite(text, target, move, "llm", guidelines, recent)
        # Offline: try the template's vanilla sentences in random order, keep the first one that hits the level.
        options = [fill_slots(v, slots) for v in move.vanilla] or [move.intent]
        self.rng.shuffle(options)
        best: tuple | None = None
        for option in options:
            result = self.rewrite(option, target, move, "template", guidelines, recent)
            repeated = sum(normalize(s) in recent for s in sentences(result.text))
            key = (abs(result.level - target), repeated, abs(result.score - band_center(target)))
            if best is None or key < best[0]:
                best = (key, result)
            if key[0] == 0:
                break
        return best[1]

    def alternatives(self, move_name: str, slots: dict, levels=range(1, 6), history: list[dict] | None = None,
                     vanilla: str | None = None) -> list[GenerationResult]:
        """Obrazac razgovora: the same move (same content) at different anger levels."""
        move = self.template.move(move_name)
        if vanilla is None:
            vanilla, source = self.vanilla.generate(move, slots, history)
        else:
            source = "given"
        results = []
        for level in levels:
            if move.levels[0] <= level <= move.levels[1]:
                results.append(self.rewrite(vanilla, level, move, source, self.vanilla.guidelines(move, slots)))
        return results
