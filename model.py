"""
Solar Panel Serial Number Intelligence — Training & Evaluation
COS40007 AI Engineering — Group CL02_G06
Uses regex pattern matching to identify solar panel brands from serial numbers collected in the field.
New scan data in data/new_data.csv triggers retraining via GitHub Actions.
"""

import os
import json
import csv
import re
import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

# -------------------------
# PATHS
# -------------------------
ARTIFACTS_DIR   = Path("artifacts")
METRICS_DIR     = ARTIFACTS_DIR / "metrics"
METADATA_DIR    = ARTIFACTS_DIR / "metadata"
MODELS_DIR      = ARTIFACTS_DIR / "models"
DATA_DIR        = Path("data")
TRAIN_CSV       = DATA_DIR / "train.csv"
TEST_CSV        = DATA_DIR / "test.csv"
NEW_DATA_CSV    = DATA_DIR / "new_data.csv"

for d in [ARTIFACTS_DIR, METRICS_DIR, METADATA_DIR, MODELS_DIR, DATA_DIR,
          Path("monitoring/logs"), Path("monitoring/reports")]:
    d.mkdir(parents=True, exist_ok=True)

# -------------------------
# SERIAL NUMBER REGEX ENGINE
# (This is the ML rule-based model for solar panel identification)
# -------------------------
SERIAL_PATTERNS = [
    # --- TRINA SOLAR ---
    # Pipe-delimited: 440NEG9R.25|Q1||00407916 or TSM-275PD05|A09180605701597
    (r"^\d{3,4}[A-Z]{2,}.*\|",  "Trina Solar"),
    (r"^TSM[-]?[A-Z0-9]",       "Trina Solar"),
    # P-prefix barcode: P012600100633255 (confirmed at Lotus Recycling)
    (r"^P0\d{12,}",              "Trina Solar"),
    # A-prefix older serial: A09180605701597 (confirmed at Lotus Recycling)
    (r"^A0\d{12,}",              "Trina Solar"),
    # Digit+letter model code
    (r"^\d{3,4}[A-Z]{2,}",      "Trina Solar"),

    # --- JINKO SOLAR ---
    # 24-digit numeric (confirmed from JinkoSolar EU verification guide)
    (r"^\d{24}$",                "JinkoSolar"),
    (r"^JKM\d",                  "JinkoSolar"),
    (r"^JK\d{6,}",               "JinkoSolar"),

    # --- LONGI SOLAR ---
    (r"^LRP?I?\d",               "LONGi Solar"),
    (r"^LR\d",                   "LONGi Solar"),

    # --- CANADIAN SOLAR ---
    (r"^CS[0-9K3W]",             "Canadian Solar"),

    # --- JA SOLAR ---
    (r"^JAM\d",                  "JA Solar"),
    (r"^JA\d{6,}",               "JA Solar"),

    # --- HANWHA Q CELLS ---
    # 19-digit serial starting with 9030 (confirmed at Lotus Recycling)
    (r"^9030\d{14,}",            "Hanwha Qcells"),
    (r"^Q\.PEAK",                "Hanwha Qcells"),
    (r"^Q\.TRON",                "Hanwha Qcells"),
    (r"^Q\.BOOST",               "Hanwha Qcells"),

    # --- RISEN ENERGY ---
    (r"^RSM\d",                  "Risen Energy"),

    # --- SUNTECH POWER ---
    (r"^STP\d",                  "Suntech Power"),

    # --- REC GROUP ---
    (r"^REC\d",                  "REC Group"),
    (r"^7\d{9,}",                "REC Group"),

    # --- TINDO SOLAR (Australian made) ---
    (r"^TN\d",                   "Tindo Solar"),
    (r"^KAR\d",                  "Tindo Solar"),

    # --- HYUNDAI ENERGY ---
    (r"^HiE",                    "Hyundai Energy"),
    (r"^HiS",                    "Hyundai Energy"),

    # --- AIKO SOLAR (confirmed at Lotus Recycling) ---
    (r"^AIKO[-]?[A-Z]",          "AIKO Solar"),

    # --- KANEKA (Japanese thin-film, discontinued 2019, confirmed at Lotus) ---
    (r"^GEB\d",                  "Kaneka"),

    # --- SOLAR JUICE (Australian distributor, confirmed at Lotus Recycling) ---
    (r"^143P\d{9,}",             "Solar Juice"),
    (r"^SJ\s?\d{3}P",            "Solar Juice"),

    # --- ULICA SOLAR (confirmed at Lotus Recycling) ---
    (r"^UL[-]\d{3}[MP]",         "Ulica Solar"),

    # --- LINUO PHOTOVOLTAIC (confirmed at Lotus Recycling) ---
    (r"^LNPV[-]",                "Linuo Photovoltaic"),

    # --- DELISTED BRANDS ---
    (r"^OSO\d",                  "Opal Solar (DELISTED)"),
    (r"^GCL\d",                  "GCL Solar (DELISTED)"),
    (r"^SKT\d",                  "Sunket (DELISTED)"),
    (r"^BYD\d",                  "BYD Solar (DELISTED)"),
    (r"^MSE?\d",                 "MSquare (DELISTED)"),

    # --- DISCONTINUED BRANDS ---
    (r"^BP\d",                   "BP Solar (DISCONTINUED)"),
    (r"^ASE\d",                  "Schott Solar (DISCONTINUED)"),
]

