import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FEEDBACK_LOG = BASE_DIR / "feedback_log.jsonl"
DYNAMIC_CONFIG = BASE_DIR / "dynamic_config.json"

def optimize_thresholds():
    if not FEEDBACK_LOG.exists():
        print("No feedback log found. Nothing to optimize.")
        return

    true_positives = 0
    false_positives = 0

    with open(FEEDBACK_LOG, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if data.get("feedback") == "True Positive":
                    true_positives += 1
                elif data.get("feedback") == "False Positive":
                    false_positives += 1
            except Exception:
                pass

    total = true_positives + false_positives
    if total == 0:
        print("No valid feedback found.")
        return

    fp_ratio = false_positives / total
    print(f"Total Feedback: {total} (TP: {true_positives}, FP: {false_positives})")
    print(f"False Positive Ratio: {fp_ratio:.2f}")

    # Load existing dynamic config or start fresh with defaults from config.py
    # We'll just tweak ML_ANOMALY_SCORE_THRESHOLD (default 0.6)
    current_threshold = 0.6
    config_data = {}

    if DYNAMIC_CONFIG.exists():
        try:
            with open(DYNAMIC_CONFIG, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                current_threshold = float(config_data.get("ML_ANOMALY_SCORE_THRESHOLD", 0.6))
        except Exception:
            pass

    # Tuning logic:
    # If FP ratio > 0.5 (Too many false alarms), make model STRICTER (increase threshold)
    # If FP ratio < 0.1 (Model is doing great but might be missing things), make model LOOSER (decrease threshold)
    new_threshold = current_threshold

    if fp_ratio > 0.5:
        new_threshold = min(0.9, current_threshold + 0.05)
        print("Action: Increasing anomaly threshold to reduce False Positives.")
    elif fp_ratio < 0.1:
        new_threshold = max(0.1, current_threshold - 0.05)
        print("Action: Decreasing anomaly threshold to cast a wider net.")
    else:
        print("Action: False Positive ratio is stable. No threshold changes required.")

    if new_threshold != current_threshold:
        config_data["ML_ANOMALY_SCORE_THRESHOLD"] = round(new_threshold, 3)
        with open(DYNAMIC_CONFIG, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
        print(f"Updated ML_ANOMALY_SCORE_THRESHOLD from {current_threshold} to {new_threshold:.3f}")

if __name__ == "__main__":
    print("Running Nightly Feedback Optimizer...")
    optimize_thresholds()
    print("Done.")
