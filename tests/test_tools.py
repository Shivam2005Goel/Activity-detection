import pytest
import pandas as pd
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.generate_sample_data import generate_synthetic_transactions
from tools.data_loader import load_filtered_data
from tools.feature_engineering import compute_features
from tools.structuring_rule import detect_structuring
from tools.ml_anomaly import run_ml_detection
from tools.consensus import compute_consensus
from tools.entity_lookup import lookup_entity
from schemas import Filters


@pytest.fixture(scope="module")
def sample_df():
    return generate_synthetic_transactions()


def test_data_loader(sample_df):
    filters = Filters(min_transaction_count=5, amount_threshold=10000.0)
    df = load_filtered_data(filters=filters)
    assert not df.empty
    assert (df["amount"] < 10000.0).all()


def test_feature_engineering(sample_df):
    df_feats = compute_features(sample_df)
    assert "rolling_7d_count" in df_feats.columns
    assert "rolling_30d_sum" in df_feats.columns
    assert "amount_zscore_vs_customer_avg" in df_feats.columns
    assert "is_just_under_threshold" in df_feats.columns


def test_structuring_rule(sample_df):
    df_feats = compute_features(sample_df)
    results = detect_structuring(df_feats)
    assert len(results) >= 1
    first = results[0]
    assert "customer_id" in first
    assert first["rule_fired"] == "structuring"
    assert len(first["supporting_txn_ids"]) >= 5


def test_ml_anomaly(sample_df):
    df_feats = compute_features(sample_df)
    results = run_ml_detection(df_feats)
    assert isinstance(results, list)


def test_consensus_engine():
    rule_results = [{"customer_id": "CUST4521", "rule_fired": "structuring", "supporting_txn_ids": ["TXN01"], "rule_score": 85.0}]
    ml_results = [{"customer_id": "CUST4521", "ml_score": 0.8, "anomaly_flag": True, "evidence_txn_ids": ["TXN01"]}]
    
    consensus = compute_consensus(rule_results, ml_results)
    assert "CUST4521" in consensus
    assert consensus["CUST4521"]["agreement"] == "Full agreement"
    assert consensus["CUST4521"]["trust_score"] >= 90.0


def test_entity_lookup(sample_df):
    res = lookup_entity("CUST4521", sample_df)
    assert res["found"] is True
    assert res["customer_id"] == "CUST4521"
    assert res["transactions_count"] > 0
