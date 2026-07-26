import pandas as pd
from typing import Optional
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from schemas import Filters
from safety.fallback_handler import safe_tool_call


@safe_tool_call("aggregation_rule")
def run_aggregation(df: pd.DataFrame, filters: Optional[Filters] = None) -> pd.DataFrame:
    """
    Performs dynamic aggregation per customer matching query filter conditions.
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=["customer_id", "transaction_count", "total_amount", "avg_amount"])

    # Group by customer_id
    agg_df = df.groupby("customer_id").agg(
        transaction_count=("transaction_id", "count"),
        total_amount=("amount", "sum"),
        avg_amount=("amount", "mean"),
        evidence_transaction_ids=("transaction_id", lambda x: list(x))
    ).reset_index()

    min_count = filters.min_transaction_count if (filters and filters.min_transaction_count is not None) else 1

    # Apply min count filter
    filtered_agg = agg_df[agg_df["transaction_count"] >= min_count].copy()
    filtered_agg.sort_values(by="transaction_count", ascending=False, inplace=True)
    
    if filters and getattr(filters, "limit", None):
        filtered_agg = filtered_agg.head(filters.limit)
        
    return filtered_agg
