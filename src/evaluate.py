"""
Solar Panel OCR Evaluator
COS40007 AI Engineering — Group CL02_G06
Evaluates serial number brand detection accuracy and generates performance report.
"""

import json
import re
import datetime
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

METRICS_DIR = Path("artifacts/metrics")
METRICS_DIR.mkdir(parents=True, exist_ok=True)

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

def run_evaluation(csv_path="data/test.csv"):
    path = Path(csv_path)
    if not path.exists():
        print(f"File not found: {csv_path}")
        return

    df = pd.read_csv(path)
    print(f"Evaluating {len(df)} records from {csv_path}")

    results = []
    for _, row in df.iterrows():
        serial     = str(row.get("serial_no", row.get("Serial_Number", "")))
        true_brand = str(row.get("brand",     row.get("Brand", "Unknown")))
        predicted  = predict_brand(serial)
        correct    = predicted == true_brand
        results.append({
            "serial":     serial,
            "true_brand": true_brand,
            "predicted":  predicted,
            "correct":    correct,
        })

    results_df = pd.DataFrame(results)
    accuracy   = results_df["correct"].mean()
    unknown_rate = (results_df["predicted"] == "Unknown").mean()

    print(f"\nAccuracy:     {accuracy:.1%}")
    print(f"Unknown rate: {unknown_rate:.1%}")

    # Save metrics
    metrics = {
        "accuracy":     round(float(accuracy), 4),
        "unknown_rate": round(float(unknown_rate), 4),
        "total":        len(results_df),
        "correct":      int(results_df["correct"].sum()),
        "timestamp":    datetime.datetime.now().isoformat(),
    }
    with open(METRICS_DIR / "evaluation_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Plot confusion by brand
    brand_accuracy = results_df.groupby("true_brand")["correct"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#4CAF50" if v >= 0.8 else "#F44336" for v in brand_accuracy.values]
    brand_accuracy.plot(kind="barh", ax=ax, color=colors)
    ax.set_title(f"Brand Detection Accuracy by Manufacturer\nOverall: {accuracy:.1%}", fontweight="bold")
    ax.set_xlabel("Accuracy")
    ax.axvline(x=0.8, color="orange", linestyle="--", label="80% target")
    ax.legend()
    plt.tight_layout()
    plt.savefig("model_results.png", dpi=100, bbox_inches="tight")
    print("Plot saved to model_results.png")

if __name__ == "__main__":
    print("=== Solar Panel OCR Evaluation ===")
    run_evaluation("data/test.csv")
