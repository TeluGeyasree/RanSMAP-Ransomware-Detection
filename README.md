# Machine Learning-Based Ransomware Detection Using Low-Level Memory Access Patterns

A machine learning system that detects ransomware from **low-level memory and storage access behavior** instead of traditional signature-based detection. It is built on the RanSMAP 2024 dataset. Four classifiers are trained and compared, and a Streamlit app lets you upload a feature file, choose a model, and view predictions.

## Highlights

- Classifies 10-second windows of system activity as **ransomware or benign**.
- Compares **Random Forest, SVM, k-NN and XGBoost**. XGBoost scored best on held-out trials (F1 0.964, ROC-AUC 0.985), with Random Forest close behind.
- Evaluation is **grouped by trial** (80/20 hold-out and 10-fold StratifiedGroupKFold), so windows from one trial never appear in both train and test.
- Includes a **Streamlit app** with CSV upload and model selection.

## Dataset

This project uses the **RanSMAP 2024 (Ransomware Storage and Memory Access Patterns)** dataset by M. Hirano and R. Kobayashi.

The dataset and the generated Parquet files are **not included** in this repository because of GitHub's file size limits. Download the dataset here:
https://www.kaggle.com/datasets/hiranomanabu/ransmap-2024-ransomware-behavioral-features

The dataset contains **1,970 trial runs** across four splits: Original (1,440), Extra (360), Mix (100) and Variants (70). Each trial has six log files: `mem_write.csv`, `mem_read.csv`, `mem_exec.csv`, `mem_readwrite.csv`, `ata_write.csv` and `ata_read.csv`. They record low-level memory and storage events such as timestamps, Guest Physical Address (GPA) or Logical Block Address (LBA), entropy and page type.

## Project Workflow

The work is organized in phases (see `notebooks/`):

| Phase | File | What it does |
| ----- | ---- | ------------ |
| 1 | `phase1_data_loading.py` | Scans the trial folders and converts the six raw CSV types into Parquet files, 20 trials at a time, to fit in memory |
| 2 | `phase2_eda.ipynb` | Explores the data. Single events are weak signals: entropy and page type have almost no correlation with the label (about -0.03 and 0.04), and benign apps such as Zip and AESCrypt show higher average entropy than ransomware |
| 3 | `phase3_feature_engineering.ipynb` | Builds window-level features with a 10-second window sliding 1 second at a time |
| 4 | `phase4_models.ipynb` | Trains and tunes the four models with trial-grouped cross-validation and a hold-out split |
| 5 | `phase5_evaluation.ipynb` | ROC and Precision-Recall curves, per-class results and error analysis |

After feature engineering, the table has **137,406 rows** (94,652 malicious and 42,754 benign, about 69% / 31%).

## Features

Features are computed per window for six access types (`write`, `read`, `exec`, `readwrite`, `ata_write`, `ata_read`), giving **28 feature columns**:

- `entropy_avg_*`: average Shannon entropy of the written data
- `count_4kb_*`, `count_2mb_*`, `count_mmio_*`: number of accesses by page type
- `addr_var_*`: variance of the accessed addresses

**13 of the 28 columns carry signal.** The other 15 are constant (see Known Issues). The most important features for XGBoost are `entropy_avg_write`, `count_4kb_write` and `addr_var_write`. All 28 columns are kept so the saved models and the app's input format stay unchanged.

## Results

Scores below are from a **trial-grouped 80/20 hold-out test**: 1,576 training trials and 394 unseen test trials (28,340 windows). F1 is for the malicious class. 10-fold StratifiedGroupKFold cross-validation, also grouped by trial, gave similar results (XGBoost 0.954 to 0.961 depending on tuning, Random Forest 0.958, k-NN 0.929, SVM 0.918).

| Model | F1 Score | ROC-AUC | PR-AUC |
| ----- | -------- | ------- | ------ |
| XGBoost | **0.9638** | **0.9853** | **0.9941** |
| Random Forest | 0.9624 | 0.9817 | 0.9927 |
| k-Nearest Neighbors | 0.9357 | 0.9367 | 0.9760 |
| Support Vector Machine | 0.9219 | 0.9495 | 0.9791 |

