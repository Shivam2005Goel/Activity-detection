import time
import json
import random
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
STREAM_LOG = BASE_DIR / "stream_alerts.jsonl"

def generate_stream():
    """
    Simulates real-time transaction ingestion and lightweight rule processing.
    Writes flagged transactions to stream_alerts.jsonl.
    """
    print(f"Starting real-time streaming simulation. Writing to {STREAM_LOG}")
    
    customers = [f"CUST{str(i).zfill(4)}" for i in range(1, 100)]
    
    while True:
        try:
            # Simulate a transaction
            cust_id = random.choice(customers)
            amount = random.uniform(10.0, 20000.0)
            
            # 5% chance of an anomaly
            is_anomaly = random.random() < 0.05
            
            if is_anomaly:
                alert = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "customer_id": cust_id,
                    "event_type": "STREAM_ALERT",
                    "amount": round(amount, 2),
                    "reason": "Sudden volume spike detected in stream" if amount > 10000 else "High frequency transfer pattern"
                }
                
                with open(STREAM_LOG, "a") as f:
                    f.write(json.dumps(alert) + "\n")
                print(f"[ALERT] Flagged {cust_id} for {alert['reason']}")
            
            time.sleep(1)  # 1 transaction per second
            
        except KeyboardInterrupt:
            print("Stopping stream processor.")
            break

if __name__ == "__main__":
    generate_stream()
