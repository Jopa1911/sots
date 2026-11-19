import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.skipif(importlib.util.find_spec("streamlit") is None, reason="streamlit not installed")
def test_streamlit_app_runs_a_turn(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("LLM_PROVIDER", "mock")
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception
    at.chat_input[0].set_value("I can hear that you are upset about the grade. What happened?").run()
    assert not at.exception
    assert len(at.chat_message) == 3


def test_pilot_analysis(tmp_path):
    sys.path.insert(0, str(ROOT / "evaluation"))
    from analyze_pilot import analyze, to_markdown

    rows = []
    for i in range(8):
        row = {"participant_id": f"P{i}"}
        row.update({f"pre_se{k}": 2 + (i + k) % 2 for k in range(1, 7)})
        row.update({f"post_se{k}": 4 for k in range(1, 7)})
        row.update({f"real{k}": 4 for k in range(1, 6)})
        row.update({f"sus{k}": 4 if k % 2 else 2 for k in range(1, 11)})
        row.update({"sim1_score": 60, "sim1_outcome": "timeout", "sim2_score": 85, "sim2_outcome": "resolved"})
        rows.append(row)
    result = analyze(pd.DataFrame(rows))
    assert result["sus_mean"] == 75.0
    assert result["post_se_mean"] > result["pre_se_mean"]
    assert result["p_value"] < 0.05
    assert "SUS" in to_markdown(result)
