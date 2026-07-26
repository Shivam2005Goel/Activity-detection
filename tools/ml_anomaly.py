import pandas as pd
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from safety.fallback_handler import safe_tool_call


@safe_tool_call("ml_anomaly")
def run_ml_detection(df_features: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Fits an unsupervised Isolation Forest anomaly detector on per-customer aggregated features.
    Returns normalized anomaly scores (0 to 1) and top contributing features per flagged customer.
    """
    if df_features is None or df_features.empty:
        return []

    df_copy = df_features.copy()

    # Aggregate features per customer
    numeric_cols = [
        "amount",
        "rolling_7d_count",
        "rolling_30d_sum",
        "amount_zscore_vs_customer_avg",
        "velocity_hours_since_last_txn"
    ]
    
    # Ensure numeric cols exist
    for col in numeric_cols:
        if col not in df_copy.columns:
            df_copy[col] = 0.0

    cust_summary = df_copy.groupby("customer_id").agg({
        "amount": ["mean", "max", "sum"],
        "rolling_7d_count": "max",
        "rolling_30d_sum": "max",
        "amount_zscore_vs_customer_avg": "max",
        "velocity_hours_since_last_txn": "min",
        "transaction_id": lambda x: list(x)
    }).reset_index()

    # Flatten column names
    cust_summary.columns = [
        "customer_id",
        "amount_mean", "amount_max", "amount_sum",
        "max_rolling_7d_count", "max_rolling_30d_sum",
        "max_zscore", "min_velocity_hours",
        "evidence_txn_ids"
    ]

    feature_matrix = cust_summary[[
        "amount_mean", "amount_max", "amount_sum",
        "max_rolling_7d_count", "max_rolling_30d_sum",
        "max_zscore", "min_velocity_hours"
    ]].fillna(0.0)

    if len(feature_matrix) < 5:
        # Not enough samples for meaningful ML anomaly fit
        return []

    # Use PyOD IForest if available, else sklearn IsolationForest
    scores = []
    try:
        from pyod.models.iforest import IForest
        clf = IForest(contamination=config.ML_CONTAMINATION, random_state=42)
        clf.fit(feature_matrix.values)
        raw_scores = clf.decision_scores_  # Outlier scores (higher = more anomalous)
        # MinMax scale raw scores to 0-1
        s_min, s_max = raw_scores.min(), raw_scores.max()
        if s_max > s_min:
            scores = (raw_scores - s_min) / (s_max - s_min)
        else:
            scores = np.zeros_like(raw_scores)
    except Exception as e:
        from sklearn.ensemble import IsolationForest
        clf = IsolationForest(contamination=config.ML_CONTAMINATION, random_state=42)
        clf.fit(feature_matrix.values)
        raw_scores = -clf.score_samples(feature_matrix.values)  # Convert logic so higher = more anomalous
        s_min, s_max = raw_scores.min(), raw_scores.max()
        if s_max > s_min:
            scores = (raw_scores - s_min) / (s_max - s_min)
        else:
            scores = np.zeros_like(raw_scores)

    # Calculate SHAP values for explainability
    shap_values_dict = {}
    try:
        import shap
        # IsolationForest (either sklearn or PyOD wrapper) works with TreeExplainer
        # PyOD IForest often exposes .detector_ or .estimators_
        explainer = shap.TreeExplainer(clf)
        shap_vals = explainer.shap_values(feature_matrix.values)
        
        for idx in range(len(feature_matrix)):
            # Pair feature names with their absolute SHAP contribution
            feat_shap = dict(zip(feature_matrix.columns, np.abs(shap_vals[idx])))
            shap_values_dict[idx] = feat_shap
    except Exception as e:
        print(f"[SHAP] Explainability calculation failed: {str(e)}")

    results = []
    for idx, row in cust_summary.iterrows():
        norm_score = float(scores[idx])
        if norm_score >= config.ML_ANOMALY_SCORE_THRESHOLD:
            top_feats = []
            if row["max_zscore"] > 3.0:
                top_feats.append("high_amount_zscore")
            if row["max_rolling_7d_count"] > 10:
                top_feats.append("high_transaction_velocity")
            if row["amount_max"] > 50000:
                top_feats.append("extreme_transaction_amount")
            if not top_feats:
                top_feats.append("multivariate_statistical_outlier")

            # Add SHAP if computed
            shap_info = shap_values_dict.get(idx, {})

            results.append({
                "customer_id": row["customer_id"],
                "ml_score": round(norm_score, 3),
                "anomaly_flag": True,
                "top_features": top_feats,
                "shap_values": shap_info,
                "evidence_txn_ids": row["evidence_txn_ids"][:5]  # limit to top 5 evidence IDs
            })

    return results
