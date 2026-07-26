# Agentic AI Suspicious Activity Detection System (Agentic AML)

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.25+-red.svg)](https://streamlit.io/)
[![DuckDB](https://img.shields.io/badge/DuckDB-0.9+-yellow.svg)](https://duckdb.org/)

An advanced **Agentic AI system** designed to detect money laundering patterns in financial transaction data. Built for the **Societe Generale AML Hackathon**.

The core system architecture **does NOT run a fixed sequential pipeline**. Instead, it parses natural language queries, extracts structured intent, and **dynamically constructs an execution plan** — calling only the required tools, executing ML models on the fly, generating dynamic visual charts, and skipping irrelevant steps.

---

## 🎯 Problem Statement

Traditional Anti-Money Laundering (AML) systems suffer from rigid rule-based constraints, resulting in high false-positive rates and alert fatigue for compliance analysts. When investigators explore data, they rely on complex SQL queries and static dashboards, making ad-hoc investigations slow and difficult. Furthermore, black-box Machine Learning models often lack the transparency and explainability required by regulatory standards.

## 💡 Proposed Solution

We propose a **Dynamic Multi-Agent System** that acts as an intelligent co-pilot for AML investigators. Our solution allows users to simply ask natural language questions (e.g., *"Find structuring patterns in the last 30 days"* or *"Show me a scatter plot of transaction amounts"*). 

An intelligent orchestrator interprets the intent, dynamically plans the sequence of required tools (skipping unnecessary ones), fetches the data, applies both deterministic rules and unsupervised ML, and returns a verified, explainable response alongside dynamically generated charts and extracted evidence data. 

---

## 🏗️ Architecture Overview

```mermaid
graph TD
    %% Custom Styles
    classDef userNode fill:#8B5CF6,stroke:#4C1D95,stroke-width:3px,color:#fff,font-weight:bold,rx:10,ry:10
    classDef ui fill:#3B82F6,stroke:#1E3A8A,stroke-width:3px,color:#fff,font-weight:bold,rx:10,ry:10
    classDef core fill:#10B981,stroke:#064E3B,stroke-width:3px,color:#fff,font-weight:bold,rx:10,ry:10
    classDef agent fill:#F59E0B,stroke:#78350F,stroke-width:3px,color:#fff,font-weight:bold,rx:10,ry:10
    classDef tool fill:#6366F1,stroke:#312E81,stroke-width:2px,color:#fff,rx:5,ry:5
    classDef db fill:#EC4899,stroke:#831843,stroke-width:2px,color:#fff,rx:5,ry:5
    classDef critic fill:#EF4444,stroke:#7F1D1D,stroke-width:3px,color:#fff,font-weight:bold,rx:10,ry:10

    User([User / Investigator]):::userNode -->|Natural Language Query| UI[Streamlit Dashboard]:::ui
    UI -->|POST /agent/query| API[FastAPI Backend]:::core
    
    subgraph Agentic Orchestrator
        API --> QU[Query Understanding Agent]:::agent
        QU -->|Extracts Intent & Filters| Planner[Dynamic Orchestrator]:::agent
        Planner -->|Builds Execution Graph| Tools{Tool Dispatcher}:::core
    end
    
    subgraph Data & Analytics Tools
        Tools --> DL[(Data Loader)]:::db
        DL --> FE[Feature Engineering]:::tool
        FE --> EDA[Dynamic Charting]:::tool
        
        FE --> ML[PyOD Anomaly Detection]:::tool
        FE --> SR[Structuring Rules]:::tool
        FE --> GL[NetworkX Graph Layering]:::tool
        
        ML --> CE{Consensus Engine}:::core
        SR --> CE
        GL --> CE
        
        CE --> RC[Risk Classifier]:::tool
        RC --> EX[Explainability Agent]:::agent
        EX --> Esc[Escalation Recommender]:::tool
    end
    
    Esc --> Verifier[Verifier / Critic Agent]:::critic
    Verifier -->|Validates Facts| API
    API -->|Returns Verified JSON| UI
```

Our architecture follows a strictly planned Agentic Execution flow decoupled into several micro-services and agents:

1. **Frontend (Streamlit)**: A modern, real-time dashboard displaying execution paths, generated charts, extracted data grids, and live audit logs.
2. **Backend Engine (FastAPI)**: A stateless orchestration engine serving as the brain of the agent.
3. **Intent Parsing Agent**: Leverages OpenRouter LLMs (or offline regex fallbacks) to understand user queries, extracting filters, entities, and execution flags.
4. **Dynamic Orchestrator**: The core controller that builds an execution graph based on the intent. It injects shared state between isolated tools and enforces strict data bounds.
5. **Consensus Engine**: Aggregates signals from rules and ML to form a unified risk score.
6. **Verifier / Critic Agent**: Acts as an internal auditor, verifying that the generated explanation aligns strictly with the factual data (e.g., checking if transaction counts and sums are mathematically correct).

---

## ⚙️ Agents and Tools Breakdown

### Core Agents
- **Query Understanding Agent (`query_understanding.py`)**: Converts natural language into a structured `Intent` schema. Identifies whether the query is an entity lookup, a broad exploration, an aggregation query, or a charting request.
- **Orchestrator Agent (`orchestrator.py`)**: The central nervous system. Decides which tools to run and which to skip based on the intent.
- **Verifier Agent (`verifier.py`)**: Before showing the final response to the human analyst, this critic agent validates the response against the factual evidence. If the LLM hallucinates an amount, the verifier blocks it.

### Tool Suite
- **`data_loader`**: Fetches raw transaction data into a pandas DataFrame based on the queried date ranges or entity IDs.
- **`feature_engineering`**: Enriches the raw dataset with rolling windows, velocity metrics, and temporal features (e.g., `daily_txn_count`, `avg_amount_7d`).
- **`eda` (Exploratory Data Analysis)**: Generates dataset statistics, missing value reports, and general metadata.
- **`structuring_rule`**: Deterministically flags transactions that look like "structuring" or "smurfing" (e.g., multiple rapid transactions just under the $10k reporting threshold).
- **`aggregation_rule`**: Flags anomalies based on aggregated volume (e.g., users exceeding 10+ transactions in a day).
- **`graph_layering`**: Uses NetworkX to build a directed graph of transactions, identifying cyclical layering behavior or complex money movement chains.
- **`ml_anomaly`**: Runs an unsupervised `IsolationForest` (via PyOD) to detect statistically anomalous multivariate patterns without needing labels.
- **`consensus`**: A weighting engine that takes votes from `structuring_rule`, `graph_layering`, and `ml_anomaly` to output a final `risk_score` and `agreement_verdict`.
- **`risk_classifier`**: Categorizes the numeric risk score into `Low`, `Medium`, `High`, or `Critical` tiers.
- **`charts`**: Automatically writes and executes safe Python plotting code using Plotly to generate dynamic visualizations based on user requests.
- **`explanation`**: Generates a natural language summary explaining *why* a customer was flagged, referencing specific transaction IDs.
- **`escalation`**: Recommends next steps for compliance teams (e.g., *File SAR*, *Monitor*, *Review*).

---

## 🤖 Agentic Features & Human-in-the-Loop

Unlike traditional fixed pipelines, this system leverages true **Agentic capabilities**:
- **Dynamic Routing**: The orchestrator acts as a router, selectively triggering data-heavy ML anomaly detection only when necessary, saving compute costs and time.
- **Self-Correction & Fallbacks**: If the primary LLM fails to parse intent or generate a chart, the system automatically falls back to offline, deterministic regex logic and pre-built visualizations, ensuring 100% uptime.
- **Human-in-the-Loop (HITL)**: This agent acts as a *co-pilot*, not an autopilot.
  - Generates Suspicious Activity Reports (SARs) as *drafts* for human review (in the `sars/` directory).
  - Provides strict evidence (exact Transaction IDs) allowing investigators to manually cross-reference the data grid.
  - The final escalation verdict (e.g., "File SAR", "Monitor") is a recommendation, leaving the ultimate regulatory decision to the compliance officer.

---

## 🔒 Security & Data Privacy

Handling financial data requires strict security constraints. Our agent is designed with safety as a first-class citizen:
- **No Data Exfiltration**: Raw transaction data (account balances, user PII, transaction IDs) is **never** sent to the LLM. The LLM only receives aggregated schema metadata (e.g., `["amount", "date"]`) to write charting logic, or high-level risk scores to draft summaries.
- **Code Execution Sandbox**: The charting agent generates Python code (`Plotly`) dynamically. However, this code is executed in a highly restricted `local_scope`, preventing it from accessing the OS, making network requests, or reading unauthorized files.
- **Verifier Fact-Checking**: LLMs are prone to hallucinating numbers. The `Verifier Agent` intercepts the LLM's natural language output and mathematically cross-checks it against the local Pandas dataframe. If the LLM claims "5 transactions" but the database says "4", the Verifier overwrites the hallucination with facts.
- **Immutable Audit Logging**: Every query, intent parsed, tool called, and ML score generated is appended to a local `audit_log.jsonl` to satisfy regulatory audit requirements.

---

## 🚀 Installation & Quick Start

Follow these steps to run the system locally on your machine.

### 1. Prerequisites
- **Python 3.11+** installed on your system.
- Git.

### 2. Clone the Repository
```bash
git clone https://github.com/Shivam2005Goel/Activity-detection.git
cd Activity-detection
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Generate the Synthetic Transaction Dataset
Before running the app, generate the initial mock database:
```bash
python scripts/generate_sample_data.py
```
*(This will create a dummy dataset simulating retail banking transactions).*

### 5. Configure API Keys (Optional but Recommended)
For dynamic Intent Parsing, Explanations, and Charting, the system uses OpenRouter LLMs.
```bash
# On Windows (Command Prompt)
set OPENROUTER_API_KEY=your_openrouter_api_key_here

# On Linux / macOS
export OPENROUTER_API_KEY=your_openrouter_api_key_here
```
*(Note: If no key is set, the system seamlessly uses an offline regex parser and template explainability engine, though dynamic charting will be disabled).*

### 6. Run the FastAPI Backend Service
In your first terminal window, launch the backend:
```bash
python api/main.py
# or
uvicorn api.main:app --port 8000 --reload
```

### 7. Launch the Streamlit Dashboard
In a second terminal window, launch the frontend:
```bash
streamlit run dashboard/app.py
```
The application will open automatically in your browser at `http://localhost:8501`.

---

## 💡 Example Queries to Try

Once the app is running, try asking the agent:

- **`"Show me a scatter plot of transaction amounts vs time"`**  
  *Triggers the dynamic charting tool to render a custom Plotly scatter plot.*
- **`"Find structuring patterns in the last 30 days"`**  
  *Triggers the structuring rules and flags accounts operating just under reporting thresholds.*
- **`"Which customers made 10+ transactions under $10,000?"`**  
  *Triggers the aggregation tools to isolate high-velocity retail actors.*
- **`"Is customer ID CUST1237 suspicious?"`**  
  *Performs an isolated entity lookup, bypassing broad ML anomaly detection to save compute.*

---

## 🧪 Automated Testing & Benchmarking

To run the automated `pytest` suite:
```bash
pytest tests/ -v
```

We also support offline benchmarking using the IBM AML Kaggle dataset (requires downloading the dataset to the `data/` folder).
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
- It does **NOT** replace human compliance analysts or make automated legal filings (SARs) without human review.
- It is optimized for batch lookups and query scans, not real-time millisecond streaming execution.
- The LLM is **NEVER** used to invent risk scores, transaction amounts, or counts — all numerical calculations are strictly computed deterministically via Pandas/DuckDB.