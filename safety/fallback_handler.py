import functools
import time
import pandas as pd
import traceback
from typing import Callable, Any, Dict
from safety.audit_logger import log_event


def safe_tool_call(tool_name: str):
    """
    Decorator wrapping tool calls with error catching, logging, and graceful fallbacks.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                err_msg = str(e)
                tb = traceback.format_exc()
                print(f"[TOOL ERROR] {tool_name} failed: {err_msg}")
                
                log_event("TOOL_ERROR", {
                    "tool_name": tool_name,
                    "error": err_msg,
                    "traceback": tb
                })
                
                # Determine default safe return type based on tool name or expected return
                if tool_name in ["data_loader", "eda", "feature_engineering", "aggregation_rule"]:
                    return pd.DataFrame()
                elif tool_name in ["structuring_rule", "ml_anomaly", "graph_layering"]:
                    return []
                elif tool_name == "entity_lookup":
                    return {"customer_id": kwargs.get("customer_id", "unknown"), "error": err_msg, "transactions": []}
                elif tool_name == "consensus":
                    return {"agreement": "Error", "trust_score": 0.0, "details": err_msg}
                elif tool_name == "risk_classifier":
                    return 0.0, "Low"
                elif tool_name == "explanation":
                    return f"Analysis unavailable due to internal tool error: {err_msg}"
                elif tool_name == "escalation":
                    return "review"
                elif tool_name == "charts":
                    return []
                else:
                    return None
        return wrapper
    return decorator


def retry_llm_call(max_retries: int = 2, delay_seconds: float = 1.0):
    """
    Decorator for retrying LLM API calls on transient network/rate limit errors.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1 + max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay_seconds * (2 ** attempt))
                    else:
                        print(f"[LLM RETRY EXHAUSTED] {func.__name__} failed after {max_retries} retries: {str(e)}")
                        raise last_exception
        return wrapper
    return decorator
