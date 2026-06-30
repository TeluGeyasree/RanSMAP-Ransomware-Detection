# =============================================================================
# PHASE 1 — DATA LOADING
# Project : Machine Learning-based Ransomware Detection
#           Using Low-level Memory Access Patterns
# Dataset : RanSMAP 2024 (Kaggle / GitHub: manabu-hirano/RanSMAP)
# Paper   : Hirano & Kobayashi, IEEE CSR 2022
# =============================================================================

import os
import gc
import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime

# =============================================================================
# PATHS
# =============================================================================

RAW_DATA_PATH = r"C:\Users\Shiva\Downloads\RANSMAP_PROJECT\DATA\RanSMAP"
PROCESSED_PATH = r"C:\Users\Shiva\Downloads\RANSMAP_PROJECT\DATA\processed"

os.makedirs(PROCESSED_PATH, exist_ok=True)

# =============================================================================
# WHAT WE ARE LOADING
# =============================================================================
# The dataset has 1970 trial folders across 4 splits:
#   original  → 1440 trials (core dataset, matches the IEEE paper)
#   extra     → 360 trials  (different hardware: i3, DDR5)
#   mix       → 100 trials  (ransomware + benign running together)
#   variants  → 70 trials   (7 Conti ransomware variants)
#
# Inside each trial folder there are 6 CSV files:
#   mem_write.csv      → memory write events  (MOST IMPORTANT — has entropy)
#   mem_read.csv       → memory read events
#   mem_exec.csv       → memory execute events
#   mem_readwrite.csv  → memory read+write events
#   ata_write.csv      → hard drive write events
#   ata_read.csv       → hard drive read events
#
# These files have NO header row — we name the columns ourselves
# Source: GitHub README (manabu-hirano/RanSMAP)
# =============================================================================

SPLITS    = ["original", "extra", "mix", "variants"]
CSV_FILES = ["mem_write", "mem_read", "mem_exec",
             "mem_readwrite", "ata_write", "ata_read"]

# Column names per file type
COLUMNS = {
    "mem_write":     ["time_sec", "time_ns", "GPA", "size",        "entropy",  "page_type"],
    "mem_read":      ["time_sec", "time_ns", "GPA", "size_unused", "col5",     "page_type"],
    "mem_exec":      ["time_sec", "time_ns", "GPA", "size_unused", "col5",     "page_type"],
    "mem_readwrite": ["time_sec", "time_ns", "GPA", "size",        "entropy",  "page_type"],
    "ata_write":     ["time_sec", "time_ns", "LBA", "size",        "entropy",  "unused"],
    "ata_read":      ["time_sec", "time_ns", "LBA", "size",        "col5",     "unused"],
}

# page_type values (from IEEE paper Section II):
#   2 = 4KB page  |  3 = 2MB page  |  0 = MMIO (Memory Mapped I/O)

# =============================================================================
# CLASS LABELS
# =============================================================================
# Malicious = ransomware or wiper malware
# Benign    = normal applications
# Mix       = ransomware running alongside a benign app (from mix/ split)
# =============================================================================

MALICIOUS = {
    "WannaCry", "Sodinokibi", "Darkside", "CaddyWiper",
    "LockBit", "Conti", "SDelete", "REvil", "Ryuk",
    "Conti_01", "Conti_02", "Conti_03", "Conti_04",
    "Conti_05", "Conti_06", "Conti_07"
}

BENIGN = {"Idle", "AESCrypt", "Zip", "Office", "Firefox"}

# Mix classes — ransomware is ACTIVE so we label these malicious
MIX = {
    "AESCrypt_Conti", "AESCrypt_REvil",
    "Firefox_Conti",  "Firefox_REvil", "Firefox_Office_REvil",
    "Office_REvil",   "SDelete_Conti", "SDelete_REvil",
    "Zip_Conti",      "Zip_REvil"
}

# =============================================================================
# STEP 1 — SCAN FOLDER STRUCTURE
# Walk all 4 splits and build a table of every trial folder
# No data is read here — just mapping what exists
# =============================================================================

print("STEP 1 — Scanning folder structure...")
print(f"Base path: {RAW_DATA_PATH}\n")

all_trials = []

