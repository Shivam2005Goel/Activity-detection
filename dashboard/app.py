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
    page_title="Agentic AML Intelligence Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Professional CSS Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
    }

    /* Main Banner */
    .main-banner {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.9) 0%, rgba(49, 46, 129, 0.8) 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 32px 40px;
        margin-bottom: 30px;
        box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.1);
        position: relative;
        overflow: hidden;
    }
    
    .main-banner::before {
        content: '';
        position: absolute;
        top: -50%; left: -50%; width: 200%; height: 200%;
        background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 60%);
        animation: rotate 20s linear infinite;
        pointer-events: none;
    }
    
    @keyframes rotate {
        100% { transform: rotate(360deg); }
    }

    .main-banner h1 {
        font-size: 2.6rem;
        font-weight: 700;
        background: linear-gradient(to right, #60A5FA, #A78BFA, #F472B6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 10px 0;
        letter-spacing: -0.02em;
    }
    
    .main-banner p {
        font-size: 1.15rem;
        color: #94A3B8;
        margin: 0;
    }

    /* Metric Boxes */
    .metric-box {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 16px;
        padding: 20px 24px;
        text-align: center;
        box-shadow: 0 8px 16px -4px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .metric-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px -4px rgba(0, 0, 0, 0.5);
        border-color: rgba(255,255,255,0.15);
        background: rgba(30, 41, 59, 0.8);
    }
    
    .metric-box .label {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #94A3B8;
        letter-spacing: 0.1em;
        margin-bottom: 6px;
    }
    
    .metric-box .value {
        font-size: 1.8rem;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #F8FAFC;
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .badge-critical { background: linear-gradient(135deg, #991B1B 0%, #7F1D1D 100%); color: #FECDD3; border: 1px solid #F43F5E; }
    .badge-high { background: linear-gradient(135deg, #9A3412 0%, #7C2D12 100%); color: #FFEDD5; border: 1px solid #FB923C; }
    .badge-medium { background: linear-gradient(135deg, #92400E 0%, #78350F 100%); color: #FEF3C7; border: 1px solid #FBBF24; }
    .badge-low { background: linear-gradient(135deg, #065F46 0%, #064E3B 100%); color: #D1FAE5; border: 1px solid #34D399; }
    
    .badge-report { background: linear-gradient(135deg, #9D174D 0%, #831843 100%); color: #FFE4E6; border: 1px solid #E11D48; }
    .badge-review { background: linear-gradient(135deg, #854D0E 0%, #713F12 100%); color: #FEF08A; border: 1px solid #CA8A04; }
    .badge-monitor { background: linear-gradient(135deg, #1E40AF 0%, #1E3A8A 100%); color: #BFDBFE; border: 1px solid #3B82F6; }

    /* Tool Cards */
    .tool-card-executed {
        background: linear-gradient(to right, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05));
        border-left: 4px solid #10B981;
        border-radius: 6px 12px 12px 6px;
        padding: 12px 16px;
        margin-bottom: 10px;
        color: #D1FAE5;
        font-weight: 500;
        font-size: 0.95rem;
        transition: transform 0.2s;
    }
    
    .tool-card-executed:hover { transform: translateX(5px); }

    .tool-card-skipped {
        background: linear-gradient(to right, rgba(100, 116, 139, 0.15), rgba(100, 116, 139, 0.05));
        border-left: 4px solid #475569;
        border-radius: 6px 12px 12px 6px;
        padding: 12px 16px;
        margin-bottom: 10px;
        color: #94A3B8;
        font-weight: 400;
        font-size: 0.95rem;
        transition: transform 0.2s;
    }

    .tool-card-skipped:hover { transform: translateX(5px); }

    /* Search Area Customization */
    [data-testid="stTextInput"] > div > div > input {
        border-radius: 12px !important;
        border: 2px solid rgba(99, 102, 241, 0.3) !important;
        padding: 16px 20px !important;
        font-size: 1.1rem !important;
        background: rgba(15, 23, 42, 0.7) !important;
        color: white !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }

    [data-testid="stTextInput"] > div > div > input:focus {
        border-color: #8B5CF6 !important;
        box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.2) !important;
        background: rgba(15, 23, 42, 0.9) !important;
    }

    /* Buttons */
    [data-testid="stButton"] button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stButton"] button[kind="primary"] {
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%) !important;
        border: none !important;
        box-shadow: 0 6px 16px -4px rgba(139, 92, 246, 0.5) !important;
    }

    [data-testid="stButton"] button[kind="primary"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 20px -4px rgba(139, 92, 246, 0.6) !important;
    }
</style>
""", unsafe_allow_html=True)

# Main Banner Header
st.markdown("""
<div class="main-banner">
    <h1>🛡️ Agentic AML Suspicious Activity Intelligence Center</h1>
    <p>Societe Generale AML Hackathon — Dynamic Multi-Agent Planning & Explainable Suspicious Activity Detection</p>
</div>
""", unsafe_allow_html=True)

# Sidebar Audit Trail & Benchmark Summary
with st.sidebar:
    st.markdown("### 📋 System Audit Log")
    st.caption("Live append-only audit trail (`audit_log.jsonl`)")

    logs = get_recent_audit_logs(limit=10)
    if logs:
        for entry in logs:
            st.markdown(f"**[{entry.get('event_type')}]** `{entry.get('timestamp')[:19]}`")
            st.json(entry.get("payload", {}), expanded=False)
            st.divider()
    else:
        st.info("No audit entries logged yet.")

    st.markdown("---")
    st.markdown("### 🏆 IBM AML Benchmark")
    backtest_path = Path(config.BACKTEST_RESULTS_PATH)
    if backtest_path.exists():
        try:
            with open(backtest_path, "r") as f:
                b_results = json.load(f)
            sup = b_results.get("supervised_model", {})
            unsup = b_results.get("unsupervised_model", {})
            
            st.markdown(f"""
            <div style="background:#1E293B; border:1px solid #334155; border-radius:10px; padding:12px;">
                <div style="color:#6366F1; font-weight:700; margin-bottom:6px;">XGBoost Supervised</div>
                <div>Precision: <b>{sup.get('precision', 'N/A')}</b></div>
                <div>Recall: <b>{sup.get('recall', 'N/A')}</b></div>
                <hr style="margin:8px 0; border-color:#334155;">
                <div style="color:#10B981; font-weight:700; margin-bottom:6px;">PyOD IsolationForest</div>
                <div>Precision: <b>{unsup.get('precision', 'N/A')}</b></div>
                <div>Recall: <b>{unsup.get('recall', 'N/A')}</b></div>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass

# Main Application Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 AI Query & Dynamic Pipeline",
    "📊 Dataset & Transaction Explorer",
    "📋 Governance & Audit Trail",
    "🏆 IBM Benchmark Validation"
])

# Tab 1: AI Query & Dynamic Pipeline Execution
with tab1:
    st.markdown("""
    <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
        <h2 style="font-family: 'Outfit', sans-serif; font-size: 2.2rem; margin-bottom: 0.5rem; background: linear-gradient(to right, #e2e8f0, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">What would you like to investigate?</h2>
        <p style="color: #94a3b8; font-size: 1.1rem;">Search across customers, transactions, and AI-detected patterns</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### 💡 Quick Launch Preset Queries")
    c1, c2, c3 = st.columns(3)
    
    preset_query = None
    with c1:
        if st.button("1️⃣ Structuring Patterns (30 Days)", use_container_width=True):
            preset_query = "Find structuring patterns in the last 30 days"
    with c2:
        if st.button("2️⃣ 10+ Txns Under $10,000", use_container_width=True):
            preset_query = "Which customers made 10+ transactions under $10,000?"
    with c3:
        if st.button("3️⃣ Customer CUST4521 Check", use_container_width=True):
            preset_query = "Is customer ID 4521 suspicious?"

    st.markdown("<br>", unsafe_allow_html=True)
    
    user_query = st.text_input(
        "Search Query",
        value=preset_query if preset_query else "Find structuring patterns in the last 30 days",
        placeholder="e.g. Find structuring patterns in the last 30 days...",
        label_visibility="collapsed"
    )

    run_button = st.button("🚀 Execute Agent Pipeline", type="primary", use_container_width=True)

    if run_button or preset_query:
        with st.spinner("Processing natural language intent & executing dynamic tool plan..."):
            response = None
            try:
                import httpx
                from schemas import AgentResponse
                api_res = httpx.post("http://localhost:8000/agent/query", json={"query": user_query}, timeout=15.0)
                if api_res.status_code == 200:
                    response = AgentResponse(**api_res.json())
            except Exception:
                pass

            if response is None:
                try:
                    response = run_agent(user_query)
                except Exception as e:
                    st.error(f"Execution Error: {str(e)}")
                    response = None

        if response:
            if response.error:
                st.error(f"Error: {response.error}")

            st.markdown("---")

            # Intent & Verification KPI Row
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="label">Intent Strategy</div>
                    <div class="value">{response.detected_intent.intent_type.replace('_', ' ').title()}</div>
                </div>
                """, unsafe_allow_html=True)
            with k2:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="label">Target Pattern</div>
                    <div class="value">{response.detected_intent.target_pattern.upper()}</div>
                </div>
                """, unsafe_allow_html=True)
            with k3:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="label">Entities Flagged</div>
                    <div class="value">{len(response.results)}</div>
                </div>
                """, unsafe_allow_html=True)
            with k4:
                v_status = response.execution_summary.verification_status
                status_color = "#10B981" if v_status == "Passed" else "#F59E0B"
                st.markdown(f"""
                <div class="metric-box">
                    <div class="label">Critic Verification</div>
                    <div class="value" style="color:{status_color};">{v_status}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # Dynamic Execution Plan Trace
            st.markdown("#### 🧩 Dynamic Tool Path Visualization")
            st.caption("Visually verifies that the system parsed intent and invoked ONLY necessary tools while skipping the rest.")

            e_col, s_col = st.columns(2)
            with e_col:
                st.markdown(f"**Executed Tools ({len(response.execution_summary.tools_used)})**")
                for tool in response.execution_summary.tools_used:
                    st.markdown(f'<div class="tool-card-executed">✅ <b>{tool}</b></div>', unsafe_allow_html=True)

            with s_col:
                st.markdown(f"**Skipped Tools ({len(response.execution_summary.tools_skipped)})**")
                for tool in response.execution_summary.tools_skipped:
                    st.markdown(f'<div class="tool-card-skipped">⬜ <b>{tool}</b> (Bypassed for efficiency)</div>', unsafe_allow_html=True)

            if response.execution_summary.bias_warning:
                st.warning(f"⚠️ **Demographic Bias Warning:** {response.execution_summary.bias_warning.get('status')}")

            st.markdown("---")

            # Flagged Entities Results Table
            st.markdown("#### 🚩 Flagged Suspicious Entities")
            if response.results:
                table_rows = []
                for item in response.results:
                    table_rows.append({
                        "Customer ID": item.customer_id,
                        "Risk Level": item.risk_level,
                        "Risk Score": f"{item.risk_score:.1f} / 100",
                        "Trust Score": f"{item.trust_score:.1f} / 100",
                        "Pattern Matched": item.pattern_matched if item.pattern_matched else "N/A",
                        "Recommended Action": item.recommended_action.upper(),
                        "Evidence Count": len(item.evidence_transaction_ids)
                    })

                df_results = pd.DataFrame(table_rows)

                st.dataframe(
                    df_results,
                    use_container_width=True,
                    hide_index=True
                )

                # Explanations & Evidence Cards
                st.markdown("#### 📝 Fact-Based Evidence & Explanations")
                for item in response.results:
                    level_class = f"badge-{item.risk_level.lower()}"
                    action_class = f"badge-{item.recommended_action.lower()}"
                    
                    header_html = (
                        f"Customer: <b>{item.customer_id}</b> &nbsp;|&nbsp; "
                        f"Risk Level: <span class='badge {level_class}'>{item.risk_level} ({item.risk_score}/100)</span> &nbsp;|&nbsp; "
                        f"Action: <span class='badge {action_class}'>{item.recommended_action.upper()}</span>"
                    )

                    with st.expander(f"Entity {item.customer_id} — {item.risk_level} Risk"):
                        st.markdown(header_html, unsafe_allow_html=True)
                        st.markdown(f"<p style='margin-top:10px; font-size:1.05rem;'><b>Factual Explanation:</b> {item.explanation}</p>", unsafe_allow_html=True)
                        st.markdown(f"**Evidence Transaction IDs:** `{item.evidence_transaction_ids}`")
                        
                        if item.consensus:
                            st.markdown("**Consensus Verdict Breakdown:**")
                            st.json(item.consensus, expanded=False)

            else:
                st.info("No suspicious entities met the flagging threshold for this query.")

            if getattr(response, 'extracted_data', None):
                st.markdown("---")
                st.markdown("#### 🗃️ Extracted Transactions Data")
                st.dataframe(pd.DataFrame(response.extracted_data), use_container_width=True)

            # Charts Rendering
            if response.charts:
                st.markdown("---")
                st.markdown("#### 📊 Dynamic Visualizations")
                for chart_json in response.charts:
                    try:
                        fig = pio.from_json(chart_json)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception:
                        pass

# Tab 2: Dataset & Transaction Explorer
with tab2:
    st.markdown("#### 📊 Dataset & Transaction Analytics")
    if Path(config.DATA_PATH).exists():
        try:
            df_raw = pd.read_csv(config.DATA_PATH)
            
            def format_currency(val):
                if val >= 1_000_000_000:
                    return f"${val/1_000_000_000:.2f}B"
                elif val >= 1_000_000:
                    return f"${val/1_000_000:.2f}M"
                elif val >= 1_000:
                    return f"${val/1_000:.2f}K"
                else:
                    return f"${val:.2f}"

            d1, d2, d3, d4 = st.columns(4)
            with d1:
                st.metric("Total Transactions", f"{len(df_raw):,}")
            with d2:
                st.metric("Total Volume (USD)", format_currency(df_raw['amount'].sum()))
            with d3:
                st.metric("Mean Amount", format_currency(df_raw['amount'].mean()))
            with d4:
                st.metric("Distinct Customers", f"{df_raw['customer_id'].nunique():,}")

            st.markdown("<br>", unsafe_allow_html=True)
            st.dataframe(df_raw, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading dataset: {str(e)}")

# Tab 3: Governance & Audit Trail
with tab3:
    st.markdown("#### 📋 Governance & Execution Audit Trail")
    st.caption("Complete chronological record of system operations, intents, tool calls, and verifications.")
    
    all_logs = get_recent_audit_logs(limit=50)
    if all_logs:
        df_logs = pd.DataFrame(all_logs)
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No audit logs available.")

# Tab 4: IBM Benchmark Validation
with tab4:
    st.markdown("#### 🏆 Offline Supervised vs Unsupervised Benchmark Validation")
    st.caption("Evaluated on Kaggle IBM Transactions for Anti-Money Laundering (AML) held-out dataset.")
    
    backtest_path = Path(config.BACKTEST_RESULTS_PATH)
    if backtest_path.exists():
        try:
            with open(backtest_path, "r") as f:
                b_results = json.load(f)
            
            col_sup, col_unsup = st.columns(2)
            with col_sup:
                st.markdown("### 🤖 Supervised Model (XGBoost)")
                sup_data = b_results.get("supervised_model", {})
                st.metric("Precision", sup_data.get("precision"))
                st.metric("Recall", sup_data.get("recall"))
                st.metric("F1 Score", sup_data.get("f1_score"))
                st.json(sup_data.get("confusion_matrix", []), expanded=True)

            with col_unsup:
                st.markdown("### 🔍 Unsupervised Model (PyOD IsolationForest)")
                unsup_data = b_results.get("unsupervised_model", {})
                st.metric("Precision", unsup_data.get("precision"))
                st.metric("Recall", unsup_data.get("recall"))
                st.metric("F1 Score", unsup_data.get("f1_score"))
        except Exception as e:
            st.error(f"Error reading backtest results: {str(e)}")
    else:
        st.info("Run `python scripts/backtest_ibm_dataset.py` to generate backtest metrics.")
