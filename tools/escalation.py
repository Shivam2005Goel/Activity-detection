from typing import Literal
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from safety.fallback_handler import safe_tool_call


@safe_tool_call("escalation")
def recommend_action(risk_level: str) -> Literal["monitor", "review", "report"]:
    """
    Recommends action based on risk level:
    Low -> monitor
    Medium -> review
    High / Critical -> report
    """
    level_lower = str(risk_level).lower()
    
    if level_lower == "low":
        return "monitor"
    elif level_lower == "medium":
        return "review"
    elif level_lower in ["high", "critical"]:
        return "report"
    else:
        return "review"
