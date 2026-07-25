import pandas as pd
from typing import Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from safety.fallback_handler import safe_tool_call
from tools.charts import generate_charts


@safe_tool_call("eda")
def run_eda(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Exploratory Data Analysis Tool: Computes summary statistics, distributions,
    and top customer volume summaries.
    """
    if df is None or df.empty:
        return {
            "total_transactions": 0,
            "total_volume": 0.0,
            "mean_amount": 0.0,
            "median_amount": 0.0,
            "txn_type_counts": {},
            "top_customers": []
        }

    total_txns = len(df)
    total_vol = float(df["amount"].sum())
    mean_amt = float(df["amount"].mean())
    median_amt = float(df["amount"].median())
    
    type_counts = df["transaction_type"].value_counts().to_dict()
    
    top_custs = (
        df.groupby("customer_id")["amount"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
        .to_dict()
    )
    
    charts = generate_charts(df)

    return {
        "total_transactions": total_txns,
        "total_volume": round(total_vol, 2),
        "mean_amount": round(mean_amt, 2),
        "median_amount": round(median_amt, 2),
        "txn_type_counts": type_counts,
        "top_customers": top_custs,
        "charts": charts
    }
