"""Web app: the angry-parent simulator (role 1) and the teacher evaluator (role 2).

    streamlit run app.py
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import streamlit as st

from src import voice
from src.anger_meter import LexiconAngerMeter
from src.classifier import get_classifier
from src.config import CONTENT_DIR, ROOT, Settings
from src.generator import REWRITER_NAMES_SR
from src.levels import NAMES_SR, level_for
from src.scenario import list_scenarios, load_scenario
from src.session import Session
from src.strategies import ESCALATING, label_name, load_cards, load_relation
from src.template import ConversationTemplate, fill_slots

st.set_page_config(page_title="Simulator ljutog roditelja", page_icon="📞", layout="wide")
LEVEL_ICON = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⛔"}
OUTCOME_SHORT = {"resolved": "dogovor", "hung_up": "prekid", "timeout": "bez dogovora"}


# ---- shared resources -------------------------------------------------------------------------------
@st.cache_resource
def settings() -> Settings:
    return Settings.from_env()


@st.cache_resource
def shared_classifier():
    return get_classifier(settings())


@st.cache_resource
def shared_meter():
    return LexiconAngerMeter()


@st.cache_resource
def template() -> ConversationTemplate:
    return ConversationTemplate.load()


def new_session(scenario_id: str, anger: float, sensitivity: float, goal: str = "") -> None:
    session = Session(scenario_id, settings(), template=template(), classifier=shared_classifier(),
                      meter=shared_meter(), initial_anger=anger, sensitivity=sensitivity)
    session.start()
    st.session_state.session = session
    st.session_state.goal = goal
    st.session_state.audio_done = None


def anger_label(value: float) -> str:
    level = level_for(value)
    return f"{LEVEL_ICON[level]} {value:.1f}/10 · {NAMES_SR[level]}"


# ---- sidebar ----------------------------------------------------------------------------------------
cfg = settings()
scenario_ids = list_scenarios()
titles = {sid: load_scenario(sid).title for sid in scenario_ids}

with st.sidebar:
    st.header("📞 Novi razgovor")
    scenario_id = st.selectbox("Scenario", scenario_ids, format_func=lambda s: titles[s])
    scenario = load_scenario(scenario_id)
    anger0 = st.slider("Početna ljutnja roditelja", 0.0, 10.0, scenario.initial_anger, 0.5)
    stubborn = st.toggle("Tvrdoglav roditelj (osetljivost 0,5)", value=False)
    if st.button("Započni razgovor", type="primary") or "session" not in st.session_state:
        new_session(scenario_id, anger0, 0.5 if stubborn else 1.0)
    st.caption(scenario.description)
    st.divider()
    debug = st.toggle("Prikaži kako agent radi", value=False,
                      help="Vanila rečenica, ciljni i izmereni nivo ljutnje, pravilo toka.")
    st.caption(f"Jezički model: {cfg.describe_llm()} · grube rečenice: "
               f"{', '.join(REWRITER_NAMES_SR.get(n, n) for n in st.session_state.session.pipeline.rewriter_names)}")
    for warning in st.session_state.session.warnings:
        st.warning(warning)

session: Session = st.session_state.session
tab_chat, tab_report, tab_cards, tab_alt, tab_about = st.tabs(
    ["💬 Razgovor", "📊 Izveštaj", "🗂️ Kartice", "🎚️ Alternative", "ℹ️ O sistemu"])

# ---- conversation (role 1: angry parent simulator) ----------------------------------------------------
with tab_chat:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader(session.scenario.title)
        if st.session_state.get("goal"):
            st.info(f"🎯 Cilj vežbe: {st.session_state.goal}")
        st.caption("Razgovor se vodi na engleskom (sadržaj i ESConv su na engleskom).")
        with st.chat_message("roditelj", avatar="😠"):
            st.write(session.opening.text)
            if debug:
                st.caption(f"potez OPEN_COMPLAINT · nivo {session.opening.target_level} → izmereno "
                           f"{session.opening.level} · vanila: {session.opening.vanilla}")
        for rec in session.records:
            with st.chat_message("nastavnik", avatar="🧑‍🏫"):
                st.write(rec.teacher_text)
                tags = ", ".join(f"{x} {label_name(x)}" for x in rec.labels)
                st.caption(f"{tags} · ljutnja roditelja {rec.anger_before:.1f} → {rec.anger_after:.1f} "
                           f"· vaša ljutnja {rec.teacher_anger:.1f}")
            with st.chat_message("roditelj", avatar="😠"):
                st.write(rec.parent_text)
                if debug:
                    st.caption(f"potez {rec.move} (pravilo {rec.policy_rule}) · cilj nivo {rec.target_level}, "
                               f"izmereno {rec.parent_level} ({rec.parent_score:.1f}) · {rec.rewrite_source}")
                    st.caption(f"vanila ({rec.vanilla_source}): {rec.vanilla}")

        if session.finished:
            st.success(f"Kraj razgovora: {session.outcome_sr}. Pogledajte karticu Izveštaj.")
        else:
            audio_text = None
            if voice.stt_available(cfg) and hasattr(st, "audio_input"):
                audio = st.audio_input("🎙️ Ili izgovorite repliku")
                if audio is not None:
                    data = audio.getvalue()
                    digest = hashlib.md5(data).hexdigest()
                    if digest != st.session_state.get("audio_done"):
                        st.session_state.audio_done = digest
                        audio_text = voice.transcribe(data, cfg)
            typed = st.chat_input("Vaša replika nastavnika (na engleskom)…")
            text = typed or audio_text
            if text:
                session.respond(text)
                if voice.tts_available(cfg):
                    st.session_state.last_audio = voice.synthesize(session.records[-1].parent_text, cfg)
                st.rerun()
        if voice.tts_available(cfg) and st.session_state.get("last_audio"):
            data, mime = st.session_state.pop("last_audio")
            st.audio(data, format=mime, autoplay=True)

    with right:
        last_delta = session.records[-1].anger_after - session.records[-1].anger_before if session.records else None
        c1, c2 = st.columns(2)
        c1.metric("Ljutnja roditelja", f"{session.anger:.1f}/10",
                  delta=None if last_delta is None else f"{last_delta:+.1f}", delta_color="inverse")
        c2.metric("Nivo", f"{LEVEL_ICON[session.level]} {NAMES_SR[session.level]}")
        st.progress(min(1.0, session.anger / 10), text=anger_label(session.anger))
        curve = pd.DataFrame({
            "roditelj": session.anger_curve,
            "nastavnik": [None] + [r.teacher_anger for r in session.records],
        }, index=pd.Index(range(len(session.anger_curve)), name="replika"))
        st.line_chart(curve, y=["roditelj", "nastavnik"], color=["#c2410c", "#0e7ec4"], y_label="ljutnja (0-10)")
        st.caption("Roditelj: model ljutnje (emocija chatbota). Nastavnik: izmerena ljutnja u vašim replikama.")

        st.markdown("**Pritužbe roditelja**")
        for cs in session.complaints:
            status = "✅ rešena" if cs.resolved else ("👂 saslušana" if cs.acknowledged else
                                                       ("❗ otvorena" if cs.raised else "… nije pomenuta"))
            st.write(f"{status} — {cs.complaint.text}")

        if session.records:
            rec = session.records[-1]
            st.markdown("**Poslednja replika — šta je promenilo ljutnju**")
            rows = [{"uzrok": f"{src} {label_name(src)}" if src in load_cards() else note, "Δ": delta}
                    for src, delta, note in rec.anger_components]
            if rows:
                st.dataframe(pd.DataFrame(rows), hide_index=True)
            if rec.off_topic:
                st.warning("Replika nije bila na temi; roditelj vraća razgovor na pritužbu.")
            if set(rec.labels) & set(ESCALATING):
                st.error("Eskalirajuće ponašanje podiže ljutnju.")

# ---- report (role 2: evaluator) ------------------------------------------------------------------------
with tab_report:
    if not session.records:
        st.info("Izveštaj se pojavljuje posle prve replike nastavnika.")
    else:
        report = session.report()
        top = st.columns(4)
        top[0].metric("Ukupno", f"{report['score']:.0f}/100")
        top[1].metric("Ishod", OUTCOME_SHORT.get(report["outcome"], "u toku"))
        pa = report["parent_anger"]
        top[2].metric("Ljutnja roditelja", f"{pa['start']:.1f} → {pa['end']:.1f}")
        top[3].metric("Vaša prosečna ljutnja", f"{report['teacher_anger']['mean']:.1f}")
        st.write(report["summary"])
        for item in report["components"].values():
            st.progress(item["points"] / item["max"], text=f"{item['name']}: {item['points']:.1f} / {item['max']}")

        st.markdown("#### Po replikama")
        for fb in report["turn_feedback"]:
            title = f"{fb['turn']}. {fb['teacher'][:70]} ({fb['delta']:+.1f} → {fb['anger_after']:.1f})"
            with st.expander(title):
                st.write(", ".join(f"{x} {label_name(x)}" for x in fb["labels"]))
                for note in fb["notes"]:
                    st.write("• " + note)
                if fb["better"]:
                    st.success(f"Može bolje, na primer: “{fb['better']}”")

        order = report["order"]
        if order["checked"]:
            st.markdown("#### Redosled strategija prema ESConv")
            for item in order["checked"]:
                st.write(("✅ " if item["ok"] else "⚠️ ") + f"{item['before']} pre {item['after']}")
        if report["recommendations"]:
            st.markdown("#### Kartice za vežbu")
            for rec in report["recommendations"]:
                st.write(f"**{rec['card']} {rec['name']}** — {rec['reason']}")
        check = report.get("simulator_check") or {}
        if check:
            st.caption(f"Provera simulatora: ciljni nivo ljutnje pogođen u {check['exact_level']:.0%} rečenica, "
                       f"prosečna greška {check['mean_level_error']} nivoa, odbačeno kandidata: "
                       f"{check['rejected_candidates']}.")
        if cfg.llm_enabled and st.button("Napiši povratnu informaciju (jezički model)"):
            st.write(session.report(llm_narrative=True).get("narrative", ""))
        st.download_button("Preuzmi razgovor i izveštaj (JSON)",
                           json.dumps(session.to_dict(), ensure_ascii=False, indent=2),
                           file_name=f"razgovor_{session.scenario.id}.json", mime="application/json")

# ---- learning cards -------------------------------------------------------------------------------------
with tab_cards:
    cards = load_cards()
    card_id = st.selectbox("Strategija", list(cards), format_func=lambda c: f"{c} — {cards[c].name}")
    card = cards[card_id]
    kind = {"calming": "smiruje", "escalating": "podiže ljutnju", "neutral": "neutralno"}.get(card.kind, card.kind)
    st.markdown(f"### {card_id} {card.name}")
    st.caption(f"Uticaj na ljutnju roditelja: Δ {card.delta:+.1f} ({kind})"
               + (f"; Δ {card.delta_if_anger_above['delta']:+.1f} ako je ljutnja > "
                  f"{card.delta_if_anger_above['threshold']:.0f}" if card.delta_if_anger_above else ""))
    st.markdown(f"**1. Objašnjenje.** {card.definition} {card.explanation}")
    st.markdown(f"**Cilj:** {card.learning_goal}")
    if card.esconv_example:
        st.markdown(f"**2. Primer iz ESConv:** “{card.esconv_example['text']}” "
                    f"<small>({card.esconv_example['ref']})</small>", unsafe_allow_html=True)
    st.markdown(f"**Primer u školi:** “{card.school_example}”  \n**Kontraprimer:** “{card.counterexample}”")
    if card.check:
        st.markdown(f"**3. Provera:** {card.check['question']}")
        choice = st.radio("Odgovor", card.check["options"], index=None, key=f"quiz_{card_id}",
                          label_visibility="collapsed")
        if choice is not None:
            if card.check["options"].index(choice) == card.check["answer"]:
                st.success("Tačno. " + card.check["feedback"])
            else:
                st.error("Nije tačno. " + card.check["feedback"])
    if card.practice:
        st.markdown(f"**4. Vežba sa agentom:** {card.practice['goal']} (početna ljutnja {card.practice['anger']})")
        if st.button("Vežbaj ovu strategiju", key=f"practice_{card_id}"):
            new_session(scenario_id, float(card.practice["anger"]), 1.0, goal=card.practice["goal"])
            st.rerun()
    st.caption("5. Povratna informacija: izveštaj posle razgovora (kartica Izveštaj).")

# ---- conversation template: alternatives at every anger level ---------------------------------------------
with tab_alt:
    st.markdown("Isti potez roditelja (isti sadržaj) na svakom nivou ljutnje: **smernice → vanila rečenica → "
                "gruba rečenica → provera**. Vanila rečenicu možete i sami da napišete.")
    tpl = template()
    move_name = st.selectbox("Potez roditelja", list(tpl.moves),
                             format_func=lambda m: f"{m} — {tpl.moves[m].intent}")
    move = tpl.move(move_name)
    slots = session.slots()
    st.caption(f"Smernica za jezički model: {fill_slots(move.guidelines, slots)} · "
               f"dozvoljeni nivoi: {move.levels[0]}–{move.levels[1]}")
    default_vanilla = fill_slots(move.vanilla[0], slots) if move.vanilla else ""
    vanilla = st.text_area("Vanila rečenica", default_vanilla, key=f"vanilla_{move_name}_{session.scenario.id}")
    if st.button("Generiši alternative", type="primary"):
        results = session.pipeline.alternatives(move_name, slots, vanilla=vanilla.strip() or None)
        for r in results:
            st.markdown(f"{LEVEL_ICON[r.target_level]} **{r.target_level} {NAMES_SR[r.target_level]}** "
                        f"<small>(izmereno: nivo {r.level}, {r.score:.1f}/10 · {r.source})</small>  \n{r.text}",
                        unsafe_allow_html=True)
        with st.expander("Svi kandidati i razlozi odbacivanja"):
            for r in results:
                st.markdown(f"**Nivo {r.target_level}**")
                for c in r.candidates:
                    mark = "✅" if c.acceptable else "❌"
                    st.write(f"{mark} [{c.source}, izmereno {c.level}] {c.text} {' '.join(c.notes)}")

# ---- about -----------------------------------------------------------------------------------------------
with tab_about:
    diagram = ROOT / "docs" / "dijagrami" / "arhitektura_simulatora.png"
    if diagram.exists():
        st.image(str(diagram), caption="Arhitektura: tok i sadržaj → emocija chatbota → merenje ljutnje nastavnika")
    st.markdown("""
