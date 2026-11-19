"""Role 2, the evaluator: how did the teacher handle the angry parent?

The report combines the three layers of the conversation:
- flow and content: outcome, complaints acknowledged and resolved, focus on the topic;
- the parent's anger: start, peak, end, and what raised or lowered it in each turn;
- the teacher's anger: measured in every teacher turn.
It also scores the order of strategies against the ESConv relation (e.g. naming the emotion before suggesting)
and checks the simulator itself (did each generated parent sentence hit its target anger level?).
"""

from __future__ import annotations

import statistics
from collections import Counter

from .levels import NAMES_SR, level_for
from .strategies import CALMING, ESCALATING, KEY_ORDER, load_cards, load_relation

MAX_POINTS = {"ishod": 30, "smanjenje_ljutnje": 20, "smirenost_nastavnika": 15, "izbor_strategija": 15,
              "redosled": 10, "fokus": 10}
COMPONENT_NAMES = {"ishod": "Ishod razgovora", "smanjenje_ljutnje": "Smanjenje ljutnje roditelja",
                   "smirenost_nastavnika": "Smirenost nastavnika", "izbor_strategija": "Izbor strategija",
                   "redosled": "Redosled strategija (ESConv)", "fokus": "Fokus na temi"}
OUTCOME_SR = {"resolved": "dogovor postignut", "hung_up": "roditelj je prekinuo razgovor",
              "timeout": "isteklo vreme bez dogovora", None: "razgovor nije završen"}
COMMENTS_SR = {
    "S1": "Pitanje otvara prostor da roditelj objasni problem.",
    "S2": "Parafraza pokazuje da ste razumeli pritužbu.",
    "S3": "Imenovali ste emociju; to najviše smiruje ljutog roditelja.",
    "S4": "Lično iskustvo: kratko i vratite se na problem deteta.",
    "S5": "Potvrdili ste da je briga roditelja opravdana.",
    "S6": "Konkretan predlog rešenja.",
    "S7": "Informacija (činjenice); deluje kad je roditelj spreman da sluša.",
    "S8": "Ljubaznost ili neutralna replika; ne rešava pritužbu.",
    "A1": "Pozivanje na pravila pre nego što se roditelj smiri podiže ljutnju.",
    "A2": "Umanjivanje problema ili prekidanje podiže ljutnju.",
    "A3": "Pretnja, autoritet ili okrivljavanje najviše podižu ljutnju.",
}


def _first_turns(records) -> dict[str, int]:
    first: dict[str, int] = {}
    for r in records:
        for label in r["labels"]:
            first.setdefault(label, r["turn"])
    return first


