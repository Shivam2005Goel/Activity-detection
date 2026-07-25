import pandas as pd
from typing import List, Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from schemas import AgentResponse, ExecutionSummary, FlaggedItem, Intent, Filters
from agents.query_understanding import parse_intent
from agents.planner import build_plan
from agents.verifier import verify
from tools.tool_registry import TOOL_REGISTRY
from safety.audit_logger import log_event
from safety.bias_checker import check_flag_rate_by_segment


def run_agent(user_query: str) -> AgentResponse:
    """
    Main Orchestrator Agent: Parses natural language query, dynamically plans tool execution path,
    executes selected tools in sequence, aggregates consensus verdicts, runs verification,
    and returns a structured AgentResponse.
    """
    log_event("QUERY_RECEIVED", {"query": user_query})

    # Step 1: Parse Query Intent
    intent: Intent = parse_intent(user_query)

    # Step 2: Build Dynamic Execution Plan
    planned_tools, skipped_tools = build_plan(intent)

    # Enforce MAX_PLANNER_STEPS safety threshold
    if len(planned_tools) > config.MAX_PLANNER_STEPS:
        planned_tools = planned_tools[:config.MAX_PLANNER_STEPS]

    # Shared Context / State during execution
    state: Dict[str, Any] = {
        "df": None,
        "df_features": None,
        "eda_results": None,
        "aggregation_df": None,
        "rule_results": [],
        "ml_results": [],
        "entity_result": None,
        "consensus_map": {},
        "flagged_items": [],
        "charts": []
    }

    agents_used = ["Query Understanding Agent", "Planner Agent", "Orchestrator Agent"]

    # Step 3: Execute Planned Tools in Sequence
    for tool_name in planned_tools:
        if tool_name not in TOOL_REGISTRY:
            continue
            
        tool_entry = TOOL_REGISTRY[tool_name]
        tool_func = tool_entry["func"]

        log_event("TOOL_EXECUTION_START", {"tool_name": tool_name})

        if tool_name == "data_loader":
            state["df"] = tool_func(filters=intent.filters)

        elif tool_name == "eda":
            if state["df"] is not None and not state["df"].empty:
                state["eda_results"] = tool_func(state["df"])
                state["charts"].extend(state["eda_results"].get("charts", []))

        elif tool_name == "feature_engineering":
            if state["df"] is not None and not state["df"].empty:
                state["df_features"] = tool_func(state["df"])

        elif tool_name == "aggregation_rule":
            if state["df"] is not None and not state["df"].empty:
                state["aggregation_df"] = tool_func(df=state["df"], filters=intent.filters)

        elif tool_name == "structuring_rule":
            df_for_rule = state["df_features"] if state["df_features"] is not None else state["df"]
            if df_for_rule is not None and not df_for_rule.empty:
                rule_hits = tool_func(df_for_rule)
                state["rule_results"].extend(rule_hits)

        elif tool_name == "graph_layering":
            if state["df"] is not None and not state["df"].empty:
                layering_hits = tool_func(state["df"])
                state["rule_results"].extend(layering_hits)

        elif tool_name == "ml_anomaly":
            df_for_ml = state["df_features"] if state["df_features"] is not None else state["df"]
            if df_for_ml is not None and not df_for_ml.empty:
                ml_hits = tool_func(df_for_ml)
                state["ml_results"].extend(ml_hits)

        elif tool_name == "entity_lookup":
            # Direct data load if entity lookup skipped data_loader
            if state["df"] is None:
                from tools.data_loader import load_filtered_data
                state["df"] = load_filtered_data(filters=None)
            
            target_id = intent.entity_id if intent.entity_id else "CUST4521"
            state["entity_result"] = tool_func(customer_id=target_id, df=state["df"])

        elif tool_name == "consensus":
            state["consensus_map"] = tool_func(
                rule_results=state["rule_results"],
                ml_results=state["ml_results"]
            )

        elif tool_name == "risk_classifier":
            from tools.risk_classifier import classify_risk
            from tools.explanation import generate_explanation
            from tools.escalation import recommend_action

            flagged_list = []

            # Case A: Entity Lookup mode
            if state["entity_result"]:
                ent = state["entity_result"]
                cust_id = ent["customer_id"]
                if ent.get("found"):
                    score = ent.get("entity_score", 45.0)
                    
                    # Mock item consensus dict for classifier
                    item_cons = {
                        "combined_score": score,
                        "pattern_matched": ent.get("flagged_patterns", ["entity_check"])[0] if ent.get("flagged_patterns") else "entity_check"
                    }
                    r_score, r_level = classify_risk(item_cons)
                    action = recommend_action(r_level)
                    
                    item_data = {
                        "customer_id": cust_id,
                        "pattern_matched": item_cons["pattern_matched"],
                        "risk_level": r_level,
                        "evidence_transaction_ids": ent.get("evidence_transaction_ids", []),
                        "total_amount": ent.get("total_volume", 0.0)
                    }
                    exp_text = generate_explanation(item_data, state["df"])
                    
                    flagged_list.append(FlaggedItem(
                        customer_id=cust_id,
                        risk_score=r_score,
                        risk_level=r_level,
                        confidence=90.0,
                        trust_score=85.0,
                        pattern_matched=item_cons["pattern_matched"],
                        explanation=exp_text,
                        evidence_transaction_ids=ent.get("evidence_transaction_ids", [])[:5],
                        recommended_action=action,
                        consensus={"mode": "entity_lookup", "found": True}
                    ))
                else:
                    flagged_list.append(FlaggedItem(
                        customer_id=cust_id,
                        risk_score=0.0,
                        risk_level="Low",
                        confidence=100.0,
                        trust_score=100.0,
                        pattern_matched="entity_not_found",
                        explanation=f"Customer ID {cust_id} was not found in the transaction dataset.",
                        evidence_transaction_ids=[],
                        recommended_action="monitor",
                        consensus={"mode": "entity_lookup", "found": False}
                    ))

            # Case B: Aggregation Query mode
            elif state["aggregation_df"] is not None and not state["aggregation_df"].empty:
                for _, row in state["aggregation_df"].head(10).iterrows():
                    cust_id = str(row["customer_id"])
                    cnt = int(row["transaction_count"])
                    total_amt = float(row["total_amount"])
                    ev_ids = row.get("evidence_transaction_ids", [])
                    
                    r_score = min(95.0, 40.0 + (cnt * 4.0))
                    item_cons = {"combined_score": r_score, "pattern_matched": "high_transaction_frequency"}
                    r_score, r_level = classify_risk(item_cons)
                    action = recommend_action(r_level)
                    
                    item_data = {
                        "customer_id": cust_id,
                        "pattern_matched": "high_transaction_frequency",
                        "risk_level": r_level,
                        "txn_count": cnt,
                        "total_amount": total_amt,
                        "evidence_transaction_ids": ev_ids
                    }
                    exp_text = generate_explanation(item_data, state["df"])
                    
                    flagged_list.append(FlaggedItem(
                        customer_id=cust_id,
                        risk_score=r_score,
                        risk_level=r_level,
                        confidence=85.0,
                        trust_score=90.0,
                        pattern_matched="aggregation_threshold_hit",
                        explanation=exp_text,
                        evidence_transaction_ids=ev_ids[:5],
                        recommended_action=action,
                        consensus={"mode": "aggregation_rule", "transaction_count": cnt}
                    ))

            # Case C: Consensus Engine mode (Rules + ML)
            elif state["consensus_map"]:
                for cust_id, cons in state["consensus_map"].items():
                    if cons.get("verdict") != "Normal" or cons.get("combined_score", 0) > 30.0:
                        r_score, r_level = classify_risk(cons)
                        action = recommend_action(r_level)
                        
                        item_data = {
                            "customer_id": cust_id,
                            "pattern_matched": cons.get("pattern_matched", "suspicious_activity"),
                            "risk_level": r_level,
                            "evidence_transaction_ids": cons.get("evidence_txn_ids", []),
                            "total_amount": cons.get("rule_details", {}).get("total_amount", 0.0) if cons.get("rule_details") else 0.0
                        }
                        exp_text = generate_explanation(item_data, state["df"])
                        
                        flagged_list.append(FlaggedItem(
                            customer_id=cust_id,
                            risk_score=r_score,
                            risk_level=r_level,
                            confidence=round(min(100.0, cons.get("trust_score", 80.0) + 5.0), 1),
                            trust_score=cons.get("trust_score", 80.0),
                            pattern_matched=cons.get("pattern_matched"),
                            explanation=exp_text,
                            evidence_transaction_ids=cons.get("evidence_txn_ids", [])[:5],
                            recommended_action=action,
                            consensus=cons
                        ))

            state["flagged_items"] = flagged_list

        elif tool_name == "charts":
            from tools.charts import generate_charts
            state["charts"].extend(generate_charts(state["df"], state["flagged_items"]))

        log_event("TOOL_EXECUTION_END", {"tool_name": tool_name})

    # Step 4: Bias Checker Audit
    bias_warning = check_flag_rate_by_segment(state["flagged_items"], state["df"])

    # Step 5: Construct Draft Agent Response
    summary = ExecutionSummary(
        agents_used=agents_used + ["Verifier Agent"],
        tools_used=planned_tools,
        tools_skipped=skipped_tools,
        planning_type="dynamic_rule_based",
        verification_status="Passed",
        bias_warning=bias_warning
    )

    draft_response = AgentResponse(
        query=user_query,
        detected_intent=intent,
        results=state["flagged_items"],
        execution_summary=summary,
        charts=state["charts"]
    )

    # Step 6: Verifier Agent Pass
    _, final_response = verify(draft_response, state["df"])

    log_event("AGENT_RESPONSE_GENERATED", {
        "query": user_query,
        "flagged_count": len(final_response.results),
        "verification_status": final_response.execution_summary.verification_status
    })

    return final_response
