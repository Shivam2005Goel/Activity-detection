import re
import pandas as pd
from typing import Tuple, List
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from schemas import AgentResponse, FlaggedItem
from safety.audit_logger import log_event


def verify(draft_response: AgentResponse, source_data: pd.DataFrame = None) -> Tuple[bool, AgentResponse]:
    """
    Verifier/Critic Agent: Audits draft AgentResponse for numerical accuracy against source data,
    risk level threshold consistency, and escalation action alignment.
    Returns: (is_passed: bool, corrected_response: AgentResponse)
    """
    if draft_response is None or not draft_response.results:
        draft_response.execution_summary.verification_status = "Passed"
        return True, draft_response

    all_passed = True
    corrected_results: List[FlaggedItem] = []

    for item in draft_response.results:
        item_passed = True

        # 1. Verify Risk Level consistency with Risk Score
        expected_level = "Low"
        if item.risk_score <= config.RISK_LOW_MAX:
            expected_level = "Low"
        elif item.risk_score <= config.RISK_MEDIUM_MAX:
            expected_level = "Medium"
        elif item.risk_score <= config.RISK_HIGH_MAX:
            expected_level = "High"
        else:
            expected_level = "Critical"

        # Apply override check: structuring or layering forces minimum Medium
        pattern = (item.pattern_matched or "").lower()
        if pattern in ["structuring", "smurfing", "layering"] and expected_level == "Low":
            expected_level = "Medium"

        if item.risk_level != expected_level:
            item_passed = False
            item.risk_level = expected_level  # Auto-correct level

        # 2. Verify Recommended Action alignment with Risk Level
        if item.risk_level in ["High", "Critical"] and item.recommended_action == "monitor":
            item_passed = False
            item.recommended_action = "report"  # Auto-correct action
        elif item.risk_level == "Low" and item.recommended_action == "report":
            item_passed = False
            item.recommended_action = "monitor"  # Auto-correct action

        # 3. Fact-check numeric evidence against source data (if provided)
        if source_data is not None and not source_data.empty and item.evidence_transaction_ids:
            try:
                evidence_df = source_data[source_data["transaction_id"].isin(item.evidence_transaction_ids)]
                if not evidence_df.empty:
                    # Extract dollar amounts mentioned in explanation string using regex
                    amounts_in_text = [float(x.replace(",", "")) for x in re.findall(r"\$([\d,]+(?:\.\d+)?)", item.explanation)]
                    actual_amounts = set(evidence_df["amount"].round(2).tolist())
                    actual_sum = round(evidence_df["amount"].sum(), 2)

                    # If text mentions a specific dollar amount, verify it exists in evidence transactions or is the total sum
                    for text_amt in amounts_in_text:
                        if text_amt not in actual_amounts and round(text_amt, 2) != actual_sum:
                            # Flag potential hallucinated number
                            item_passed = False
            except Exception as e:
                print(f"Verifier fact-check warning: {str(e)}")

        if not item_passed:
            all_passed = False

        corrected_results.append(item)

    draft_response.results = corrected_results
    status = "Passed" if all_passed else "Needs Review"
    draft_response.execution_summary.verification_status = status

    log_event("VERIFICATION_COMPLETED", {
        "status": status,
        "items_audited": len(corrected_results),
        "all_passed": all_passed
    })

    return all_passed, draft_response
