import pandas as pd
from typing import List, Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from safety.fallback_handler import safe_tool_call


@safe_tool_call("structuring_rule")
def detect_structuring(df_features: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detects structuring (smurfing) patterns: multiple cash deposits or transfers
    just under the regulatory reporting threshold within a rolling time window.
    """
    if df_features is None or df_features.empty:
        return []

    df_copy = df_features.copy()
    if "is_just_under_threshold" not in df_copy.columns:
        df_copy["is_just_under_threshold"] = (
            (df_copy["amount"] >= config.STRUCTURING_AMOUNT_LOWER_BOUND) &
            (df_copy["amount"] < config.STRUCTURING_AMOUNT_THRESHOLD)
        )

    # Filter to transactions in the threshold proximity range
    just_under_df = df_copy[df_copy["is_just_under_threshold"]].copy()
    if just_under_df.empty:
        return []

    just_under_df["timestamp_dt"] = pd.to_datetime(just_under_df["timestamp"])
    just_under_df = just_under_df.sort_values(by=["customer_id", "timestamp_dt"])

    flagged_structuring = []
    window_days = f"{config.STRUCTURING_WINDOW_DAYS}D"

    for customer_id, group in just_under_df.groupby("customer_id"):
        group_indexed = group.set_index("timestamp_dt")
        
        # Calculate rolling count within time window
        rolling_counts = group_indexed["transaction_id"].rolling(window_days).count()
        
        max_rolling = rolling_counts.max()
        if max_rolling >= config.STRUCTURING_MIN_TXN_COUNT:
            evidence_txn_ids = group["transaction_id"].tolist()
            total_amount = group["amount"].sum()
            
            # Score 80-100 based on count intensity
            rule_score = min(100.0, 70.0 + (max_rolling * 3.0))
            
            flagged_structuring.append({
                "customer_id": customer_id,
                "rule_fired": "structuring",
                "supporting_txn_ids": evidence_txn_ids,
                "txn_count": len(evidence_txn_ids),
                "total_amount": round(total_amount, 2),
                "rule_score": round(rule_score, 1)
            })

    return flagged_structuring
