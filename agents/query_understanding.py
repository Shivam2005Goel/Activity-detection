import re
import json
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from schemas import Intent, Filters
from safety.fallback_handler import retry_llm_call
from safety.audit_logger import log_event


def _keyword_regex_fallback_parser(user_query: str) -> Intent:
    """
    Deterministically parses query intent using regex pattern matching.
    Ensures system functions 100% offline without an LLM API key.
    """
    query_lower = user_query.lower()
    filters = Filters()
    entity_id = None
    intent_type = "broad_exploration"
    target_pattern = "none"
    requires_full_eda = False
    requires_ml_detection = False

    # 1. Customer ID / Entity Lookup pattern (must contain digits, e.g. CUST4521 or customer 4521)
    cust_match = re.search(r"(?:customer\s*(?:id)?\s*[:#]?\s*|cust\s*)([0-9]{3,6})", user_query, re.IGNORECASE)
    if cust_match:
        found_id = f"CUST{cust_match.group(1)}"
        entity_id = found_id
        intent_type = "entity_lookup"

    # 2. Date Range extraction ("last N days")
    days_match = re.search(r"last\s+(\d+)\s+days?", query_lower)
    if days_match:
        num_days = int(days_match.group(1))
        filters.date_end = datetime.now().date()
        filters.date_start = filters.date_end - timedelta(days=num_days)

    # 3. Aggregation query ("10+ transactions under $10,000")
    count_match = re.search(r"(\d+)\+?\s*transactions?", query_lower)
    amount_match = re.search(r"under\s*\$?([\d,]+)", query_lower)
    
    if count_match or amount_match:
        intent_type = "aggregation_query"
        if count_match:
            filters.min_transaction_count = int(count_match.group(1))
        if amount_match:
            amt_str = amount_match.group(1).replace(",", "")
            filters.amount_threshold = float(amt_str)

    # 4. Pattern Search (structuring / smurfing / layering)
    if "structur" in query_lower or "smurf" in query_lower:
        intent_type = "pattern_search"
        target_pattern = "structuring"
    elif "layer" in query_lower:
        intent_type = "pattern_search"
        target_pattern = "layering"
    elif "cash" in query_lower and "deposit" in query_lower:
        intent_type = "pattern_search"
        target_pattern = "structuring"

    # 5. Broad exploration / EDA flags
    aml_keywords = ["transaction", "customer", "money", "laundering", "bank", "account", "structuring", "smurfing", "layering", "deposit", "withdrawal", "transfer", "fraud", "suspicious", "check", "eda", "summary", "overview", "txns", "aml"]
    if not any(word in query_lower for word in aml_keywords) and intent_type == "broad_exploration" and not cust_match:
        intent_type = "out_of_domain"
    elif intent_type == "broad_exploration" or "eda" in query_lower or "summary" in query_lower or "overview" in query_lower:
        requires_full_eda = True
        requires_ml_detection = True

    intent = Intent(
        intent_type=intent_type,
        target_pattern=target_pattern,
        filters=filters,
        entity_id=entity_id,
        requires_full_eda=requires_full_eda,
        requires_ml_detection=requires_ml_detection,
        confidence=0.85
    )

    return intent


@retry_llm_call(max_retries=config.LLM_MAX_RETRIES, delay_seconds=1.0)
def _call_openrouter_intent(user_query: str, history: list = None) -> Intent:
    """
    Calls OpenRouter LLM for structured JSON Intent parsing.
    """
    if not config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set.")

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    schema_example = {
        "intent_type": "pattern_search | aggregation_query | entity_lookup | broad_exploration | out_of_domain",
        "target_pattern": "structuring | smurfing | layering | rapid_cashout | none",
        "filters": {
            "date_start": "YYYY-MM-DD or null",
            "date_end": "YYYY-MM-DD or null",
            "country": "string or null",
            "transaction_type": "string or null",
            "customer_segment": "string or null",
            "amount_threshold": "float or null",
            "min_transaction_count": "int or null"
        },
        "entity_id": "string or null",
        "requires_full_eda": "bool",
        "requires_ml_detection": "bool",
        "confidence": "float 0-1"
    }

    history_text = ""
    if history:
        history_text = "Previous Conversation History:\n" + "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history[-3:]]) + "\n\n"

    prompt = (
        f"{history_text}Extract intent details from this new financial query: '{user_query}'\n\n"
        f"Return ONLY valid JSON matching this schema:\n{json.dumps(schema_example, indent=2)}\n"
        f"Current date: {datetime.now().strftime('%Y-%m-%d')}"
    )

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are an intent parser for an AML system. Return raw JSON matching the requested schema exactly. Use the previous conversation history to resolve pronouns (e.g., 'they', 'them') or missing context in the current query. If the user query is entirely unrelated to finance, banking, or AML, set intent_type to 'out_of_domain'."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0
    }

    response = httpx.post(
        f"{config.OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=config.LLM_TIMEOUT_SECONDS
    )

    if response.status_code == 200:
        data = response.json()
        raw_json_str = data["choices"][0]["message"]["content"].strip()
        if raw_json_str.startswith("```"):
            raw_json_str = re.sub(r"^```(?:json)?\s*", "", raw_json_str)
            raw_json_str = re.sub(r"\s*```$", "", raw_json_str)
        json_match = re.search(r"\{.*\}", raw_json_str, re.DOTALL)
        if json_match:
            raw_json_str = json_match.group(0)
        parsed_dict = json.loads(raw_json_str)
        return Intent(**parsed_dict)
    else:
        raise RuntimeError(f"OpenRouter status {response.status_code}: {response.text}")


def parse_intent(user_query: str, history: list = None) -> Intent:
    """
    Main Query Understanding Agent entrypoint. Uses OpenRouter LLM when configured
    with automatic fallback to deterministic regex/keyword parser.
    """
    intent = None
    if config.OPENROUTER_API_KEY:
        try:
            intent = _call_openrouter_intent(user_query, history)
            log_event("QUERY_UNDERSTANDING_LLM_SUCCESS", {"query": user_query, "intent": intent.model_dump()})
        except Exception as e:
            print(f"[QUERY PARSER FALLBACK] OpenRouter LLM call failed ({str(e)}). Using keyword/regex parser.")

    if intent is None:
        # Keyword / Regex Fallback
        intent = _keyword_regex_fallback_parser(user_query)
        log_event("QUERY_UNDERSTANDING_REGEX_FALLBACK", {"query": user_query, "intent": intent.model_dump()})
        
    return intent
