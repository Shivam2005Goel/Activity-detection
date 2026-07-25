import duckdb
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from schemas import Filters
from safety.fallback_handler import safe_tool_call
from safety.schema_validator import validate_input_df


@safe_tool_call("data_loader")
def load_filtered_data(filters: Optional[Filters] = None, csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Loads and filters transaction data from CSV using DuckDB based on input Filters.
    """
    target_path = csv_path if csv_path else config.DATA_PATH
    if not Path(target_path).exists():
        # Fall back to generating sample data if missing
        from scripts.generate_sample_data import generate_synthetic_transactions
        df_gen = generate_synthetic_transactions()
        
    con = duckdb.connect(database=":memory:")
    
    where_clauses = ["1=1"]
    params = []

    if filters:
        if filters.date_start:
            where_clauses.append("CAST(timestamp AS TIMESTAMP) >= CAST(? AS TIMESTAMP)")
            params.append(filters.date_start.isoformat())
        elif filters.date_end:
            # If date_end given without date_start, default to DEFAULT_LOOKBACK_DAYS before date_end
            start_default = (filters.date_end - timedelta(days=config.DEFAULT_LOOKBACK_DAYS)).isoformat()
            where_clauses.append("CAST(timestamp AS TIMESTAMP) >= CAST(? AS TIMESTAMP)")
            params.append(start_default)
            
        if filters.date_end:
            where_clauses.append("CAST(timestamp AS TIMESTAMP) <= CAST(? AS TIMESTAMP)")
            params.append((filters.date_end + timedelta(days=1)).isoformat())
            
        if filters.country:
            where_clauses.append("LOWER(country) = LOWER(?)")
            params.append(filters.country)
            
        if filters.transaction_type:
            where_clauses.append("LOWER(transaction_type) = LOWER(?)")
            params.append(filters.transaction_type)
            
        if filters.customer_segment:
            where_clauses.append("LOWER(customer_segment) = LOWER(?)")
            params.append(filters.customer_segment)

        if filters.amount_threshold is not None:
            where_clauses.append("amount < ?")
            params.append(filters.amount_threshold)

    query = f"""
        SELECT *
        FROM read_csv_auto('{target_path}')
        WHERE {' AND '.join(where_clauses)}
        ORDER BY timestamp ASC
    """
    
    df = con.execute(query, params).df()
    con.close()
    
    is_valid, msg = validate_input_df(df)
    if not is_valid:
        print(f"Data loading validation warning: {msg}")
        
    return df