def predict_brand(serial):
    """Predict brand from serial number using regex pattern matching."""
    s = serial.strip().upper()
    for pattern, brand in SERIAL_PATTERNS:
        if re.match(pattern, s, re.IGNORECASE):
            return brand
    return "Unknown"

def extract_wattage(text):
    """Extract wattage from OCR text."""
    match = re.search(r'(\d{3,4})\s?[Ww](?!h)', text)
    return int(match.group(1)) if match else None

def extract_voltage(text):
    """Extract voltage from OCR text."""
    match = re.search(r'(\d{2,3}\.?\d*)\s?[Vv]', text)
    return float(match.group(1)) if match else None

# -------------------------
# LOAD DATA
# -------------------------
def load_data(csv_path):
    if not Path(csv_path).exists():
        print(f"No data found at {csv_path}")
        return pd.DataFrame()
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} records from {csv_path}")
    return df

# -------------------------
# EVALUATE MODEL
# -------------------------
def evaluate(df, label="test"):
    if df.empty:
        print(f"No {label} data to evaluate.")
        return {}

    correct = 0
    total = len(df)
    unknown_count = 0
    delisted_count = 0
    brand_counts = {}
    confidences = []

    for _, row in df.iterrows():
        serial = str(row.get("serial_no", row.get("Serial_Number", "")))
        true_brand = str(row.get("brand", row.get("Brand", "Unknown")))
        predicted = predict_brand(serial)

        if predicted == true_brand:
            correct += 1
        if predicted == "Unknown":
            unknown_count += 1
        if "DELISTED" in predicted or "DISCONTINUED" in predicted:
            delisted_count += 1

        brand_counts[predicted] = brand_counts.get(predicted, 0) + 1

        # Simulate confidence score (1.0 = known brand, 0.5 = unknown)
        conf = 1.0 if predicted != "Unknown" else 0.5
        confidences.append(conf)

    accuracy = correct / total if total > 0 else 0
    unknown_rate = unknown_count / total if total > 0 else 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    metrics = {
        "label": label,
        "total_samples": total,
        "correct_predictions": correct,
        "accuracy": round(accuracy, 4),
        "unknown_rate": round(unknown_rate, 4),
        "avg_confidence": round(avg_confidence, 4),
        "delisted_detected": delisted_count,
        "brand_distribution": brand_counts,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    print(f"\n=== {label.upper()} RESULTS ===")
    print(f"Total samples:     {total}")
    print(f"Accuracy:          {accuracy:.1%}")
    print(f"Unknown rate:      {unknown_rate:.1%}")
    print(f"Avg confidence:    {avg_confidence:.2f}")
    print(f"Delisted detected: {delisted_count}")

    return metrics

# -------------------------
# PLOT RESULTS
# -------------------------
def plot_results(train_metrics, test_metrics, new_metrics=None):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Solar Panel OCR Model — Performance Report", fontsize=14, fontweight="bold")

    # Plot 1: Accuracy comparison
    labels = ["Train", "Test"]
    accuracies = [train_metrics.get("accuracy", 0), test_metrics.get("accuracy", 0)]
    colors = ["#2196F3", "#4CAF50"]
    if new_metrics:
        labels.append("New Data")
        accuracies.append(new_metrics.get("accuracy", 0))
        colors.append("#FF9800")
    axes[0].bar(labels, accuracies, color=colors)
    axes[0].set_title("Brand Detection Accuracy")
    axes[0].set_ylabel("Accuracy")
    axes[0].set_ylim(0, 1)
    for i, v in enumerate(accuracies):
        axes[0].text(i, v + 0.02, f"{v:.1%}", ha="center", fontweight="bold")

    # Plot 2: Unknown rate
    unknown_rates = [train_metrics.get("unknown_rate", 0), test_metrics.get("unknown_rate", 0)]
    if new_metrics:
        unknown_rates.append(new_metrics.get("unknown_rate", 0))
    axes[1].bar(labels, unknown_rates, color=["#F44336" if r > 0.2 else "#4CAF50" for r in unknown_rates])
    axes[1].set_title("Unknown Brand Rate\n(>20% = drift alert)")
    axes[1].set_ylabel("Rate")
    axes[1].set_ylim(0, 1)
    axes[1].axhline(y=0.2, color="red", linestyle="--", label="Drift threshold")
    axes[1].legend()

    # Plot 3: Brand distribution from test set
    brand_dist = test_metrics.get("brand_distribution", {})
    if brand_dist:
        top_brands = sorted(brand_dist.items(), key=lambda x: -x[1])[:8]
        b_names = [b[0][:15] for b in top_brands]
        b_counts = [b[1] for b in top_brands]
        axes[2].barh(b_names, b_counts, color="#2196F3")
        axes[2].set_title("Brand Distribution (Test Set)")
        axes[2].set_xlabel("Count")

    plt.tight_layout()
    output_path = "model_results.png"
    plt.savefig(output_path, dpi=100, bbox_inches="tight")
    print(f"Plot saved to {output_path}")
    return output_path

# -------------------------
# SAVE METRICS
# -------------------------
def save_metrics(train_metrics, test_metrics, new_metrics=None):
    all_metrics = {
        "training": train_metrics,
        "evaluation": test_metrics,
        "timestamp": datetime.datetime.now().isoformat(),
    }
    if new_metrics:
        all_metrics["new_data"] = new_metrics

    # Save JSON
    with open(METRICS_DIR / "evaluation_metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=2)

    # Save metrics.txt for artifact upload
    with open("metrics.txt", "w") as f:
        f.write("=== SOLAR PANEL OCR MODEL METRICS ===\n\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("TRAINING SET:\n")
        f.write(f"  Samples:    {train_metrics.get('total_samples', 0)}\n")
        f.write(f"  Accuracy:   {train_metrics.get('accuracy', 0):.1%}\n")
        f.write(f"  Unknown:    {train_metrics.get('unknown_rate', 0):.1%}\n\n")
        f.write("TEST SET:\n")
        f.write(f"  Samples:    {test_metrics.get('total_samples', 0)}\n")
        f.write(f"  Accuracy:   {test_metrics.get('accuracy', 0):.1%}\n")
        f.write(f"  Unknown:    {test_metrics.get('unknown_rate', 0):.1%}\n")
        if new_metrics:
            f.write("\nNEW DATA:\n")
            f.write(f"  Samples:    {new_metrics.get('total_samples', 0)}\n")
            f.write(f"  Accuracy:   {new_metrics.get('accuracy', 0):.1%}\n")
            f.write(f"  Unknown:    {new_metrics.get('unknown_rate', 0):.1%}\n")

    # Save metadata
    with open(METADATA_DIR / "model_version.txt", "w") as f:
        f.write("1.0.0")
    with open(METADATA_DIR / "last_retrain.txt", "w") as f:
        f.write(datetime.datetime.now().isoformat())

    print("Metrics saved.")

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    print("=== Solar Panel OCR Model Training & Evaluation ===")
    print(f"Started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    train_df = load_data(TRAIN_CSV)
    test_df  = load_data(TEST_CSV)
    new_df   = load_data(NEW_DATA_CSV)

    train_metrics = evaluate(train_df, label="train") if not train_df.empty else {"accuracy": 0, "unknown_rate": 0, "total_samples": 0}
    test_metrics  = evaluate(test_df,  label="test")  if not test_df.empty  else {"accuracy": 0, "unknown_rate": 0, "total_samples": 0}
    new_metrics   = evaluate(new_df,   label="new_data") if not new_df.empty else None

    plot_results(train_metrics, test_metrics, new_metrics)
    save_metrics(train_metrics, test_metrics, new_metrics)

    print("\n=== COMPLETE ===")
