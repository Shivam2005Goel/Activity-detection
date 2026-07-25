from typing import List, Dict, Any, Tuple
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from safety.fallback_handler import safe_tool_call


@safe_tool_call("consensus")
def compute_consensus(rule_results: List[Dict[str, Any]], ml_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Consensus Engine: Combines deterministic rule hits and unsupervised ML anomaly scores,
    producing agreement status, weighted risk scores, and trust scores.
    """
    rule_map = {r["customer_id"]: r for r in rule_results}
    ml_map = {m["customer_id"]: m for m in ml_results}

    all_customers = set(rule_map.keys()).union(set(ml_map.keys()))
    consensus_map = {}

    for cust_id in all_customers:
        rule_item = rule_map.get(cust_id)
        ml_item = ml_map.get(cust_id)

        has_rule = rule_item is not None
        has_ml = ml_item is not None and ml_item.get("anomaly_flag", False)

        rule_score = rule_item.get("rule_score", 0.0) if has_rule else 0.0
        ml_score = ml_item.get("ml_score", 0.0) * 100.0 if has_ml else 0.0

        if has_rule and has_ml:
            agreement = "Full agreement"
            # Both rule and ML flag customer -> high combined score and trust
            combined_score = (0.7 * rule_score) + (0.3 * ml_score)
            trust_score = 95.0
            verdict = "Confirmed Suspicious"
        elif has_rule and not has_ml:
            agreement = "Partial"
            # Rule hit without ML anomaly -> deterministic evidence takes priority
            combined_score = max(rule_score, 75.0)
            trust_score = 80.0
            verdict = "Rule Violation"
        elif not has_rule and has_ml:
            agreement = "Disagreement"
            # ML anomaly without rule hit -> lower trust, subject to verifier review
            combined_score = ml_score
            trust_score = 55.0
            verdict = "Statistical Outlier"
        else:
            agreement = "None"
            combined_score = 10.0
            trust_score = 90.0
            verdict = "Normal"

        evidence_ids = []
        if has_rule:
            evidence_ids.extend(rule_item.get("supporting_txn_ids", []))
        if has_ml:
            evidence_ids.extend(ml_item.get("evidence_txn_ids", []))

        # Deduplicate evidence IDs while preserving order
        unique_evidence_ids = list(dict.fromkeys(evidence_ids))

        pattern_matched = None
        if has_rule:
            pattern_matched = rule_item.get("rule_fired", "pattern_match")
        elif has_ml:
            pattern_matched = "statistical_anomaly"

        consensus_map[cust_id] = {
            "customer_id": cust_id,
            "agreement": agreement,
            "rule_score": round(rule_score, 1),
            "ml_score": round(ml_score, 1),
            "combined_score": round(combined_score, 1),
            "trust_score": round(trust_score, 1),
            "verdict": verdict,
            "pattern_matched": pattern_matched,
            "evidence_txn_ids": unique_evidence_ids,
            "rule_details": rule_item,
            "ml_details": ml_item
        }

    return consensus_map
