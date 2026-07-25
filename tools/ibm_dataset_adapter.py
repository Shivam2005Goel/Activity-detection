import pandas as pd
from safety.fallback_handler import safe_tool_call


@safe_tool_call("ibm_dataset_adapter")
def adapt_ibm_dataset(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Schema Adapter: Maps native Kaggle IBM AML dataset columns onto the system's
    internal transaction schema.
    """
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    df = pd.DataFrame()
    df["transaction_id"] = df_raw.index.astype(str).map(lambda i: f"IBM{int(i):07d}")
    
    from_bank = df_raw["From Bank"].astype(str) if "From Bank" in df_raw.columns else "B0"
    account = df_raw["Account"].astype(str) if "Account" in df_raw.columns else "A0"
    df["customer_id"] = from_bank + "_" + account
    df["account_id"] = account
    
    if "Timestamp" in df_raw.columns:
        df["timestamp"] = pd.to_datetime(df_raw["Timestamp"])
    else:
        df["timestamp"] = pd.datetime.now()

    df["amount"] = df_raw["Amount Paid"] if "Amount Paid" in df_raw.columns else df_raw.get("Amount Received", 0.0)
    df["currency"] = df_raw["Payment Currency"] if "Payment Currency" in df_raw.columns else "USD"
    
    payment_format = df_raw["Payment Format"].astype(str).str.lower() if "Payment Format" in df_raw.columns else "wire"
    df["transaction_type"] = payment_format
    df["channel"] = payment_format

    to_bank = df_raw["To Bank"].astype(str) if "To Bank" in df_raw.columns else "B0"
    to_account = df_raw["Account.1"].astype(str) if "Account.1" in df_raw.columns else "A0"
    df["counterparty_id"] = to_bank + "_" + to_account

    df["country"] = None
    df["customer_segment"] = None
    
    # Ground truth column retained ONLY for offline backtesting (never fed to live detection tools)
    if "Is Laundering" in df_raw.columns:
        df["is_laundering_ground_truth"] = df_raw["Is Laundering"]

    return df
