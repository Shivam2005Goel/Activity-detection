import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from safety.fallback_handler import safe_tool_call


@safe_tool_call("charts")
def generate_charts(df: pd.DataFrame, results: Optional[List[Any]] = None) -> List[str]:
    """
    Generates interactive Plotly figures formatted as JSON strings for Streamlit UI rendering.
    """
    charts_json = []

    if df is None or df.empty:
        return charts_json

    # 1. Transaction Timeline Chart
    try:
        df_timeline = df.copy()
        df_timeline["date"] = pd.to_datetime(df_timeline["timestamp"]).dt.date
        daily_agg = df_timeline.groupby("date").agg(
            daily_amount=("amount", "sum"),
            daily_count=("transaction_id", "count")
        ).reset_index()

        fig_timeline = px.line(
            daily_agg,
            x="date",
            y="daily_amount",
            title="Daily Transaction Volume (USD)",
            labels={"date": "Date", "daily_amount": "Volume ($)"},
            template="plotly_dark"
        )
        charts_json.append(fig_timeline.to_json())
    except Exception as e:
        print(f"Chart error (timeline): {str(e)}")

    # 2. Risk Level Breakdown Donut Chart (if results available)
    if results:
        try:
            risk_levels = [r.risk_level for r in results]
            level_counts = pd.Series(risk_levels).value_counts().reset_index()
            level_counts.columns = ["risk_level", "count"]

            color_map = {
                "Low": "#28a745",
                "Medium": "#ffc107",
                "High": "#fd7e14",
                "Critical": "#dc3545"
            }

            fig_risk = px.pie(
                level_counts,
                names="risk_level",
                values="count",
                title="Flagged Risk Classification Breakdown",
                color="risk_level",
                color_discrete_map=color_map,
                hole=0.4,
                template="plotly_dark"
            )
            charts_json.append(fig_risk.to_json())
        except Exception as e:
            print(f"Chart error (risk breakdown): {str(e)}")

    # 3. Transaction Amount Distribution Histogram
    try:
        fig_hist = px.histogram(
            df,
            x="amount",
            nbins=30,
            title="Transaction Amount Distribution ($)",
            labels={"amount": "Transaction Amount ($)"},
            template="plotly_dark"
        )
        charts_json.append(fig_hist.to_json())
    except Exception as e:
        print(f"Chart error (histogram): {str(e)}")

    return charts_json