class Evaluator:
    def __init__(self, teacher_threshold: float = 5.0, llm=None):
        self.cards = load_cards()
        self.relation = load_relation()
        self.teacher_threshold = teacher_threshold
        self.llm = llm

    # ---- public -----------------------------------------------------------------------------------
    def evaluate(self, session) -> dict:
        records = [r.to_dict() for r in session.records]
        opening = session.opening.to_dict() if session.opening else None
        return self.evaluate_records(records, session.initial_anger, session.outcome,
                                     [c.to_dict() for c in session.complaints],
                                     float(session.scenario.anger.get("resolve_threshold", 3.0)), opening)

    def evaluate_records(self, records: list[dict], initial_anger: float, outcome: str | None,
                         complaints: list[dict], resolve_threshold: float = 3.0, opening: dict | None = None) -> dict:
        n = len(records)
        parent_curve = [initial_anger] + [r["anger_after"] for r in records]
        teacher_curve = [r["teacher_anger"] for r in records]
        counts = Counter(label for r in records for label in r["labels"])
        escalating_turns = [r for r in records if set(r["labels"]) & set(ESCALATING)]
        calming_turns = [r for r in records if set(r["labels"]) & set(CALMING)
                         and not set(r["labels"]) & set(ESCALATING) and not r["off_topic"]]
        premature = [r for r in records if "S6" in r["labels"] and r["anger_before"] > 5]
        off_topic = [r for r in records if r["off_topic"]]
        injections = [r for r in records if r.get("injection")]
        high_teacher = [r for r in records if r["teacher_anger"] >= self.teacher_threshold]
        order = self._order(records)

        components = {
            "ishod": self._outcome_points(outcome, complaints),
            "smanjenje_ljutnje": self._reduction_points(parent_curve, resolve_threshold),
            "smirenost_nastavnika": self._composure_points(records, n),
            "izbor_strategija": self._strategy_points(calming_turns, escalating_turns, n),
            "redosled": self._order_points(order, calming_turns, premature),
            "fokus": max(0.0, 10 - 3 * len(off_topic) - 2 * len(injections)),
        }
        components = {k: round(min(v, MAX_POINTS[k]), 1) for k, v in components.items()}
        score = round(sum(components.values()), 1) if n else 0.0

        report = {
            "outcome": outcome,
            "outcome_sr": OUTCOME_SR.get(outcome, str(outcome)),
            "turns": n,
            "score": score,
            "components": {k: {"name": COMPONENT_NAMES[k], "points": v, "max": MAX_POINTS[k]}
                           for k, v in components.items()},
            "parent_anger": {"start": initial_anger, "max": max(parent_curve), "end": parent_curve[-1],
                             "end_level": NAMES_SR[level_for(parent_curve[-1])], "curve": parent_curve},
            "teacher_anger": {"mean": round(statistics.mean(teacher_curve), 2) if teacher_curve else 0.0,
                              "max": max(teacher_curve) if teacher_curve else 0.0,
                              "turns_above_threshold": len(high_teacher), "threshold": self.teacher_threshold,
                              "curve": teacher_curve},
            "strategy_counts": dict(counts),
            "calming_turns": len(calming_turns),
            "escalating_turns": len(escalating_turns),
            "premature_suggestions": [r["turn"] for r in premature],
            "off_topic_turns": [r["turn"] for r in off_topic],
            "order": order,
            "complaints": complaints,
            "turn_feedback": [self._turn_feedback(r) for r in records],
            "simulator_check": self._simulator_check(records, opening),
        }
        report["recommendations"] = self._recommendations(report, counts)
        report["summary"] = self._summary(report)
        if self.llm is not None and n:
            report["narrative"] = self._narrative(report, records)
        return report

    # ---- components -------------------------------------------------------------------------------
    @staticmethod
    def _outcome_points(outcome, complaints) -> float:
        if outcome == "resolved":
            return 30.0
        if outcome == "hung_up":
            return 0.0
        resolved = sum(1 for c in complaints if c["resolved"])
        return 5.0 + 10.0 * resolved / max(1, len(complaints))

    @staticmethod
    def _reduction_points(curve, resolve_threshold) -> float:
        start, end = curve[0], curve[-1]
        if start <= resolve_threshold:
            return 20.0 if end <= start else max(0.0, 20 - 5 * (end - start))
        return 20.0 * max(0.0, min(1.0, (start - end) / (start - resolve_threshold)))

    def _composure_points(self, records, n) -> float:
        """Calm tone (measured teacher anger) and no emotional reactions (minimising, sarcasm, blaming)."""
        if not n:
            return 0.0
        lost = sum(1 for r in records if r["teacher_anger"] >= self.teacher_threshold
                   or {"A2", "A3"} & set(r["labels"]))
        points = 15.0 * (1 - lost / n)
        if max(r["teacher_anger"] for r in records) >= 7:
            points -= 5
        return max(0.0, points)

    @staticmethod
    def _order_points(order, calming_turns, premature) -> float:
        if order["total"]:
            points = 10.0 * order["respected"] / order["total"]
        elif calming_turns:
            points = 10.0
        else:
            points = 0.0
        return max(0.0, points - 2 * len(premature))

    @staticmethod
    def _strategy_points(calming_turns, escalating_turns, n) -> float:
        if not n:
            return 0.0
        return max(0.0, 15.0 * len(calming_turns) / n - 3 * len(escalating_turns))

    def _order(self, records) -> dict:
        first = _first_turns(records)
        checked, violations = [], []
        for a, b in KEY_ORDER:
            if b not in first:
                continue
            ok = a in first and first[a] < first[b]
            checked.append({"before": a, "after": b, "ok": ok, "turn": first[b]})
            if not ok:
                violations.append({"before": a, "after": b, "turn": first[b],
                                   "text": f"{b} ({self.cards[b].name}) u replici {first[b]}, a {a} "
                                           f"({self.cards[a].name}) nije korišćen pre toga."})
        hasse = []
        for a, b in self.relation.get("edges", []):
            if a in CALMING and b in CALMING and a in first and b in first:
                hasse.append({"before": a, "after": b, "ok": first[a] <= first[b]})
        return {"checked": checked, "violations": violations, "respected": sum(c["ok"] for c in checked),
                "total": len(checked), "esconv_edges": hasse}

    # ---- feedback ---------------------------------------------------------------------------------
    def _turn_feedback(self, r: dict) -> dict:
        notes = []
        if r.get("injection"):
            notes.append("Pokušaj izlaska iz uloge; simulator ostaje u ulozi i vraća razgovor na temu.")
        elif r["off_topic"]:
            notes.append("Skrenuli ste sa teme; roditelj vraća razgovor na pritužbu.")
        for label in r["labels"]:
            if label in COMMENTS_SR:
                notes.append(f"{label}: {COMMENTS_SR[label]}")
        if "S6" in r["labels"] and r["anger_before"] > 5:
            notes.append(f"Predlog je dat dok je ljutnja bila {r['anger_before']:.1f}/10; "
                         "prvo smirite roditelja (S3, S2), pa predložite.")
        if r["proposal"] == "rejected" and r["anger_before"] <= 5:
            notes.append("Roditelj prvo želi da čuje da ste razumeli pritužbu (parafraza ili imenovanje emocije).")
        if r["proposal"] == "vague":
            notes.append("Predlog nije dovoljno konkretan (ko, šta, kada).")
        if r["teacher_anger"] >= self.teacher_threshold:
            notes.append(f"U vašem tonu se oseća ljutnja ({r['teacher_anger']:.1f}/10).")
        if r["acknowledged"]:
            notes.append("Roditelj oseća da je pritužba saslušana: " + ", ".join(r["acknowledged"]) + ".")
        if r["resolved"]:
            notes.append("Pritužba rešena: " + ", ".join(r["resolved"]) + ".")
        return {
            "turn": r["turn"],
            "teacher": r["teacher_text"],
            "labels": r["labels"],
            "delta": round(r["anger_after"] - r["anger_before"], 2),
            "anger_after": r["anger_after"],
            "components": [{"source": c[0], "delta": c[1], "note": c[2]} for c in r["anger_components"]],
            "notes": notes,
            "better": self._better_option(r),
        }

    def _better_option(self, r: dict) -> str:
        labels = set(r["labels"])
        if r["off_topic"]:
            return self.cards["OFF"].counterexample
        if labels & set(ESCALATING) or ("S6" in labels and r["anger_before"] > 5) or \
                ("S7" in labels and r["anger_before"] > 5):
            return self.cards["S3"].school_example
        if labels == {"S8"} or r["proposal"] == "vague":
            return self.cards["S1"].school_example if r["anger_before"] > 5 else self.cards["S6"].school_example
        return ""

    def _recommendations(self, report: dict, counts: Counter) -> list[dict]:
        recs: list[dict] = []

        def add(card_id: str, reason: str) -> None:
            if card_id not in {r["card"] for r in recs}:
                recs.append({"card": card_id, "name": self.cards[card_id].name, "reason": reason})

        for anti in ESCALATING:
            if counts.get(anti):
                add(anti, f"Korišćeno {counts[anti]}x; podiže ljutnju roditelja.")
        if report["premature_suggestions"]:
            add("S6", "Predlog dat dok je roditelj još bio ljut (> 5/10).")
        if not counts.get("S3"):
            add("S3", "Emocija roditelja nijednom nije imenovana.")
        if not counts.get("S2"):
            add("S2", "Pritužba nijednom nije parafrazirana.")
        if report["off_topic_turns"]:
            add("OFF", "Razgovor je skretao sa teme.")
        if report["teacher_anger"]["turns_above_threshold"]:
            add("A2", "U vašem tonu je bilo ljutnje; ostanite smireni i kad roditelj napada.")
        if report["outcome"] != "resolved" and not counts.get("S6"):
            add("S6", "Nije ponuđeno konkretno rešenje.")
        return recs[:4]

    def _summary(self, report: dict) -> str:
        pa = report["parent_anger"]
        parts = [f"Ishod: {report['outcome_sr']} (replika nastavnika: {report['turns']}). "
                 f"Ljutnja roditelja: {pa['start']:.1f} → {pa['end']:.1f} (najviše {pa['max']:.1f}). "
                 f"Ukupno {report['score']:.0f}/100 poena."]
        if report["escalating_turns"]:
            parts.append(f"Eskalirajućih replika: {report['escalating_turns']}.")
        if report["premature_suggestions"]:
            parts.append("Predlog je dat prerano (replike " +
                         ", ".join(map(str, report["premature_suggestions"])) + ").")
        order = report["order"]
        if order["total"]:
            parts.append(f"Redosled kao u ESConv: {order['respected']} od {order['total']} ključnih parova.")
        if report["teacher_anger"]["turns_above_threshold"]:
            parts.append(f"Ljutnja u vašem tonu u {report['teacher_anger']['turns_above_threshold']} replika.")
        return " ".join(parts)

    @staticmethod
    def _simulator_check(records: list[dict], opening: dict | None) -> dict:
        """Role 2b: did the simulator's sentences hit the target anger level, and were candidates rejected?"""
        rows = [(r["target_level"], r["parent_level"], r["candidates"]) for r in records]
        if opening:
            rows.insert(0, (opening["target_level"], opening["level"],
                            [{"ok": c["safe"] and c["focused"]} for c in opening["candidates"]]))
        if not rows:
            return {}
        diffs = [abs(t - m) for t, m, _ in rows]
        rejected = sum(1 for _, _, cands in rows for c in cands if not c.get("ok", True))
        return {"sentences": len(rows), "exact_level": round(sum(d == 0 for d in diffs) / len(rows), 2),
                "mean_level_error": round(statistics.mean(diffs), 2), "rejected_candidates": rejected}

    def _narrative(self, report: dict, records: list[dict]) -> str:
        transcript = "\n".join(f"Nastavnik: {r['teacher_text']}\nRoditelj: {r['parent_text']}" for r in records)
        system = ("Ti si mentor nastavnicima. Na osnovu transkripta razgovora sa ljutim roditeljem i izveštaja "
                  "napiši kratku povratnu informaciju na srpskom (5-7 rečenica): šta je dobro, šta da promeni, "
                  "jedna konkretna rečenica koju može da kaže sledeći put. Bez ocenjivanja ličnosti.")
        user = f"Izveštaj: {report['summary']}\n\nTranskript:\n{transcript}"
        try:
            return self.llm.complete(system, [{"role": "user", "content": user}], max_tokens=500)
        except Exception as exc:
            return f"(povratna informacija jezičkog modela nije dostupna: {exc})"
