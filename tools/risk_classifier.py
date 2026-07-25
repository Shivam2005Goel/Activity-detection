from typing import Tuple, Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from safety.fallback_handler import safe_tool_call


@safe_tool_call("risk_classifier")
def classify_risk(item_consensus: Dict[str, Any]) -> Tuple[float, str]:
    """
    Classifies risk score (0-100) and risk level (Low, Medium, High, Critical)
    with mandatory override rules for pattern hits.
    """
    raw_score = item_consensus.get("combined_score", 0.0)
    pattern = item_consensus.get("pattern_matched", "")

    # Base classification by thresholds
    if raw_score <= config.RISK_LOW_MAX:
        level = "Low"
    elif raw_score <= config.RISK_MEDIUM_MAX:
        level = "Medium"
    elif raw_score <= config.RISK_HIGH_MAX:
        level = "High"
    else:
        level = "Critical"

    # Mandatory Override Rule: Any structuring or layering rule hit forces minimum "Medium" level
    if pattern in ["structuring", "smurfing", "layering"] and level == "Low":
        level = "Medium"
        raw_score = max(raw_score, 45.0)

    return round(raw_score, 1), level
