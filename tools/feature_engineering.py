import pandas as pd
import numpy as np
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from safety.fallback_handler import safe_tool_call


@safe_tool_call("feature_engineering")
def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes transactional features per customer including rolling counts, velocity,
    amount z-scores, and threshold proximity flags.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df_feats = df.copy()
    df_feats["timestamp_dt"] = pd.to_datetime(df_feats["timestamp"])
    df_feats = df_feats.sort_values(by=["customer_id", "timestamp_dt"]).reset_index(drop=True)

    # 1. Structuring threshold proximity flag
    df_feats["is_just_under_threshold"] = (
        (df_feats["amount"] >= config.STRUCTURING_AMOUNT_LOWER_BOUND) &
        (df_feats["amount"] < config.STRUCTURING_AMOUNT_THRESHOLD)
    )

    # 2. Customer-level mean and std for Z-score calculation
    cust_stats = df_feats.groupby("customer_id")["amount"].agg(["mean", "std"]).reset_index()
    cust_stats["std"] = cust_stats["std"].fillna(1.0).replace(0, 1.0)
    
    df_feats = df_feats.merge(cust_stats, on="customer_id", how="left")
    df_feats["amount_zscore_vs_customer_avg"] = (df_feats["amount"] - df_feats["mean"]) / (df_feats["std"] + 1e-6)
    df_feats.drop(columns=["mean", "std"], inplace=True)

    # 3. Transaction Velocity (hours since previous transaction per customer)
    df_feats["prev_timestamp"] = df_feats.groupby("customer_id")["timestamp_dt"].shift(1)
    time_diff_hours = (df_feats["timestamp_dt"] - df_feats["prev_timestamp"]).dt.total_seconds() / 3600.0
    df_feats["velocity_hours_since_last_txn"] = time_diff_hours.fillna(9999.0)
    df_feats.drop(columns=["prev_timestamp"], inplace=True)

    # 4. Rolling 7-day count and 30-day sum per customer using indexed datetime
    df_feats_indexed = df_feats.set_index("timestamp_dt")
    
    rolling_7d_counts = (
        df_feats_indexed.groupby("customer_id")["transaction_id"]
        .rolling("7D")
        .count()
        .reset_index()
    )
    rolling_30d_sums = (
        df_feats_indexed.groupby("customer_id")["amount"]
        .rolling("30D")
        .sum()
        .reset_index()
    )
    
    df_feats["rolling_7d_count"] = rolling_7d_counts["transaction_id"].values
    df_feats["rolling_30d_sum"] = rolling_30d_sums["amount"].values

    return df_feats
