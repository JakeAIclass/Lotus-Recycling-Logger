"""
Preprocess New Data
COS40007 AI Engineering — Group CL02_G06
Merges new_data.csv into train.csv when new data is pushed.
"""

import pandas as pd
from pathlib import Path
import datetime

TRAIN_CSV    = Path("data/train.csv")
NEW_DATA_CSV = Path("data/new_data.csv")

def preprocess():
    if not NEW_DATA_CSV.exists():
        print("No new_data.csv found. Skipping preprocessing.")
        return

    new_df = pd.read_csv(NEW_DATA_CSV)
    print(f"New data: {len(new_df)} records")

    if TRAIN_CSV.exists():
        train_df = pd.read_csv(TRAIN_CSV)
        print(f"Existing train data: {len(train_df)} records")
        combined = pd.concat([train_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["serial_no"], keep="last")
    else:
        combined = new_df

    combined.to_csv(TRAIN_CSV, index=False)
    print(f"Updated train.csv: {len(combined)} total records")

    # Log the merge
    log_path = Path("monitoring/logs/preprocessing.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"{datetime.datetime.now().isoformat()} - Merged {len(new_df)} new records. Total: {len(combined)}\n")

if __name__ == "__main__":
    preprocess()
