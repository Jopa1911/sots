import pytest

from src.anger_model import AngerModel


@pytest.fixture
def model():
    return AngerModel()


def test_reflection_lowers_anger(model):
    assert model.update(7.0, ["S3"]).after == 5.5


def test_early_suggestion_raises_anger(model):
    assert model.update(7.0, ["S6"]).after == 7.5
    assert model.update(5.0, ["S6"]).after == 4.0


def test_step_is_limited(model):
    assert model.update(7.0, ["S3", "S2", "S1"]).after == 5.0
    assert model.update(5.0, ["A3", "A2"]).after == 7.0


def test_yes_but_halves_calming(model):
    update = model.update(6.0, ["S3", "A1"])
    assert update.after == pytest.approx(6.0 + 1.0 - 0.75)


def test_teacher_anger_offtopic_and_ignoring(model):
    assert model.update(5.0, ["S8"], teacher_anger=5.5).after == 5.5
    assert model.update(5.0, ["S8"], teacher_anger=8.0).after == 6.0
    assert model.update(5.0, [], off_topic=True).after == 5.5
    assert model.update(5.0, ["S8"], ignored_turns=3).after == 5.5


def test_bounds_and_sensitivity():
    stubborn = AngerModel(sensitivity=0.5)
    assert stubborn.update(7.0, ["S3"]).after == 6.25
    assert AngerModel().update(0.5, ["S3"]).after == 0.0
    assert AngerModel().update(9.5, ["A3"]).after == 10.0
