from typing import Dict, Any, Callable
from tools.data_loader import load_filtered_data
from tools.eda import run_eda
from tools.feature_engineering import compute_features
from tools.aggregation_rule import run_aggregation
from tools.structuring_rule import detect_structuring
from tools.graph_layering import detect_layering
from tools.ml_anomaly import run_ml_detection
from tools.entity_lookup import lookup_entity
from tools.consensus import compute_consensus
from tools.risk_classifier import classify_risk
from tools.explanation import generate_explanation
from tools.escalation import recommend_action
from tools.charts import generate_charts

TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "data_loader": {
        "name": "data_loader",
        "func": load_filtered_data,
        "description": "Loads and filters transaction data from storage via DuckDB.",
        "required_columns": []
    },
    "eda": {
        "name": "eda",
        "func": run_eda,
        "description": "Exploratory Data Analysis: summary statistics and dataset distributions.",
        "required_columns": ["amount", "transaction_type", "customer_id"]
    },
    "feature_engineering": {
        "name": "feature_engineering",
        "func": compute_features,
        "description": "Computes rolling counts, velocity, z-scores, and threshold flags.",
        "required_columns": ["customer_id", "timestamp", "amount"]
    },
    "aggregation_rule": {
        "name": "aggregation_rule",
        "func": run_aggregation,
        "description": "Simple aggregation tool for customer counts and amount thresholds.",
        "required_columns": ["customer_id", "amount", "transaction_id"]
    },
    "structuring_rule": {
        "name": "structuring_rule",
        "func": detect_structuring,
        "description": "Rule tool for detecting structuring and smurfing cash deposits.",
        "required_columns": ["is_just_under_threshold", "customer_id", "timestamp"]
    },
    "graph_layering": {
        "name": "graph_layering",
        "func": detect_layering,
        "description": "Graph analyzer tool for money layering chains using NetworkX.",
        "required_columns": ["counterparty_id", "transaction_type", "account_id"]
    },
    "ml_anomaly": {
        "name": "ml_anomaly",
        "func": run_ml_detection,
        "description": "Unsupervised PyOD IsolationForest anomaly detection tool.",
        "required_columns": ["amount", "rolling_7d_count", "rolling_30d_sum"]
    },
    "entity_lookup": {
        "name": "entity_lookup",
        "func": lookup_entity,
        "description": "Entity lookup tool for specific customer history and pattern check.",
        "required_columns": ["customer_id", "amount", "timestamp"]
    },
    "consensus": {
        "name": "consensus",
        "func": compute_consensus,
        "description": "Consensus Engine combining rule violations and ML anomaly scores.",
        "required_columns": []
    },
    "risk_classifier": {
        "name": "risk_classifier",
        "func": classify_risk,
        "description": "Classifies numerical risk score into Low, Medium, High, Critical.",
        "required_columns": []
    },
    "explanation": {
        "name": "explanation",
        "func": generate_explanation,
        "description": "Generates factual 1-2 sentence evidence explanation via OpenRouter LLM/template.",
        "required_columns": []
    },
    "escalation": {
        "name": "escalation",
        "func": recommend_action,
        "description": "Recommends action (monitor, review, report) based on risk level.",
        "required_columns": []
    },
    "charts": {
        "name": "charts",
        "func": generate_charts,
        "description": "Generates Plotly interactive figures for UI visualization.",
        "required_columns": []
    }
}


def get_all_registered_tools() -> list[str]:
    """Returns list of all registered tool names."""
    return list(TOOL_REGISTRY.keys())
