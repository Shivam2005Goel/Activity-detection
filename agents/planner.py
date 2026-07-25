from typing import List, Tuple
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from schemas import Intent
from tools.tool_registry import get_all_registered_tools
from safety.audit_logger import log_event


def build_plan(intent: Intent) -> Tuple[List[str], List[str]]:
    """
    Planner Agent: Dynamically builds the required tool execution path for a given Intent,
    skipping unnecessary tools to ensure efficient, query-specific execution.
    Returns: (planned_tools, skipped_tools)
    """
    all_tools = get_all_registered_tools()
    plan = []

    if intent.intent_type == "entity_lookup":
        # Entity-scoped lookup bypasses general dataset loading and ML scans
        plan = ["entity_lookup", "risk_classifier", "explanation", "escalation"]

    elif intent.intent_type == "aggregation_query":
        # Simple aggregation skips feature engineering, ML, rules, and consensus
        plan = ["data_loader", "aggregation_rule", "risk_classifier", "explanation", "escalation"]

    elif intent.intent_type == "pattern_search":
        plan = ["data_loader", "feature_engineering"]
        if intent.target_pattern in ["structuring", "smurfing"]:
            plan.append("structuring_rule")
        elif intent.target_pattern == "layering":
            plan.append("graph_layering")
        else:
            plan.append("structuring_rule")
            
        plan.extend(["consensus", "risk_classifier", "explanation", "escalation"])

    elif intent.intent_type == "broad_exploration" or intent.requires_full_eda or intent.requires_ml_detection:
        plan = ["data_loader", "eda", "feature_engineering", "ml_anomaly", "consensus", "risk_classifier", "explanation", "escalation", "charts"]

    else:
        # Default fallback execution path
        plan = ["data_loader", "feature_engineering", "ml_anomaly", "consensus", "risk_classifier", "explanation", "escalation"]

    # Calculate skipped tools (preserving registry order)
    skipped = [t for t in all_tools if t not in plan]

    log_event("PLAN_BUILT", {
        "intent_type": intent.intent_type,
        "target_pattern": intent.target_pattern,
        "planned_tools": plan,
        "skipped_tools": skipped
    })

    return plan, skipped
