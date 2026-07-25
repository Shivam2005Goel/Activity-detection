import json
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config

def log_event(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Appends a structured JSON line event to the append-only audit log file.
    """
    audit_file = Path(config.AUDIT_LOG_PATH)
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": event_type,
        "payload": payload
    }
    
    try:
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, default=str) + "\n")
    except Exception as e:
        print(f"Error writing to audit log: {str(e)}", file=sys.stderr)


def get_recent_audit_logs(limit: int = 50) -> list[Dict[str, Any]]:
    """
    Reads the last N lines from audit_log.jsonl for API/Dashboard display.
    """
    audit_file = Path(config.AUDIT_LOG_PATH)
    if not audit_file.exists():
        return []
    
    logs = []
    try:
        with open(audit_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    logs.append(json.loads(line))
    except Exception as e:
        print(f"Error reading audit log: {str(e)}", file=sys.stderr)
        
    return list(reversed(logs))
