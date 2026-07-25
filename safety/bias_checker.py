import pandas as pd
from typing import List, Dict, Any, Optional
from schemas import FlaggedItem


def check_flag_rate_by_segment(all_flagged: List[FlaggedItem], full_df: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Analyzes whether flagged entities disproportionately represent certain countries or customer segments.
    Returns a warning dictionary if any group's flag rate exceeds 2.0x its population share.
    """
    if full_df is None or full_df.empty or not all_flagged:
        return None

    flagged_cust_ids = set(item.customer_id for item in all_flagged)
    
    # Get distinct customer demographics
    cust_df = full_df[["customer_id", "country", "customer_segment"]].drop_duplicates()
    total_customers = len(cust_df)
    
    if total_customers == 0:
        return None

    warnings = []

    # 1. Check Country segment bias
    if "country" in cust_df.columns and cust_df["country"].notnull().any():
        country_counts = cust_df["country"].value_counts()
        flagged_cust_df = cust_df[cust_df["customer_id"].isin(flagged_cust_ids)]
        flagged_country_counts = flagged_cust_df["country"].value_counts()

        for country, count in country_counts.items():
            pop_share = count / total_customers
            flagged_count = flagged_country_counts.get(country, 0)
            flag_share = flagged_count / len(flagged_cust_ids) if flagged_cust_ids else 0
            
            # Check for disproportionate flagging (>2x share)
            if pop_share > 0.05 and flag_share > (2.0 * pop_share):
                warnings.append({
                    "dimension": "country",
                    "group": country,
                    "population_share": round(pop_share * 100, 1),
                    "flagged_share": round(flag_share * 100, 1),
                    "ratio": round(flag_share / pop_share, 2)
                })

    # 2. Check Customer Segment bias
    if "customer_segment" in cust_df.columns and cust_df["customer_segment"].notnull().any():
        segment_counts = cust_df["customer_segment"].value_counts()
        flagged_cust_df = cust_df[cust_df["customer_id"].isin(flagged_cust_ids)]
        flagged_segment_counts = flagged_cust_df["customer_segment"].value_counts()

        for segment, count in segment_counts.items():
            pop_share = count / total_customers
            flagged_count = flagged_segment_counts.get(segment, 0)
            flag_share = flagged_count / len(flagged_cust_ids) if flagged_cust_ids else 0
            
            if pop_share > 0.05 and flag_share > (2.0 * pop_share):
                warnings.append({
                    "dimension": "customer_segment",
                    "group": segment,
                    "population_share": round(pop_share * 100, 1),
                    "flagged_share": round(flag_share * 100, 1),
                    "ratio": round(flag_share / pop_share, 2)
                })

    if warnings:
        return {
            "status": "Disproportionate Flag Rate Detected",
            "warnings": warnings,
            "recommendation": "Review segment calibration to prevent automated demographic bias."
        }

    return None