XGBoost and Random Forest perform almost the same. The difference is smaller than the spread across cross-validation folds.

![ROC curves](RESULTS/roc_curves.png)

![Precision-Recall curves](RESULTS/pr_curves.png)

**Error analysis (XGBoost, hold-out test):** the false positive rate is 7.1% and the false negative rate is 4.5%. Benign Zip and AESCrypt cause 319 of the 543 false positives (59%), which matches the EDA finding that they imitate ransomware entropy. Most missed ransomware comes from Ryuk (278) and WannaCry (263) out of 941 false negatives.

## Trained Models

`all_models.pkl` (126 MB, contains all four models) is too large for the repository. Download it from the [v1.0 release](https://github.com/TeluGeyasree/RanSMAP-Ransomware-Detection/releases/tag/v1.0) and place it in the `MODELS/` folder before running the app. Without it, the prediction page asks for the file. `model.pkl` (XGBoost only) is included for reference.

## Running the Project

Python version used: **3.9**

1. Clone the repository and open a terminal in its folder:

```
   git clone https://github.com/TeluGeyasree/RanSMAP-Ransomware-Detection.git
   cd RanSMAP-Ransomware-Detection
```

2. (Recommended) Create and activate a virtual environment. On Windows:

```
   python -m venv venv
   .\venv\Scripts\Activate.ps1
```

3. Install the required packages:

```
   pip install -r requirements.txt
```

4. Download `all_models.pkl` from the release (see Trained Models) into `MODELS/`.

5. Start the Streamlit app:

```
   streamlit run app.py
```

6. In the app, upload `sample_data.csv`, choose a model, and view the predictions.

## Sample Input

`sample_data.csv` has **50 rows (25 benign, 25 malicious)** and the 28 input feature columns, with no label column. It is only for trying the app. The rows come from the full dataset, which includes data the models trained on, so do not use it to judge accuracy. `make_sample_input.py` shows how it was created and needs the processed dataset, which can be regenerated by running the notebooks on the Kaggle data.

## Repository Structure

```
├── MODELS/               Saved XGBoost model, scaler, feature list and test predictions
├── RESULTS/              ROC and Precision-Recall plots
├── notebooks/            Phase 1-5 code
├── app.py                Streamlit web app
├── make_sample_input.py  Script used to create the sample file
├── requirements.txt      Python dependencies
├── sample_data.csv       Sample input for the app
└── README.md
```

## Known Issues

- **15 of the 28 feature columns are constant** (all `count_2mb_*` and `count_mmio_*`, the storage page-count columns, and `entropy_avg_ata_read`). Feature engineering counted page types 2, 3 and 0, but the data contains other codes (types 1, 2 and 4 appear in the write logs), and the storage logs have no page type.
- **About 31% of trials (613 of 1,970) have extra rows**, up to 408 instead of the expected 51, because long trials were split across file chunks during window processing. Evaluation is grouped by trial, so these rows never cross the train/test split.
- Hyperparameter tuning ran cross-validation on all trials (including the hold-out trials) and the scaler was fit on all data, so scores may be slightly optimistic.
- Planned fix: process each trial once, correct the page-type codes, and retrain.

## Limitations

- The app does **batch prediction** on an uploaded CSV. It does not monitor a live system.
- The models were trained and evaluated only on RanSMAP, which comes from specific lab machines and ransomware families. Other hardware, programs and newer ransomware are untested.
- Results come from one hold-out split and 10-fold cross-validation on this dataset and should not be read as production accuracy.

## Author

**Telu Geyasree**: [GitHub](https://github.com/TeluGeyasree)

## Reference

M. Hirano and R. Kobayashi, *RanSMAP: Open Dataset of Ransomware Storage and Memory Access Patterns for Creating Deep Learning Based Ransomware Detectors*, Computers & Security, 2024.
