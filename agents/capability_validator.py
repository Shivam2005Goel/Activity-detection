import re
from typing import Tuple
from schemas import Intent

def validate_capability(intent: Intent, user_query: str) -> Tuple[bool, str]:
    """
    Capability Validator Agent:
    Explicit architectural component that sits between Intent Detection and Planner.
    Validates if the detected intent and user query fall within the supported
    capabilities of the AML system.
    
    Returns:
        (is_supported: bool, reason_or_message: str)
    """
    
    if intent.intent_type == "out_of_domain":
        return False, "I can't help with that. Please ask questions related to AML, financial transactions, or suspicious activities."
        
    query_lower = user_query.lower()
    
    # Robust vocabulary list for supported domain queries
    aml_keywords = [
        "transaction", "customer", "money", "laundering", "bank", "account", 
        "structuring", "smurfing", "layering", "deposit", "withdrawal", "transfer", 
        "fraud", "suspicious", "check", "eda", "summary", "overview", "txns", 
        "aml", "flag", "risk", "data", "dataset", "table", "csv", "pattern", "activity"
    ]
    
    # Check for direct entity lookups
    cust_match = re.search(r"(?:customer\s*(?:id)?\s*[:#]?\s*|cust\s*)([0-9]{3,6})", user_query, re.IGNORECASE)
    
    # Capability check: If no relevant terms or customer IDs are detected, it's unsupported
    if not any(word in query_lower for word in aml_keywords) and not cust_match:
        return False, "I can't help with that. Please ask questions related to AML, financial transactions, or suspicious activities."
        
    return True, "Supported"
