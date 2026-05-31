# Solar Panel Recycling Data Logger
### COS40007 AI Engineering — Group CL02_G06

**Team Members:**
- Jake Vippond (105372869)
- Duc Anh Dao (104647993)
- Le Nguyen Vu Dang (104776732)
- Charitha Pallemulle Mudiyanselage (104178396)

---

## Project Overview

An AI-powered solar panel identification and tracking system for the recycling industry. The system uses a regex-based serial number intelligence engine to identify solar panels by brand, model, wattage, voltage, age, and compliance status from their serial number alone. Data is collected by scanning panel barcodes in the field and adding scan records to the dataset. The MLOps pipeline automatically retrains and evaluates the model when new data is pushed to the repository.

The project was developed in collaboration with Lotus Recycling (Campbellfield, VIC) — Australia's only genuine full-recovery solar recycler. Real panel serial numbers were collected on-site to build the training dataset.

---

## Problem Statement

Australia is facing a solar panel recycling crisis. Over 100,000 tonnes of panels will reach end of life annually by 2035. The Solar Stewardship Scheme requires panels to be tracked and responsibly recycled, but there is currently no standardised system for identifying panels once they leave the roof. Workers manually record panel information by hand, leading to lost data, misidentified panels, and no chain of custody.

---

## Our Solution

A serial number intelligence engine that identifies solar panels from their barcode data alone. When a panel serial number is entered into the system, it is run through a regex pattern matching engine covering 30+ manufacturers. The system returns the brand, model series, wattage, voltage, estimated manufacturing date, degradation estimate, IEC certification, warranty status, and compliance information.

New scan data is added to `data/new_data.csv` and pushed to GitHub. This automatically triggers the MLOps pipeline which preprocesses the data, checks for drift, retrains the model, evaluates accuracy, and uploads performance artifacts.

---

## How Data Is Collected

Serial numbers are collected by scanning the barcode on the backsheet of solar panels using a phone camera. The raw barcode data is recorded and added to the dataset manually. In future, this process will be automated using EasyOCR to read the serial number directly from the barcode image.

---

## Project Structure

```
├── .github/workflows/train.yml       # GitHub Actions automated pipeline
├── src/
│   ├── monitor.py                    # Drift and performance monitoring
│   ├── evaluate.py                   # Model evaluation and reporting
│   └── preprocess_new_data.py        # Merges new data into training set
├── data/
│   ├── train.csv                     # Training dataset (real panel scans from Lotus Recycling)
│   ├── test.csv                      # Test dataset
│   └── new_data.csv                  # Add new panel scan data here to trigger retraining
├── model.py                          # Main training and evaluation script
├── requirements.txt                  # Python dependencies
└── README.md
```

---

## How To Run Locally

```bash
pip install -r requirements.txt
python model.py
python src/monitor.py
python src/evaluate.py
```

---

## How To Trigger Retraining

Add new panel scan records to `data/new_data.csv` and push to main:

```bash
git add data/new_data.csv
git commit -m "Add new panel scan data"
git push
```

GitHub Actions will automatically run the full pipeline:
1. Preprocess and merge new data into train.csv
2. Run drift detection — alert if unknown brand rate exceeds 20%
3. Train and evaluate the model
4. Upload artifacts (model_results.png, metrics.txt)

---

## Dataset

Training data was collected at Lotus Recycling, Campbellfield VIC. Real panel serial numbers from the following brands are included:

- Trina Solar (multiple serial formats)
- Hanwha Q.CELLS
- Canadian Solar
- JA Solar
- LONGi Solar
- Risen Energy
- Suntech Power
- JinkoSolar
- Tindo Solar
- REC Group
- Hyundai Energy
- Kaneka (discontinued Japanese thin-film)
- Solar Juice (Australian distributor)
- AIKO Solar
- Ulica Solar
- Linuo Photovoltaic

---

## GitHub Link

https://github.com/COS40007-2026-Classrooms/applied-project-cl02_g06/
