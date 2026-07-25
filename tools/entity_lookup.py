import pandas as pd
from typing import Dict, Any, List
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from safety.fallback_handler import safe_tool_call
from tools.feature_engineering import compute_features
from tools.structuring_rule import detect_structuring


@safe_tool_call("entity_lookup")
def lookup_entity(customer_id: str, df: pd.DataFrame) -> Dict[str, Any]:
    """
    Pulls specific customer history and runs entity-scoped feature and rule checks.
    """
    if df is None or df.empty:
        return {"customer_id": customer_id, "found": False, "transactions": [], "flagged_patterns": []}

    # Filter to specific customer
    cust_df = df[df["customer_id"].str.upper() == customer_id.upper()].copy()

    if cust_df.empty:
        return {
            "customer_id": customer_id,
            "found": False,
            "transactions_count": 0,
            "transactions": [],
            "flagged_patterns": [],
            "entity_score": 0.0
        }

    # Compute features specifically for this entity
    df_feats = compute_features(cust_df)
    structuring_hits = detect_structuring(df_feats)

    flagged_patterns = []
    entity_score = 10.0  # baseline normal score

    if structuring_hits:
        flagged_patterns.append("structuring")
        entity_score = max(entity_score, structuring_hits[0].get("rule_score", 85.0))

    # Check for large amount spikes
    max_amount = cust_df["amount"].max()
    if max_amount > 50000.0:
        flagged_patterns.append("high_single_transaction_amount")
        entity_score = max(entity_score, 75.0)

    evidence_txn_ids = cust_df["transaction_id"].tolist()

    return {
        "customer_id": customer_id,
        "found": True,
        "transactions_count": len(cust_df),
        "total_volume": round(cust_df["amount"].sum(), 2),
        "avg_amount": round(cust_df["amount"].mean(), 2),
        "flagged_patterns": flagged_patterns,
        "entity_score": entity_score,
        "evidence_txn_ids": evidence_txn_ids,
        "structuring_details": structuring_hits[0] if structuring_hits else None
    }
