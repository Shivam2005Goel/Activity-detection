import pandas as pd
from typing import Tuple

REQUIRED_COLUMNS = [
    "transaction_id",
    "customer_id",
    "account_id",
    "timestamp",
    "amount",
    "currency",
    "transaction_type",
    "channel",
    "counterparty_id",
    "country",
    "customer_segment"
]

CRITICAL_NON_NULL_COLUMNS = [
    "transaction_id",
    "customer_id",
    "timestamp",
    "amount"
]


def validate_input_df(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validates input DataFrame schema and data integrity before downstream processing.
    """
    if df is None:
        return False, "Input DataFrame is None."

    if df.empty:
        return True, "DataFrame is empty (valid zero-row result)."

    # 1. Check required columns exist
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        return False, f"Missing required columns in DataFrame: {missing_cols}"

    # 2. Check critical non-null columns
    for col in CRITICAL_NON_NULL_COLUMNS:
        if df[col].isnull().all():
            return False, f"Critical column '{col}' is entirely null."

    # 3. Check amount column is numeric and non-negative
    try:
        numeric_amounts = pd.to_numeric(df["amount"], errors="coerce")
        if numeric_amounts.isnull().any():
            return False, "Column 'amount' contains non-numeric values."
        if (numeric_amounts < 0).any():
            return False, "Column 'amount' contains negative values."
    except Exception as e:
        return False, f"Error validating 'amount' column: {str(e)}"

    # 4. Check timestamp parseability
    try:
        pd.to_datetime(df["timestamp"], errors="raise")
    except Exception as e:
        return False, f"Column 'timestamp' contains invalid datetime values: {str(e)}"

    return True, "Validation successful."
