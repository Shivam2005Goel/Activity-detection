import pytest
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from agents.query_understanding import _keyword_regex_fallback_parser, parse_intent
from agents.planner import build_plan
from agents.verifier import verify
from schemas import Intent, AgentResponse, ExecutionSummary, FlaggedItem


def test_query_understanding_fallback():
    # Test Structuring query
    i1 = _keyword_regex_fallback_parser("Find structuring patterns in the last 30 days")
    assert i1.intent_type == "pattern_search"
    assert i1.target_pattern == "structuring"

    # Test Aggregation query
    i2 = _keyword_regex_fallback_parser("Which customers made 10+ transactions under $10,000?")
    assert i2.intent_type == "aggregation_query"
    assert i2.filters.min_transaction_count == 10
    assert i2.filters.amount_threshold == 10000.0

    # Test Entity Lookup query
    i3 = _keyword_regex_fallback_parser("Is customer ID 4521 suspicious?")
    assert i3.intent_type == "entity_lookup"
    assert i3.entity_id == "CUST4521"


def test_planner_paths():
    # Structuring intent -> planned path
    i1 = Intent(intent_type="pattern_search", target_pattern="structuring")
    planned, skipped = build_plan(i1)
    assert "structuring_rule" in planned
    assert "eda" in skipped
    assert "ml_anomaly" in skipped

    # Aggregation intent -> planned path
    i2 = Intent(intent_type="aggregation_query")
    planned, skipped = build_plan(i2)
    assert "aggregation_rule" in planned
    assert "structuring_rule" in skipped
    assert "ml_anomaly" in skipped

    # Entity lookup intent -> planned path
    i3 = Intent(intent_type="entity_lookup", entity_id="CUST4521")
    planned, skipped = build_plan(i3)
    assert "entity_lookup" in planned
    assert "data_loader" in skipped
    assert "ml_anomaly" in skipped


def test_verifier_critic():
    item = FlaggedItem(
        customer_id="CUST4521",
        risk_score=85.0,
        risk_level="Low",  # Intentionally wrong level to test auto-correct
        confidence=90.0,
        trust_score=95.0,
        pattern_matched="structuring",
        explanation="Customer CUST4521 made 10 cash deposits.",
        evidence_transaction_ids=["TXN00001"],
        recommended_action="monitor"  # Intentionally wrong action for high risk
    )

    draft = AgentResponse(
        query="Test query",
        detected_intent=Intent(intent_type="pattern_search"),
        results=[item],
        execution_summary=ExecutionSummary(agents_used=[], tools_used=[], tools_skipped=[])
    )

    passed, corrected = verify(draft)
    assert passed is False  # Verification caught auto-correctable issues
    assert corrected.results[0].risk_level in ["Medium", "High"]
    assert corrected.results[0].recommended_action in ["review", "report"]
