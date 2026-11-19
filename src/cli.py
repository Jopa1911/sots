"""Conversation in the terminal.

    python -m src.cli                       # scenario bad_grade
    python -m src.cli --scenario trip_exclusion --anger 8 --sensitivity 0.5 --debug

Commands during the call: /stanje (state), /alt (the last move at every anger level), /izvestaj (report),
/kraj (end), /pomoc (help).
"""

from __future__ import annotations

import argparse
import json

from .config import Settings
from .generator import REWRITER_NAMES_SR
from .levels import NAMES_SR, level_for
from .scenario import list_scenarios
from .session import Session
from .strategies import label_name
from .textutil import utf8_console

HELP = ("Komande: /stanje (stanje razgovora), /alt (poslednji potez na svim nivoima ljutnje), "
        "/izvestaj (izveštaj), /kraj, /pomoc. Razgovor se vodi na engleskom.")


def bar(value: float, width: int = 20) -> str:
    filled = round(value / 10 * width)
    return "#" * filled + "." * (width - filled)


def show_parent(text: str, anger: float) -> None:
    print(f"\nRODITELJ  [{bar(anger)}] {anger:4.1f}/10 {NAMES_SR[level_for(anger)]}")
    print(f"  {text}\n")


def print_report(report: dict) -> None:
    print("\n=== IZVEŠTAJ (evaluator) ===")
    print(report["summary"])
    for item in report["components"].values():
        print(f"  {item['name']:<32} {item['points']:5.1f} / {item['max']}")
    print("\nPo replikama:")
    for fb in report["turn_feedback"]:
        print(f"  {fb['turn']:>2}. {fb['labels']} {fb['delta']:+.1f} -> {fb['anger_after']:.1f}: {fb['teacher']}")
        for note in fb["notes"]:
            print(f"      - {note}")
        if fb["better"]:
            print(f"      bolje: \"{fb['better']}\"")
    if report["recommendations"]:
        print("\nKartice za vežbu:")
        for rec in report["recommendations"]:
            print(f"  {rec['card']} {rec['name']}: {rec['reason']}")
    check = report.get("simulator_check", {})
    if check:
        print(f"\nProvera simulatora: ciljni nivo ljutnje pogođen u {check['exact_level']:.0%} rečenica.")
    if report.get("narrative"):
        print("\n" + report["narrative"])


def main() -> None:
    utf8_console()
    parser = argparse.ArgumentParser(description="Simulator ljutog roditelja (terminal).")
    parser.add_argument("--scenario", default="bad_grade", choices=list_scenarios())
    parser.add_argument("--anger", type=float, default=None, help="početna ljutnja 0-10")
    parser.add_argument("--sensitivity", type=float, default=None, help="1.0 prosečan, 0.5 tvrdoglav roditelj")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--debug", action="store_true", help="prikaži vanila rečenicu, ciljni nivo i pravilo toka")
    parser.add_argument("--save", action="store_true", help="sačuvaj razgovor u logs/sessions/")
    args = parser.parse_args()

    settings = Settings.from_env()
    session = Session(args.scenario, settings, initial_anger=args.anger, sensitivity=args.sensitivity,
                      seed=args.seed)
    for warning in session.warnings:
        print("UPOZORENJE:", warning)
    print(f"Scenario: {session.scenario.title}\n{session.scenario.description}")
    print(f"Jezički model: {settings.describe_llm()} | grube rečenice: "
          f"{', '.join(REWRITER_NAMES_SR.get(n, n) for n in session.pipeline.rewriter_names)}")
    print(HELP)
    opening = session.start()
    show_parent(opening.text, session.anger)

    while not session.finished:
        try:
            text = input("NASTAVNIK > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text in {"/kraj", "/quit", "/exit"}:
            break
        if text == "/pomoc":
            print(HELP)
            continue
        if text == "/stanje":
            print(json.dumps(session.policy_state(), indent=2, ensure_ascii=False))
            print([c.to_dict() for c in session.complaints])
            continue
        if text == "/izvestaj":
            print_report(session.report())
            continue
        if text == "/alt":
            move = session.records[-1].move if session.records else "OPEN_COMPLAINT"
            for result in session.pipeline.alternatives(move, session.slots()):
                print(f"  nivo {result.target_level} ({result.level}): {result.text}")
            continue
        rec = session.respond(text)
        names = ", ".join(f"{label} {label_name(label)}" for label in rec.labels)
        print(f"  [{names} | ljutnja nastavnika {rec.teacher_anger:.1f} | roditelj {rec.anger_before:.1f} -> "
              f"{rec.anger_after:.1f}]")
        if args.debug:
            print(f"  potez {rec.move} (pravilo {rec.policy_rule}), cilj L{rec.target_level}, izmereno "
                  f"L{rec.parent_level}, izvor: {REWRITER_NAMES_SR.get(rec.rewrite_source, rec.rewrite_source)}")
            print(f"  vanila ({rec.vanilla_source}): {rec.vanilla}")
        show_parent(rec.parent_text, rec.anger_after)

    if session.records:
        if session.finished:
            print(f"Kraj razgovora: {session.outcome_sr}.")
        print_report(session.report(llm_narrative=settings.llm_enabled))
        if args.save:
            print("sačuvano:", session.save())


if __name__ == "__main__":
    main()
