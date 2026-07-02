# Ransomware Detection 

This project presents a machine learning-based ransomware detection system that identifies ransomware using **low-level memory and storage access patterns** instead of traditional signature-based detection. Using the RanSMAP 2024 dataset, raw behavioral logs are processed into meaningful features through data preprocessing and feature engineering. Multiple machine learning models, including XGBoost, Random Forest, SVM, and k-Nearest Neighbors, are trained and evaluated to distinguish ransomware from benign applications. A Streamlit-based web application is also provided for interactive prediction and model evaluation.

## Dataset

This project uses the **RanSMAP 2024 (Ransomware Storage and Memory Access Patterns)** dataset developed by **M. Hirano and R. Kobayashi**.

Due to GitHub's file size limitations, the dataset and generated Parquet files are **not included** in this repository.

Dataset can be downloaded from:

https://www.kaggle.com/datasets/hiranomanabu/ransmap-2024-ransomware-behavioral-features

The dataset contains **1,970 trial runs** across four splits:

- Original (1440)
- Extra (360)
- Mix (100)
- Variants (70)

Each trial contains six behavioral log files:

- `mem_write.csv`
- `mem_read.csv`
- `mem_exec.csv`
- `mem_readwrite.csv`
- `ata_write.csv`
- `ata_read.csv`

The raw dataset records low-level memory and storage events with columns such as timestamp (seconds and nanoseconds), Guest Physical Address (GPA) or Logical Block Address (LBA), entropy, page type, and other event-specific information. During preprocessing, additional metadata including class name, trial ID, labels, and malicious/benign indicators are added for machine learning.

## Results

Four machine learning models were trained and evaluated:

| Model | F1 Score |
|--------|----------:|
| XGBoost | **0.9638** |
| Random Forest | 0.9624 |
| k-Nearest Neighbors | 0.9357 |
| Support Vector Machine | 0.9219 |

XGBoost achieved the best overall performance.

## Running the Project

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the Streamlit application:

```bash
streamlit run app.py
```

## Reference

M. Hirano and R. Kobayashi, *RanSMAP: Open Dataset of Ransomware Storage and Memory Access Patterns for Creating Deep Learning Based Ransomware Detectors*, Computers & Security, 2024.
