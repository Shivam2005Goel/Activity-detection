import pandas as pd
import networkx as nx
from typing import List, Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from safety.fallback_handler import safe_tool_call


@safe_tool_call("graph_layering")
def detect_layering(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Detects money laundering layering patterns: directed fund transfers through chains
    of 3+ intermediate accounts within short time windows.
    """
    if df is None or df.empty:
        return []

    # Filter to transfers with valid counterparty_id
    transfers = df[
        (df["transaction_type"].str.lower() == "transfer") &
        (df["counterparty_id"].notnull())
    ].copy()

    if transfers.empty:
        return []

    # Map account_id -> customer_id
    acc_to_cust = {}
    for _, row in df.iterrows():
        acc_to_cust[row["account_id"]] = row["customer_id"]

    G = nx.DiGraph()

    # Build directed multigraph edges
    for _, row in transfers.iterrows():
        sender_acc = row["account_id"]
        receiver_acc = row["counterparty_id"]
        sender_cust = acc_to_cust.get(sender_acc, sender_acc)
        receiver_cust = acc_to_cust.get(receiver_acc, receiver_acc)

        if sender_cust != receiver_cust:
            G.add_edge(sender_cust, receiver_cust, txn_id=row["transaction_id"], amount=row["amount"])

    flagged_layering = []
    seen_customers = set()

    # Detect simple paths of length >= 3
    nodes = list(G.nodes())
    for source in nodes:
        if source in seen_customers:
            continue
        for target in nodes:
            if source != target and nx.has_path(G, source, target):
                try:
                    for path in nx.all_simple_paths(G, source=source, target=target, cutoff=4):
                        if len(path) >= 3:
                            # Path found: source -> hop1 -> hop2 ...
                            evidence_txn_ids = []
                            for i in range(len(path) - 1):
                                edge_data = G.get_edge_data(path[i], path[i+1])
                                if edge_data and "txn_id" in edge_data:
                                    evidence_txn_ids.append(edge_data["txn_id"])

                            originator = path[0]
                            if originator not in seen_customers:
                                seen_customers.add(originator)
                                flagged_layering.append({
                                    "customer_id": originator,
                                    "rule_fired": "layering",
                                    "supporting_txn_ids": evidence_txn_ids,
                                    "rule_score": 85.0,
                                    "chain": path
                                })
                except Exception:
                    continue

    return flagged_layering