for split in SPLITS:
    split_path = os.path.join(RAW_DATA_PATH, split)

    if not os.path.isdir(split_path):
        print(f"  [SKIP] {split} not found")
        continue

    entries = [e for e in os.listdir(split_path)
               if os.path.isdir(os.path.join(split_path, e))]

    # Detect folder depth:
    # original/extra → split/cpu/ram/class/trial  (4 levels)
    # mix/variants   → split/class/trial           (2 levels)
    first      = os.path.join(split_path, entries[0])
    first_sub  = os.listdir(first)[0] if os.listdir(first) else ""
    deep       = first_sub not in MALICIOUS | BENIGN | MIX

    for l1 in sorted(entries):
        l1_path = os.path.join(split_path, l1)
        if not os.path.isdir(l1_path): continue

        if deep:
            # original/extra: cpu → ram → class → trial
            for l2 in sorted(os.listdir(l1_path)):
                l2_path = os.path.join(l1_path, l2)
                if not os.path.isdir(l2_path): continue

                for cls in sorted(os.listdir(l2_path)):
                    cls_path = os.path.join(l2_path, cls)
                    if not os.path.isdir(cls_path): continue

                    label  = ("malicious" if cls in MALICIOUS | MIX
                              else "benign" if cls in BENIGN
                              else "unknown")
                    is_mal = 1 if label == "malicious" else 0 if label == "benign" else -1

                    for trial in sorted(os.listdir(cls_path)):
                        trial_path = os.path.join(cls_path, trial)
                        if not os.path.isdir(trial_path): continue

                        all_trials.append({
                            "split":        split,
                            "cpu_type":     l1,
                            "ram_spec":     l2,
                            "class_name":   cls,
                            "trial_id":     trial,
                            "trial_path":   trial_path,
                            "label":        label,
                            "is_malicious": is_mal
                        })
        else:
            # mix/variants: class → trial directly
            cls    = l1
            label  = ("malicious" if cls in MALICIOUS | MIX
                      else "benign" if cls in BENIGN
                      else "unknown")
            is_mal = 1 if label == "malicious" else 0 if label == "benign" else -1

            for trial in sorted(os.listdir(l1_path)):
                trial_path = os.path.join(l1_path, trial)
                if not os.path.isdir(trial_path): continue

                all_trials.append({
                    "split":        split,
                    "cpu_type":     "n/a",
                    "ram_spec":     "n/a",
                    "class_name":   cls,
                    "trial_id":     trial,
                    "trial_path":   trial_path,
                    "label":        label,
                    "is_malicious": is_mal
                })

# Convert to DataFrame so it's easy to inspect
trials_df = pd.DataFrame(all_trials)

print(f"Total trials found : {len(trials_df)}\n")
print(trials_df.groupby(["class_name", "label"])
      .size().reset_index(name="trials")
      .sort_values("trials", ascending=False)
      .to_string(index=False))

# =============================================================================
# STEP 2 — LOAD ALL CSV FILES AND SAVE AS PARQUET
# Process one file type at a time, one trial at a time
# Write each batch of 20 trials directly to disk — never holds
# more than 20 trials in RAM at once
# =============================================================================

print("\n\nSTEP 2 — Loading CSVs and saving as parquet...")
print(f"Output: {PROCESSED_PATH}\n")

BATCH_SIZE = 20

