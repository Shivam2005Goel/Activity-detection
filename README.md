# Agentic AI Suspicious Activity Detection System (Agentic AML)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.25+-red.svg)](https://streamlit.io/)
[![DuckDB](https://img.shields.io/badge/DuckDB-0.9+-yellow.svg)](https://duckdb.org/)

An agentic AI system for detecting money laundering patterns in financial transaction data. Built for the **Societe Generale AML Hackathon**.

The core system architecture **does NOT run a fixed sequential pipeline**. Instead, it parses natural language queries, extracts structured intent, and **dynamically constructs an execution plan** — calling only the required tools and skipping the rest.

---

## 🌟 Key Features

1. **Dynamic Tool Path Planning**: Visually demonstrates query-specific execution paths (tools called vs. skipped).
2. **Deterministic Rules & Unsupervised ML**: Combines structuring/smurfing rules, NetworkX graph layering, and PyOD IsolationForest anomaly detection.
3. **Consensus Engine**: Combines rule hits and ML anomaly scores into weighted trust scores and agreement verdicts (`Full agreement`, `Partial`, `Disagreement`).
4. **Verifier & Critic Agent**: Audits generated draft responses for numerical factuality, risk score consistency, and escalation action alignment.
5. **OpenRouter & Offline Fallbacks**: Connects to OpenRouter LLMs for intent parsing and 1-2 sentence evidence explanations. Seamlessly falls back to deterministic regex/keyword parsers and template generators when offline.
6. **Structured Audit Trail**: Appends all query events, intents, tool calls, and verification steps to `audit_log.jsonl`.
7. **IBM AML Benchmark Validation**: Offline supervised backtest script using XGBoost on Kaggle IBM AML dataset with ground-truth labels.

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/Shivam2005Goel/Activity-detection.git
cd Activity-detection
pip install -r requirements.txt
```

### 2. Generate Synthetic Transaction Dataset

```bash
python scripts/generate_sample_data.py
```

### 3. (Optional) Set OpenRouter API Key

```bash
set OPENROUTER_API_KEY=your_openrouter_api_key_here
```
*(Note: If no key is set, the system automatically uses the offline regex parser and template explainability engine.)*

### 4. Run FastAPI Service

```bash
uvicorn api.main:app --port 8000 --reload
```

### 5. Launch Streamlit Dashboard

```bash
streamlit run dashboard/app.py
```

---

## 💡 Official Example Queries & Execution Paths

| Example Query | Execution Path | Skipped Tools |
| :--- | :--- | :--- |
| **`"Find structuring patterns in the last 30 days"`** | `data_loader` → `feature_engineering` → `structuring_rule` → `consensus` → `risk_classifier` → `explanation` → `escalation` | `eda`, `ml_anomaly`, `aggregation_rule`, `graph_layering`, `entity_lookup` |
| **`"Which customers made 10+ transactions under $10,000?"`** | `data_loader` → `aggregation_rule` → `explanation` → `escalation` | `feature_engineering`, `ml_anomaly`, `structuring_rule`, `eda` |
| **`"Is customer ID 4521 suspicious?"`** | `entity_lookup` → `risk_classifier` → `explanation` → `escalation` | `data_loader`, `eda`, `ml_anomaly`, `aggregation_rule` |

---

## 🧪 Testing & Verification

Run the full automated test suite:

```bash
pytest tests/ -v
```

Run the offline IBM AML Kaggle benchmark backtest:

```bash
python scripts/backtest_ibm_dataset.py
```

---

## ⚠️ System Capabilities & Limitations (Model Card)

### What This System DOES Do
- Dynamically routes natural language financial queries to specific analytical tools.
- Detects structuring/smurfing deposits, layering transfer chains, and statistical volume spikes.
- Provides factual, non-hallucinated explanations verified against evidence transaction IDs.
- Audits segment-level flag rates to detect demographic/country bias.

### What This System DOES NOT Do
- It does NOT replace human compliance analysts or make automated legal filings without review.
- It does NOT perform real-time streaming event processing across high-frequency banking feeds (optimized for batch lookups and query scans).
- The LLM is NEVER used to invent risk scores, amounts, or transaction counts — all numerical calculations are strictly computed deterministically.