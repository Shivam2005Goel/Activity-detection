import pytest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.generate_sample_data import generate_synthetic_transactions
from agents.orchestrator import run_agent


@pytest.fixture(scope="module", autouse=True)
def setup_sample_data():
    generate_synthetic_transactions()


def test_official_query_1_structuring():
    """
    Official Query 1: 'Find structuring patterns in the last 30 days'
    Expected: filter data -> structuring rule -> risk classify -> explain -> escalate
    Skipped: eda, ml_anomaly, aggregation_rule, entity_lookup
    """
    q1 = "Find structuring patterns in the last 30 days"
    resp = run_agent(q1)

    assert resp.error is None
    assert resp.detected_intent.intent_type == "pattern_search"
    assert resp.detected_intent.target_pattern == "structuring"

    tools_used = resp.execution_summary.tools_used
    tools_skipped = resp.execution_summary.tools_skipped

    assert "structuring_rule" in tools_used
    assert "eda" in tools_skipped
    assert "ml_anomaly" in tools_skipped
    assert "aggregation_rule" in tools_skipped
    assert len(resp.results) > 0


def test_official_query_2_aggregation():
    """
    Official Query 2: 'Which customers made 10+ transactions under $10,000?'
    Expected: filter data -> simple aggregation only -> explain -> escalate
    Skipped: feature_engineering, ml_anomaly, structuring_rule, eda
    """
    q2 = "Which customers made 10+ transactions under $10,000?"
    resp = run_agent(q2)

    assert resp.error is None
    assert resp.detected_intent.intent_type == "aggregation_query"

    tools_used = resp.execution_summary.tools_used
    tools_skipped = resp.execution_summary.tools_skipped

    assert "aggregation_rule" in tools_used
    assert "feature_engineering" in tools_skipped
    assert "ml_anomaly" in tools_skipped
    assert "structuring_rule" in tools_skipped
    assert len(resp.results) > 0


def test_official_query_3_entity_lookup():
    """
    Official Query 3: 'Is customer ID 4521 suspicious?'
    Expected: entity lookup only -> risk classify -> explain -> escalate
    Skipped: data_loader, eda, ml_anomaly, aggregation_rule
    """
    q3 = "Is customer ID 4521 suspicious?"
    resp = run_agent(q3)

    assert resp.error is None
    assert resp.detected_intent.intent_type == "entity_lookup"
    assert resp.detected_intent.entity_id == "CUST4521"

    tools_used = resp.execution_summary.tools_used
    tools_skipped = resp.execution_summary.tools_skipped

    assert "entity_lookup" in tools_used
    assert "data_loader" in tools_skipped
    assert "ml_anomaly" in tools_skipped
    assert "eda" in tools_skipped
    assert len(resp.results) == 1
    assert resp.results[0].customer_id == "CUST4521"


def test_edge_case_unknown_customer():
    q_unknown = "Is customer ID CUST999999 suspicious?"
    resp = run_agent(q_unknown)
    assert resp.error is None
    assert len(resp.results) == 1
    assert resp.results[0].risk_level == "Low"


def test_edge_case_ambiguous_query():
    q_ambiguous = "Tell me about transaction trends"
    resp = run_agent(q_ambiguous)
    assert resp.error is None
    assert "eda" in resp.execution_summary.tools_used
    assert "charts" in resp.execution_summary.tools_used
