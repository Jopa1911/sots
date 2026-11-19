import json

from src.session import Session
from src.simulate import TEACHERS, run


def test_empathic_teacher_resolves_the_call():
    session = run("empathic", verbose=False)
    assert session.outcome == "resolved"
    report = session.report()
    assert report["score"] >= 85
    assert all(c["resolved"] for c in report["complaints"])


def test_defensive_teacher_makes_the_parent_hang_up():
    session = run("defensive", verbose=False)
    assert session.outcome == "hung_up"
    report = session.report()
    assert report["score"] < 30
    assert {r["card"] for r in report["recommendations"]} & {"A1", "A2", "A3"}


def test_rushing_teacher_gets_order_feedback():
    report = run("rushing", verbose=False).report()
    assert report["premature_suggestions"] == [1, 2]
    assert report["order"]["violations"]


def test_offtopic_turn_is_redirected(settings):
    session = Session("bad_grade", settings)
    session.start()
    rec = session.respond("By the way, how was your weekend?")
    assert rec.off_topic and rec.move == "REDIRECT_TO_TOPIC" and rec.anger_after > rec.anger_before
    rec = session.respond("Are you an AI?")
    assert rec.injection and rec.move == "REDIRECT_TO_TOPIC"


def test_timeout_and_serialisation(settings):
    session = Session("bad_grade", settings)
    session.start()
    for _ in range(session.scenario.max_turns):
        if session.finished:
            break
        session.respond("Okay.")
    assert session.outcome in {"timeout", "hung_up"}
    json.dumps(session.to_dict())


def test_all_scripts_run_on_both_scenarios():
    for scenario, teachers in TEACHERS.items():
        for teacher in teachers:
            session = run(teacher, scenario, verbose=False)
            assert session.records