**Uloga 1 — simulator ljutog roditelja.** Obrazac razgovora bira sledeći potez (tok), scenario daje
činjenice (sadržaj), a model ljutnje drži emociju roditelja (0–10). Rečenica nastaje u dva koraka: jezički model
po grubim smernicama piše neutralnu (vanila) rečenicu, a poseban model je prepisuje u grubu rečenicu za zadati
nivo ljutnje. Svaka rečenica se proverava meračem ljutnje, filterom za bezbednost i proverom fokusa.

**Uloga 2 — evaluator.** Meri ljutnju u replikama nastavnika, prepoznaje strategije (S1–S8 iz ESConv,
A1–A3 eskalirajuće) i ocenjuje razgovor: ishod, smanjenje ljutnje, smirenost, izbor i redosled strategija, fokus.
""")
    relation = load_relation()
    if relation.get("edges"):
        st.caption("ESConv relacija „obično dolazi pre“ (≥ 70%): " +
                   ", ".join(f"{a}→{b}" for a, b in relation["edges"]))
    metrics_path = CONTENT_DIR / "esconv" / "classifier_metrics.json"
    if metrics_path.exists():
        m = json.loads(metrics_path.read_text(encoding="utf-8"))
        st.caption(f"ESConv klasifikator strategija: tačnost {m['esconv_test_accuracy']}, "
                   f"makro-F1 {m['esconv_test_macro_f1']} (izdvojeni razgovori).")
    with st.expander("Podešavanja (.env)"):
        st.json(cfg.public_dict())
