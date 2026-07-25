import json
import os
import sys
import pandas as pd
import plotly.io as pio
import streamlit as st
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from agents.orchestrator import run_agent
from safety.audit_logger import get_recent_audit_logs

# Streamlit Page Config
st.set_page_config(
    page_title="Agentic AML Suspicious Activity Detector",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #4F46E5; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #6B7280; margin-bottom: 1.5rem; }
    .badge-passed { background-color: #059669; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; }
    .badge-review { background-color: #D97706; color: white; padding: 4px 12px; border-radius: 12px; font-weight: 600; }
    .card-box { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
    .metric-card { background: linear-gradient(135deg, #1E1B4B 0%, #312E81 100%); padding: 14px; border-radius: 8px; color: white; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🛡️ Agentic AML Suspicious Activity Detection System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Societe Generale AML Hackathon — Dynamic Execution Plan & Multi-Agent Intelligence</div>', unsafe_allow_html=True)

# Sidebar — Audit Log & Benchmark Metrics
with st.sidebar:
    st.header("📋 System Audit Trail")
    st.caption("Live append-only audit log (`audit_log.jsonl`)")
    
    logs = get_recent_audit_logs(limit=15)
    if logs:
        for entry in logs:
            st.markdown(f"**[{entry.get('event_type')}]** `{entry.get('timestamp')[:19]}`")
            st.json(entry.get("payload", {}), expanded=False)
            st.divider()
    else:
        st.info("No audit logs recorded yet. Run a query to start logging.")

    st.markdown("---")
    st.header("📊 Benchmark Validation")
    backtest_path = Path(config.BACKTEST_RESULTS_PATH)
    if backtest_path.exists():
        try:
            with open(backtest_path, "r") as f:
                b_results = json.load(f)
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.subheader("IBM AML Kaggle Benchmark")
            sup = b_results.get("supervised_model", {})
            st.write(f"**Precision:** `{sup.get('precision', 'N/A')}`")
            st.write(f"**Recall:** `{sup.get('recall', 'N/A')}`")
            st.write(f"**F1 Score:** `{sup.get('f1_score', 'N/A')}`")
            st.caption("Offline evaluation on held-out ground truth data")
            st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Could not load benchmark metrics: {str(e)}")
    else:
        st.caption("Run `python scripts/backtest_ibm_dataset.py` to generate offline benchmark metrics.")

# Official Example Query Buttons
st.markdown("### 💡 Quick Launch Example Queries")
col1, col2, col3 = st.columns(3)

preset_query = None
with col1:
    if st.button("1️⃣ Structuring Patterns (30 Days)", use_container_width=True):
        preset_query = "Find structuring patterns in the last 30 days"
with col2:
    if st.button("2️⃣ 10+ Txns Under $10,000", use_container_width=True):
        preset_query = "Which customers made 10+ transactions under $10,000?"
with col3:
    if st.button("3️⃣ Customer CUST4521 Check", use_container_width=True):
        preset_query = "Is customer ID 4521 suspicious?"

# Text Input Area
user_query = st.text_input(
    "Enter Natural Language AML Query:",
    value=preset_query if preset_query else "Find structuring patterns in the last 30 days",
    placeholder="e.g. Find structuring patterns in the last 30 days"
)

run_button = st.button("🚀 Run Dynamic Agent Pipeline", type="primary", use_container_width=True)

if run_button or preset_query:
    with st.spinner("Parsing intent, dynamically building tool execution plan, and executing agents..."):
        try:
            response = run_agent(user_query)
        except Exception as e:
            st.error(f"Error executing agent pipeline: {str(e)}")
            response = None

    if response:
        if response.error:
            st.error(f"Execution Error: {response.error}")

        st.markdown("---")

        # Top Summary Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Detected Intent", response.detected_intent.intent_type.upper())
        with m2:
            st.metric("Target Pattern", response.detected_intent.target_pattern.upper())
        with m3:
            st.metric("Flagged Entities", len(response.results))
        with m4:
            v_status = response.execution_summary.verification_status
            if v_status == "Passed":
                st.markdown('**Verification Status**<br><span class="badge-passed">✅ Passed</span>', unsafe_allow_html=True)
            else:
                st.markdown('**Verification Status**<br><span class="badge-review">⚠️ Needs Review</span>', unsafe_allow_html=True)

        st.markdown("### 🧩 Dynamic Tool Execution Trace")
        st.caption("Visually verifies that the system parsed intent and invoked ONLY necessary tools while skipping the rest.")

        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.success(f"**Executed Tools ({len(response.execution_summary.tools_used)})**")
            for t in response.execution_summary.tools_used:
                st.markdown(f"✅ `{t}`")

        with t_col2:
            st.info(f"**Skipped Tools ({len(response.execution_summary.tools_skipped)})**")
            for t in response.execution_summary.tools_skipped:
                st.markdown(f"⬜ `{t}`")

        if response.execution_summary.bias_warning:
            st.warning(f"⚠️ **Bias Warning:** {response.execution_summary.bias_warning.get('status')}")

        st.markdown("---")

        # Flagged Items Results Table
        st.markdown("### 🚩 Flagged Suspicious Entities")
        if response.results:
            table_data = []
            for item in response.results:
                table_data.append({
                    "Customer ID": item.customer_id,
                    "Risk Level": item.risk_level,
                    "Risk Score (0-100)": item.risk_score,
                    "Trust Score": item.trust_score,
                    "Pattern Matched": item.pattern_matched,
                    "Recommended Action": item.recommended_action.upper(),
                    "Evidence Txns": len(item.evidence_transaction_ids)
                })

            df_table = pd.DataFrame(table_data)

            # Color styling helper
            def color_risk(val):
                if val == "Critical":
                    return "background-color: #7f1d1d; color: white;"
                elif val == "High":
                    return "background-color: #991b1b; color: white;"
                elif val == "Medium":
                    return "background-color: #854d0e; color: white;"
                else:
                    return "background-color: #14532d; color: white;"

            st.dataframe(
                df_table.style.map(color_risk, subset=["Risk Level"]),
                use_container_width=True
            )

            # Explanation Cards & Evidence Details
            st.markdown("#### 📝 Fact-Based Explanations & Evidence")
            for idx, item in enumerate(response.results):
                with st.expander(f"Entity: {item.customer_id} | Risk: {item.risk_level} ({item.risk_score}/100) | Action: {item.recommended_action.upper()}"):
                    st.write(f"**Explanation:** {item.explanation}")
                    st.write(f"**Evidence Transaction IDs:** `{item.evidence_transaction_ids}`")
                    if item.consensus:
                        st.json(item.consensus)

        else:
            st.info("No suspicious entities met the flagging threshold for this query.")

        # Interactive Plotly Charts
        if response.charts:
            st.markdown("---")
            st.markdown("### 📊 Interactive Visualizations")
            c_cols = st.columns(len(response.charts))
            for idx, c_json in enumerate(response.charts):
                with c_cols[idx % len(c_cols)]:
                    fig = pio.from_json(c_json)
                    st.plotly_chart(fig, use_container_width=True)
