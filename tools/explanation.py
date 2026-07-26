import json
import httpx
import functools
from typing import Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from safety.fallback_handler import safe_tool_call, retry_llm_call


@retry_llm_call(max_retries=1, delay_seconds=0.5)
def _call_openrouter_explanation(fact_sheet: Dict[str, Any]) -> str:
    """
    Invokes LLM via OpenRouter API to produce a 1-2 sentence evidence explanation.
    """
    if not config.OPENROUTER_API_KEY:
        raise ValueError("No OPENROUTER_API_KEY provided.")

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = (
        f"You are an AML Compliance Explanation Engine. Explain the flagged suspicious activity "
        f"in 1-2 concise, professional sentences using ONLY the facts provided below. "
        f"You MUST explicitly include the 'customer_id' in your explanation text. "
        f"Do NOT invent or introduce any numbers, dates, or details not present in the input.\n\n"
        f"FACT SHEET:\n{json.dumps(fact_sheet, indent=2)}"
    )

    payload = {
        "model": config.LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise financial crime explanation engine. Only state verified facts given in input."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 120
    }

    response = httpx.post(
        f"{config.OPENROUTER_BASE_URL}/chat/completions",
        headers=headers,
        json=payload,
        timeout=8.0
    )
    
    if response.status_code == 200:
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()
        return content
    else:
        raise RuntimeError(f"OpenRouter API returned status {response.status_code}: {response.text}")


_EXPLANATION_CACHE = {}

@safe_tool_call("explanation")
def generate_explanation(item_data: Dict[str, Any], source_data: Any = None) -> str:
    """
    Generates plain-English factual explanation using OpenRouter LLM or fallback template.
    """
    cust_id = item_data.get("customer_id", "Unknown")
    pattern = item_data.get("pattern_matched") or item_data.get("rule_fired") or "suspicious activity"
    risk_level = item_data.get("risk_level", "Medium")
    txn_count = item_data.get("txn_count", len(item_data.get("evidence_transaction_ids", [])))
    total_amount = item_data.get("total_amount", 0.0)

    cache_key = f"{cust_id}_{pattern}_{risk_level}_{txn_count}"
    if cache_key in _EXPLANATION_CACHE:
        return _EXPLANATION_CACHE[cache_key]

    fact_sheet = {
        "customer_id": cust_id,
        "risk_level": risk_level,
        "pattern_detected": pattern,
        "evidence_transaction_count": txn_count,
        "total_amount_usd": total_amount,
        "evidence_transaction_ids": item_data.get("evidence_transaction_ids", [])
    }

    # Attempt LLM call if API key configured (limit LLM calls to prevent timeouts)
    if config.OPENROUTER_API_KEY and len(_EXPLANATION_CACHE) < 5:
        try:
            res = _call_openrouter_explanation(fact_sheet)
            _EXPLANATION_CACHE[cache_key] = res
            return res
        except Exception as e:
            print(f"[EXPLANATION FALLBACK] LLM call failed ({str(e)}), using template generator.")

    # Robust Template Fallback
    if pattern in ["structuring", "smurfing"]:
        return (
            f"Customer {cust_id} exhibited a structuring pattern with {txn_count} transactions "
            f"totaling ${total_amount:,.2f} positioned just under the $10,000 reporting threshold within a short window."
        )
    elif pattern == "layering":
        return (
            f"Customer {cust_id} initiated a sequence of rapid inter-account transfers ({txn_count} transactions) "
            f"indicative of money layering across account chains."
        )
    elif pattern in ["statistical_anomaly", "high_amount_zscore"]:
        return (
            f"Customer {cust_id} was flagged as a statistical outlier with {txn_count} transactions "
            f"showing significant volume deviation from typical historical activity."
        )
    else:
        return (
            f"Customer {cust_id} was flagged for {pattern} with risk level {risk_level} "
            f"across {txn_count} evidence transactions."
        )
