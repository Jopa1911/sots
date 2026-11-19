import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import Settings  # noqa: E402
from src.scenario import load_scenario  # noqa: E402
from src.template import ConversationTemplate  # noqa: E402


@pytest.fixture
def settings():
    return Settings(llm_provider="mock", max_minutes=0, seed=1, classifier_backend="rules")


@pytest.fixture
def template():
    return ConversationTemplate.load()


@pytest.fixture
def scenario():
    return load_scenario("bad_grade")
