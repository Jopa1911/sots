from src.levels import level_for
from src.scenario import list_scenarios, load_scenario
from src.template import ConversationTemplate


def base_state(**kw):
    state = {"turn": 3, "outcome": None, "off_topic": False, "anger": 6.0, "strategies": ["S8"],
             "last_strategy": "S8", "proposal": "none", "open_complaints": 2, "unraised_complaints": 1,
             "main_acknowledged": False, "details_left": 3, "details_revealed": 1,
             "hidden_need_revealed": False, "ignored": 0}
    state.update(kw)
    return state


def test_every_move_has_content(template):
    for name, move in template.moves.items():
        assert move.vanilla, name
        assert move.guidelines, name
        assert 1 <= move.levels[0] <= move.levels[1] <= 5


def test_conditions():
    holds = ConversationTemplate.condition_holds
    assert holds({"anger_gte": 5}, {"anger": 5})
    assert not holds({"anger_gt": 5}, {"anger": 5})
    assert holds({"strategies_has": "S1"}, {"strategies": ["S3", "S1"]})
    assert holds({"strategies_has_any": ["A2", "A3"]}, {"strategies": ["A3"]})
    assert holds({"last_strategy_in": ["S2", "S3"]}, {"last_strategy": "S3"})
    assert holds({"proposal_not_in": ["accepted"]}, {"proposal": "none"})
    assert not holds({"missing_gte": 1}, {})


def test_policy_flow(template):
    assert template.choose_move(base_state(turn=0))[0] == "OPEN_COMPLAINT"
    assert template.choose_move(base_state(outcome="hung_up"))[0] == "HANG_UP"
    assert template.choose_move(base_state(off_topic=True, strategies=["OFF"]))[0] == "REDIRECT_TO_TOPIC"
    assert template.choose_move(base_state(anger=9.0))[0] == "THREATEN_ESCALATION"
    assert template.choose_move(base_state(strategies=["A1"]))[0] == "REJECT_RULES"
    assert template.choose_move(base_state(strategies=["A3"]))[0] == "ACCUSE"
    assert template.choose_move(base_state(proposal="rejected", strategies=["S6"]))[0] == "REJECT_PROPOSAL"
    assert template.choose_move(base_state(proposal="accepted", open_complaints=0))[0] == "ACCEPT_PROPOSAL"
    assert template.choose_move(base_state(proposal="accepted", open_complaints=1))[0] == "CONDITIONAL_ACCEPT"
    assert template.choose_move(base_state(strategies=["S1"], anger=4.0))[0] == "REVEAL_HIDDEN_NEED"
    assert template.choose_move(base_state(strategies=["S1"], anger=7.0))[0] == "ELABORATE_COMPLAINT"
    assert template.choose_move(base_state(ignored=2))[0] == "REPEAT_COMPLAINT"


def test_level_mapping():
    assert [level_for(a) for a in (0, 2, 3, 4, 5, 6, 7, 8, 9, 10)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_scenarios_load():
    for sid in list_scenarios():
        scenario = load_scenario(sid)
        assert scenario.main_complaint.main
        assert scenario.topic_keywords and scenario.details
