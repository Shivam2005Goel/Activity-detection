import httpx
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from schemas import Intent
from safety.fallback_handler import retry_llm_call
from safety.audit_logger import log_event


def _fallback_synthesizer(user_query: str, intent: Intent, state: dict) -> str:
    """
    Deterministic rule-based fallback when LLM fails or is not configured.
    """
    if intent.intent_type == "aggregation_query" and state.get("aggregation_df") is not None:
        total_customers = len(state["aggregation_df"])
        total_transactions = len(state["df"]) if state.get("df") is not None else 0
        tx_type = intent.filters.transaction_type if intent.filters.transaction_type else "relevant"
        return f"Found a total of {total_transactions} {tx_type} transactions across {total_customers} unique customers based on your query."
    
    return f"Processed query: {user_query}. Identified {len(state.get('flagged_items', []))} high-risk entities."


@retry_llm_call(max_retries=config.LLM_MAX_RETRIES, delay_seconds=1.0)
def _call_openrouter_synthesizer(user_query: str, context_str: str) -> str:
    """
    Calls OpenRouter LLM to generate a natural language summary.
    """
    if not config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set.")

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"You are a helpful Data Synthesizer Agent for an Anti-Money Laundering (AML) system.\n"
        f"A user asked the following query: '{user_query}'\n\n"
        f"The backend system processed this and returned the following data metrics:\n"
        f"{context_str}\n\n"
        f"Write a single, clear, conversational sentence that directly answers the user's query using the provided data metrics. "
        f"Do not add extra conversational fluff. Do not format as a list."
    )

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }

    response = httpx.post(
        f"{config.OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=config.LLM_TIMEOUT_SECONDS
    )

    if response.status_code == 200:
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    else:
        raise RuntimeError(f"OpenRouter status {response.status_code}: {response.text}")


def synthesize_response(user_query: str, intent: Intent, state: dict) -> str:
    """
    Main Synthesizer Agent entrypoint.
    """
    context_parts = []
    
    if state.get("df") is not None:
        context_parts.append(f"Total Transactions Found: {len(state['df'])}")
    if state.get("aggregation_df") is not None:
        context_parts.append(f"Total Unique Customers Involved: {len(state['aggregation_df'])}")
    if state.get("flagged_items"):
        context_parts.append(f"Total High-Risk Suspicious Entities Flagged: {len(state['flagged_items'])}")
        
    context_str = "\n".join(context_parts)
    
    summary_text = None
    if config.OPENROUTER_API_KEY:
        try:
            summary_text = _call_openrouter_synthesizer(user_query, context_str)
            log_event("SYNTHESIZER_LLM_SUCCESS", {"query": user_query, "summary": summary_text})
        except Exception as e:
            print(f"[SYNTHESIZER FALLBACK] OpenRouter LLM call failed ({str(e)}).")
    
    if summary_text is None:
        summary_text = _fallback_synthesizer(user_query, intent, state)
        log_event("SYNTHESIZER_REGEX_FALLBACK", {"query": user_query, "summary": summary_text})
        
    return summary_text
