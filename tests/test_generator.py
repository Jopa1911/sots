import random
import statistics

from src.generator import AngerPipeline, LLMRewriter, RuleRewriter, VanillaGenerator
from src.llm import ScriptedLLM, parse_json


def slots_for(scenario):
    return dict(scenario.slots, next_detail=scenario.details[0], next_complaint=scenario.complaints[1].say,
                next_condition=scenario.complaints[1].condition)


def test_rewrites_get_angrier_with_level(template, scenario, settings):
    pipeline = AngerPipeline(template, scenario, settings, rng=random.Random(1))
    slots = slots_for(scenario)
    scores = {level: [] for level in range(1, 6)}
    for name in template.moves:
        for result in pipeline.alternatives(name, slots):
            assert result.text
            assert pipeline.safety.is_safe(result.text)
            scores[result.target_level].append(result.score)
    means = [statistics.mean(v) for _, v in sorted(scores.items())]
    assert means == sorted(means)


def test_rule_rewriter_levels(template):
    rewriter = RuleRewriter(template, random.Random(0))
    move = template.move("DEMAND_ACTION")
    assert rewriter.rewrite("Could you let Luka take the test again?", 1, move) == [
        "Could you let Luka take the test again?"]
    harsh = rewriter.rewrite("Could you let Luka take the test again?", 4, move)
    assert harsh and all("!" in h for h in harsh)


def test_llm_vanilla_is_used_and_checked(template, scenario):
    llm = ScriptedLLM(["As an AI, I cannot do that.", "As an AI, I refuse."])
    gen = VanillaGenerator(template, scenario, llm=llm, rng=random.Random(0))
    text, source = gen.generate(template.move("DEMAND_ACTION"), slots_for(scenario), [])
    assert source == "template"
    llm = ScriptedLLM(["I would like Luka to take the test again."])
    gen = VanillaGenerator(template, scenario, llm=llm, rng=random.Random(0))
    text, source = gen.generate(template.move("DEMAND_ACTION"), slots_for(scenario), [])
    assert source == "llm" and "Luka" in text
    system, messages = llm.calls[0]
    assert "NEUTRAL" in system and "Guideline" in messages[0]["content"]


def test_llm_rewriter_prompt_and_parsing(template, scenario, settings):
    llm = ScriptedLLM(['["I want Luka to retake the test! This is unacceptable!", "Let Luka retake it now!"]'])
    rewriter = LLMRewriter(llm, template)
    out = rewriter.rewrite("I would like Luka to take the test again.", 3, template.move("DEMAND_ACTION"), n=2)
    assert len(out) == 2
    assert "level 3" in llm.calls[0][0] and "Examples" in llm.calls[0][0]
    pipeline = AngerPipeline(template, scenario, settings, llm=ScriptedLLM(lambda s, m: '["Fine."]'))
    assert pipeline.rewriter_names[-1] == "rules"


def test_parse_json_with_text_around():
    assert parse_json('Here you go:\n```json\n["a", "b"]\n```') == ["a", "b"]
    assert parse_json('{"labels": ["S3"]} thanks') == {"labels": ["S3"]}
