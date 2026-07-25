import random
from datetime import datetime, timedelta
import pandas as pd
from pathlib import Path
import sys

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config

def generate_synthetic_transactions():
    random.seed(42)
    
    start_date = datetime.now() - timedelta(days=120)
    
    customers = [f"CUST{i:04d}" for i in range(1000, 1300)]
    # Ensure CUST4521 is explicitly included
    if "CUST4521" not in customers:
        customers.append("CUST4521")
        
    accounts = {c: f"ACC_{c}" for c in customers}
    countries = ["US", "FR", "GB", "DE", "SG", "CH", "JP"]
    segments = ["retail", "corporate", "high_net_worth"]
    cust_segment_map = {c: random.choice(segments) for c in customers}
    cust_country_map = {c: random.choice(countries) for c in customers}
    
    transactions = []
    txn_counter = 1
    
    # 1. Inject Structuring Pattern for 15 specific customers (including CUST4521)
    structuring_customers = ["CUST4521"] + random.sample([c for c in customers if c != "CUST4521"], 14)
    for c in structuring_customers:
        # Base window within last 30 days
        window_start = datetime.now() - timedelta(days=random.randint(5, 25))
        num_deposits = random.randint(8, 15)
        for i in range(num_deposits):
            txn_time = window_start + timedelta(hours=random.randint(2, 72))
            amount = round(random.uniform(9000.0, 9990.0), 2)
            transactions.append({
                "transaction_id": f"TXN{txn_counter:05d}",
                "customer_id": c,
                "account_id": accounts[c],
                "timestamp": txn_time.isoformat(),
                "amount": amount,
                "currency": "USD",
                "transaction_type": "cash_deposit",
                "channel": random.choice(["branch", "atm"]),
                "counterparty_id": None,
                "country": cust_country_map[c],
                "customer_segment": cust_segment_map[c]
            })
            txn_counter += 1

    # 2. Inject Layering Pattern for 10 customers
    layering_customers = random.sample([c for c in customers if c not in structuring_customers], 10)
    for i, c1 in enumerate(layering_customers):
        # Pick 2-3 target counterparties to create a chain
        chain = [c1] + random.sample([c for c in customers if c != c1], 3)
        chain_start = datetime.now() - timedelta(days=random.randint(10, 60))
        chain_amount = round(random.uniform(50000.0, 150000.0), 2)
        
        for step in range(len(chain) - 1):
            sender = chain[step]
            receiver = chain[step+1]
            txn_time = chain_start + timedelta(hours=step * 12 + random.randint(1, 4))
            transactions.append({
                "transaction_id": f"TXN{txn_counter:05d}",
                "customer_id": sender,
                "account_id": accounts[sender],
                "timestamp": txn_time.isoformat(),
                "amount": round(chain_amount * random.uniform(0.95, 0.99), 2),
                "currency": "USD",
                "transaction_type": "transfer",
                "channel": "wire",
                "counterparty_id": accounts[receiver],
                "country": cust_country_map[sender],
                "customer_segment": cust_segment_map[sender]
            })
            txn_counter += 1

    # 3. Inject Outliers for 20 customers
    outlier_customers = random.sample([c for c in customers if c not in structuring_customers and c not in layering_customers], 20)
    for c in outlier_customers:
        # Give normal small transactions first
        for _ in range(5):
            txn_time = start_date + timedelta(days=random.randint(1, 100))
            transactions.append({
                "transaction_id": f"TXN{txn_counter:05d}",
                "customer_id": c,
                "account_id": accounts[c],
                "timestamp": txn_time.isoformat(),
                "amount": round(random.uniform(50.0, 500.0), 2),
                "currency": "USD",
                "transaction_type": random.choice(["deposit", "withdrawal", "transfer"]),
                "channel": random.choice(["online", "atm"]),
                "counterparty_id": None,
                "country": cust_country_map[c],
                "customer_segment": cust_segment_map[c]
            })
            txn_counter += 1
            
        # Injected spike 8-10x normal
        outlier_time = datetime.now() - timedelta(days=random.randint(2, 40))
        transactions.append({
            "transaction_id": f"TXN{txn_counter:05d}",
            "customer_id": c,
            "account_id": accounts[c],
            "timestamp": outlier_time.isoformat(),
            "amount": round(random.uniform(150000.0, 500000.0), 2),
            "currency": "USD",
            "transaction_type": "transfer",
            "channel": "wire",
            "counterparty_id": accounts[random.choice(customers)],
            "country": cust_country_map[c],
            "customer_segment": cust_segment_map[c]
        })
        txn_counter += 1

    # 4. Generate normal background transactions for all customers
    target_total = 2500
    while len(transactions) < target_total:
        c = random.choice(customers)
        txn_time = start_date + timedelta(days=random.randint(0, 119), hours=random.randint(0, 23))
        t_type = random.choice(["deposit", "withdrawal", "transfer", "cash_deposit"])
        channel = random.choice(["branch", "online", "atm", "wire"])
        counterparty = accounts[random.choice(customers)] if t_type == "transfer" else None
        
        # Normal amount distributions
        amount = round(random.expovariate(1.0 / 300.0) + 10.0, 2)
        if amount > 8500:  # avoid accidental structuring in normal data
            amount = round(random.uniform(10.0, 4000.0), 2)
            
        transactions.append({
            "transaction_id": f"TXN{txn_counter:05d}",
            "customer_id": c,
            "account_id": accounts[c],
            "timestamp": txn_time.isoformat(),
            "amount": amount,
            "currency": "USD",
            "transaction_type": t_type,
            "channel": channel,
            "counterparty_id": counterparty,
            "country": cust_country_map[c],
            "customer_segment": cust_segment_map[c]
        })
        txn_counter += 1

    df = pd.DataFrame(transactions)
    
    # Ensure data dir exists
    data_dir = Path(config.DATA_PATH).parent
    data_dir.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(config.DATA_PATH, index=False)
    print(f"Generated {len(df)} synthetic transactions successfully at {config.DATA_PATH}")
    print(f"Structuring customers count: {len(structuring_customers)}")
    print(f"Layering customers count: {len(layering_customers)}")
    print(f"Outlier customers count: {len(outlier_customers)}")
    return df

if __name__ == "__main__":
    generate_synthetic_transactions()
