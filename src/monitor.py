"""
Solar Panel OCR Monitor — Drift & Performance Monitoring
COS40007 AI Engineering — Group CL02_G06
Monitors unknown brand rate and data drift across serial number scan data.
"""

import os
import json
import csv
import re
import datetime
import pandas as pd
import numpy as np
from pathlib import Path

MONITORING_DIR  = Path("monitoring")
LOGS_DIR        = MONITORING_DIR / "logs"
REPORTS_DIR     = MONITORING_DIR / "reports"
METRICS_DIR     = Path("artifacts/metrics")

for d in [LOGS_DIR, REPORTS_DIR, METRICS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Drift thresholds
UNKNOWN_RATE_THRESHOLD  = 0.20   # Alert if >20% serials return Unknown
CONFIDENCE_THRESHOLD    = 0.70   # Alert if avg confidence drops below 0.70
MIN_SAMPLES_FOR_DRIFT   = 5      # Need at least 5 samples to check drift

SERIAL_PATTERNS = [
    (r"^\d{3,4}[A-Z]{2,}.*\|", "Trina Solar"),
    (r"^TSM[-]?[A-Z0-9]", "Trina Solar"),
    (r"^P0\d{12,}", "Trina Solar"),
    (r"^A0\d{12,}", "Trina Solar"),
    (r"^\d{3,4}[A-Z]{2,}", "Trina Solar"),
    (r"^\d{24}$", "JinkoSolar"),
    (r"^JKM\d", "JinkoSolar"),
    (r"^LRP?I?\d", "LONGi Solar"),
    (r"^LR\d", "LONGi Solar"),
    (r"^CS[0-9K3W]", "Canadian Solar"),
    (r"^JAM\d", "JA Solar"),
    (r"^9030\d{14,}", "Hanwha Qcells"),
    (r"^Q\.PEAK", "Hanwha Qcells"),
    (r"^Q\.TRON", "Hanwha Qcells"),
    (r"^RSM\d", "Risen Energy"),
    (r"^STP\d", "Suntech Power"),
    (r"^7\d{9,}", "REC Group"),
    (r"^TN\d", "Tindo Solar"),
    (r"^HiE", "Hyundai Energy"),
    (r"^HiS", "Hyundai Energy"),
    (r"^AIKO[-]?[A-Z]", "AIKO Solar"),
    (r"^GEB\d", "Kaneka"),
    (r"^143P\d{9,}", "Solar Juice"),
    (r"^UL[-]\d{3}[MP]", "Ulica Solar"),
    (r"^LNPV[-]", "Linuo Photovoltaic"),
    (r"^OSO\d", "Opal Solar (DELISTED)"),
    (r"^GCL\d", "GCL Solar (DELISTED)"),
    (r"^BYD\d", "BYD Solar (DELISTED)"),
    (r"^BP\d", "BP Solar (DISCONTINUED)"),
]

def predict_brand(serial):
    s = serial.strip().upper()
    for pattern, brand in SERIAL_PATTERNS:
        if re.match(pattern, s, re.IGNORECASE):
            return brand
    return "Unknown"

def get_confidence(brand):
    if brand == "Unknown":
        return 0.5
    if "DELISTED" in brand or "DISCONTINUED" in brand:
        return 0.75
    return 1.0

def check_data_drift(df, label="monitor"):
    """Check for data drift based on unknown rate and confidence scores."""
    if df.empty:
        return None

    serials = df.get("serial_no", df.get("Serial_Number", pd.Series(dtype=str))).astype(str)
    total = len(serials)

    if total < MIN_SAMPLES_FOR_DRIFT:
        print(f"Not enough samples for drift detection ({total} < {MIN_SAMPLES_FOR_DRIFT})")
        return None

    predictions = [predict_brand(s) for s in serials]
    confidences = [get_confidence(p) for p in predictions]

    unknown_count    = predictions.count("Unknown")
    unknown_rate     = unknown_count / total
    avg_confidence   = sum(confidences) / len(confidences)
    delisted_count   = sum(1 for p in predictions if "DELISTED" in p or "DISCONTINUED" in p)

    brand_dist = {}
    for p in predictions:
        brand_dist[p] = brand_dist.get(p, 0) + 1

    drift_detected   = unknown_rate > UNKNOWN_RATE_THRESHOLD
    low_confidence   = avg_confidence < CONFIDENCE_THRESHOLD

    report = {
        "label":              label,
        "timestamp":          datetime.datetime.now().isoformat(),
        "total_samples":      total,
        "unknown_count":      unknown_count,
        "unknown_rate":       round(unknown_rate, 4),
        "avg_confidence":     round(avg_confidence, 4),
        "delisted_detected":  delisted_count,
        "brand_distribution": brand_dist,
        "drift_detected":     drift_detected,
        "low_confidence":     low_confidence,
        "alerts":             [],
    }

    if drift_detected:
        alert = f"DATA DRIFT ALERT: Unknown brand rate {unknown_rate:.1%} exceeds threshold {UNKNOWN_RATE_THRESHOLD:.1%}"
        report["alerts"].append(alert)
        print(f"⚠️  {alert}")

    if low_confidence:
        alert = f"LOW CONFIDENCE ALERT: Avg confidence {avg_confidence:.2f} below threshold {CONFIDENCE_THRESHOLD:.2f}"
        report["alerts"].append(alert)
        print(f"⚠️  {alert}")

    if delisted_count > 0:
        alert = f"DELISTED PANELS DETECTED: {delisted_count} panels from delisted/discontinued brands"
        report["alerts"].append(alert)
        print(f"⚠️  {alert}")

    if not report["alerts"]:
        print(f"✅ No drift detected. Unknown rate: {unknown_rate:.1%}, Confidence: {avg_confidence:.2f}")

    return report

def save_monitoring_report(report, name="drift_report"):
    if not report:
        return

    # Save JSON report
    report_path = REPORTS_DIR / f"{name}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Save to monitoring log
    log_path = LOGS_DIR / "monitoring.log"
    with open(log_path, "a") as f:
        f.write(f"\n{'='*50}\n")
        f.write(f"Timestamp: {report['timestamp']}\n")
        f.write(f"Label: {report['label']}\n")
        f.write(f"Samples: {report['total_samples']}\n")
        f.write(f"Unknown Rate: {report['unknown_rate']:.1%}\n")
        f.write(f"Avg Confidence: {report['avg_confidence']:.2f}\n")
        f.write(f"Drift Detected: {report['drift_detected']}\n")
        if report["alerts"]:
            f.write("ALERTS:\n")
            for alert in report["alerts"]:
                f.write(f"  - {alert}\n")

    # Save metrics for pipeline
    metrics_path = METRICS_DIR / "monitoring_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to {report_path}")

def monitor_new_data():
    """Run monitoring on new data to check for drift before retraining."""
    new_data_path = Path("data/new_data.csv")
    if not new_data_path.exists():
        print("No new data file found.")
        return False

    df = pd.read_csv(new_data_path)
    print(f"\n=== MONITORING NEW DATA ({len(df)} records) ===")
    report = check_data_drift(df, label="new_data")
    save_monitoring_report(report, name="new_data_drift_report")

    if report and report["drift_detected"]:
        print("\n🔄 Drift detected — retraining recommended.")
        return True
    return False

def monitor_existing_data():
    """Run monitoring on train and test sets."""
    for csv_path, label in [("data/train.csv", "train"), ("data/test.csv", "test")]:
        if Path(csv_path).exists():
            df = pd.read_csv(csv_path)
            print(f"\n=== MONITORING {label.upper()} DATA ({len(df)} records) ===")
            report = check_data_drift(df, label=label)
            save_monitoring_report(report, name=f"{label}_drift_report")

if __name__ == "__main__":
    print("=== Solar Panel OCR Monitor ===")
    print(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    monitor_existing_data()
    drift_found = monitor_new_data()
    print(f"\nMonitoring complete. Drift detected: {drift_found}")