for ft in CSV_FILES:

    out_path = os.path.join(PROCESSED_PATH, f"{ft}_combined.parquet")

    if os.path.exists(out_path):
        mb = os.path.getsize(out_path) / (1024*1024)
        print(f"  {ft:<20} already saved ({mb:.0f} MB) — skipping")
        continue

    print(f"  Processing {ft}...")

    writer     = None
    batch      = []
    batch_num  = 0
    total_rows = 0

    for i, trial in trials_df.iterrows():

        csv_path = os.path.join(trial["trial_path"], f"{ft}.csv")
        if not os.path.exists(csv_path):
            continue
        if os.path.getsize(csv_path) == 0:
            continue

        # Read one trial CSV
        try:
            df = pd.read_csv(
                csv_path,
                header=None,
                names=COLUMNS[ft],
                dtype={
                    "time_sec":    np.int64,
                    "time_ns":     np.int64,
                    "GPA":         np.float32,
                    "LBA":         np.float32,
                    "size":        np.float32,
                    "size_unused": np.float32,
                    "entropy":     np.float32,
                    "col5":        np.float32,
                    "page_type":   np.int8,
                    "unused":      np.float32,
                }
            )
        except Exception:
            continue

        # Drop corrupted rows
        df = df[df["time_sec"] > 0].reset_index(drop=True)
        if len(df) == 0:
            continue

        # Tag every row with metadata
        df["class_name"]   = trial["class_name"]
        df["trial_id"]     = trial["trial_id"]
        df["split"]        = trial["split"]
        df["cpu_type"]     = trial["cpu_type"]
        df["ram_spec"]     = trial["ram_spec"]
        df["label"]        = trial["label"]
        df["is_malicious"] = trial["is_malicious"]

        batch.append(df)
        del df
        gc.collect()

        # Write batch to parquet when full
        if len(batch) >= BATCH_SIZE:
            batch_df = pd.concat(batch, ignore_index=True)
            table    = pa.Table.from_pandas(batch_df)

            if writer is None:
                writer = pq.ParquetWriter(out_path, table.schema,
                                          compression="snappy")
            writer.write_table(table)

            total_rows += len(batch_df)
            batch_num  += 1

            if batch_num % 5 == 0:
                pct = (list(trials_df.index).index(i) + 1) / len(trials_df) * 100
                print(f"    batch {batch_num:>3} | "
                      f"{total_rows:>12,} rows | "
                      f"{pct:5.1f}% done", end="\r")

            del batch_df, table
            batch = []
            gc.collect()

    # Write remaining trials
    if batch:
        batch_df = pd.concat(batch, ignore_index=True)
        table    = pa.Table.from_pandas(batch_df)
        if writer is None:
            writer = pq.ParquetWriter(out_path, table.schema,
                                      compression="snappy")
        writer.write_table(table)
        total_rows += len(batch_df)
        del batch_df, table
        batch = []
        gc.collect()

    if writer:
        writer.close()
        writer = None

    mb = os.path.getsize(out_path) / (1024*1024)
    print(f"  {ft:<20} done — {total_rows:>12,} rows  |  {mb:.0f} MB     ")

print("\nAll file types saved!")

# =============================================================================
# STEP 3 — QUICK VERIFICATION
# Just check what got saved and basic sanity check on entropy
# =============================================================================

print("\n\nSTEP 3 — Verification\n")
print(f"{'File':<35}  {'Size (MB)':>10}  {'Rows':>12}  {'Classes':>8}")
print("-" * 70)

for ft in CSV_FILES:
    path = os.path.join(PROCESSED_PATH, f"{ft}_combined.parquet")
    if not os.path.exists(path):
        print(f"{ft+'_combined.parquet':<35}  NOT FOUND")
        continue

    mb = os.path.getsize(path) / (1024*1024)
    df = pd.read_parquet(path, columns=["class_name", "is_malicious"])
    print(f"  {ft+'_combined.parquet':<33}  {mb:>10.0f}  "
          f"{len(df):>12,}  {df['class_name'].nunique():>8}")
    del df
    gc.collect()

# Entropy sanity check on mem_write
print("\nEntropy check — mem_write (should be higher for malicious classes):\n")

mw = pd.read_parquet(
    os.path.join(PROCESSED_PATH, "mem_write_combined.parquet"),
    columns=["class_name", "label", "entropy"]
)

ent = (mw.groupby(["class_name", "label"])["entropy"]
       .mean()
       .sort_values(ascending=False)
       .reset_index())

ent.columns = ["class_name", "label", "mean_entropy"]
ent["bar"]  = ent["mean_entropy"].apply(lambda x: "█" * int(x * 4))

print(ent.to_string(index=False))

mal_avg = mw[mw["label"] == "malicious"]["entropy"].mean()
ben_avg = mw[mw["label"] == "benign"]["entropy"].mean()

print(f"\nMalicious avg entropy : {mal_avg:.4f}")
print(f"Benign avg entropy    : {ben_avg:.4f}")
print(f"Gap                   : {mal_avg - ben_avg:+.4f}")
print("\nLarger gap = easier for ML models to separate classes")

del mw
gc.collect()

print("\n" + "="*65)
print("  PHASE 1 COMPLETE")
print("  Processed parquet files ready in DATA/processed/")
print("  Next → Phase 2 EDA")
print("="*65)
