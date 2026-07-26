import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import httpx
import re

from safety.fallback_handler import safe_tool_call
from safety.audit_logger import log_event
import config

def _call_openrouter_charts(query: str, df_info: str) -> str:
    """Calls OpenRouter LLM to generate Python code for a Plotly chart."""
    if not config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set.")

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"You are a Python Data Visualization expert. "
        f"A user asked: '{query}'\n\n"
        f"You have access to two Pandas DataFrames:\n"
        f"1. `df` (Raw transaction data): {df_info.get('df_info', 'N/A')}\n"
        f"2. `agg_df` (Aggregated customer data): {df_info.get('agg_info', 'N/A')}\n\n"
        f"Write Python code using `plotly.express` as `px` or `plotly.graph_objects` as `go` to generate a chart that answers the user's query. "
        f"Choose either `df` or `agg_df` depending on what the query asks. "
        f"The chart object MUST be assigned to a variable named `fig`.\n"
        f"Ensure `fig.update_layout(template='plotly_dark')` is used.\n"
        f"Only return the raw python code. Do not include markdown code blocks (```python) or explanations. Just the raw text."
    )

    payload = {
        "model": config.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }

    response = httpx.post(
        f"{config.OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=config.LLM_TIMEOUT_SECONDS
    )

    if response.status_code == 200:
        code = response.json()["choices"][0]["message"]["content"].strip()
        # strip markdown blocks if they still exist
        code = re.sub(r"^```python\s*", "", code)
        code = re.sub(r"```\s*$", "", code)
        return code
    else:
        raise RuntimeError(f"OpenRouter status {response.status_code}: {response.text}")


@safe_tool_call("charts")
def generate_charts(df: pd.DataFrame, results: Optional[List[Any]] = None, intent: Optional[Any] = None, state: Optional[Dict] = None, user_query: Optional[str] = None) -> List[str]:
    """
    Generates interactive Plotly figures formatted as JSON strings for Streamlit UI rendering.
    """
    charts_json = []

    if df is None or df.empty:
        return charts_json

    # 1. Dynamic LLM Generated Chart
    llm_success = False
    print(f"DEBUG CHARTS: config={bool(config.OPENROUTER_API_KEY)}, user_query={user_query}")
    if config.OPENROUTER_API_KEY and user_query:
        try:
            df_info_dict = {}
            if df is not None and not df.empty:
                df_info_dict["df_info"] = f"Columns: {list(df.columns)}, Sample Row: {df.iloc[0].to_dict()}"
            
            agg_df = state.get("aggregation_df") if state else None
            if agg_df is not None and not agg_df.empty:
                df_info_dict["agg_info"] = f"Columns: {list(agg_df.columns)}, Sample Row: {agg_df.iloc[0].to_dict()}"
            
            if df_info_dict:
                code = _call_openrouter_charts(user_query, df_info_dict)
                log_event("CHART_LLM_SUCCESS", {"query": user_query, "code_generated": code})
                
                # Execute the code in a restricted local scope
                local_scope = {"pd": pd, "px": px, "go": go, "df": df.copy()}
                if agg_df is not None:
                    local_scope["agg_df"] = agg_df.copy()
                
                exec(code, {}, local_scope)
                
                print(f"DEBUG CHARTS: fig in local_scope? {'fig' in local_scope}")
                if "fig" in local_scope:
                    charts_json.append(local_scope["fig"].to_json())
                    llm_success = True
        except Exception as e:
            print(f"[CHART LLM FALLBACK] Failed to dynamically generate chart: {str(e)}")
            
    if llm_success:
        print(f"DEBUG CHARTS: Returning dynamic chart, len={len(charts_json)}")
        return charts_json # Skip the hardcoded charts if we successfully made a dynamic one
        
    # 2. Transaction Timeline Chart (Fallback)
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

    # 4. Dynamic Aggregation Bar Chart
    if intent and getattr(intent, "intent_type", "") == "aggregation_query" and state and state.get("aggregation_df") is not None:
        try:
            agg_df = state["aggregation_df"]
            if not agg_df.empty:
                # Create a Bar Chart for Top Customers
                fig_bar = px.bar(
                    agg_df,
                    x="customer_id",
                    y="transaction_count",
                    title="Top Customers by Transaction Volume",
                    labels={"customer_id": "Customer ID", "transaction_count": "Total Transactions"},
                    color="transaction_count",
                    template="plotly_dark"
                )
                charts_json.insert(0, fig_bar.to_json()) # Put it first so it's prominent
        except Exception as e:
            print(f"Chart error (dynamic bar chart): {str(e)}")

    print(f"DEBUG CHARTS: Returning fallback charts, len={len(charts_json)}")
    return charts_json
