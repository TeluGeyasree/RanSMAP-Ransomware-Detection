import pandas as pd   # pandas: reads and writes tables
import pickle         # pickle: loads your saved feature_cols.pkl

# STEP 1: Load the list of 28 feature column names your model was trained on
with open("MODELS/feature_cols.pkl", "rb") as f:    # "rb" = open the file for reading in binary
    feature_cols = list(pickle.load(f))              # list() makes sure it's a plain Python list

# STEP 2: Load your processed feature table
df = pd.read_parquet("data/processed/features_final_phase3_clean.parquet")
print("Table shape:", df.shape)                      # (rows, columns)

# STEP 3: Safety check: make sure every feature column exists in this table
missing = [c for c in feature_cols if c not in df.columns]   # collects any column names not found
if missing:
    print("These feature columns are missing:", missing)
    print("Columns in this file:", list(df.columns))
    raise SystemExit("Wrong file? Try features_final.parquet instead.")   # stops the script here

# STEP 4: Look for the label column (ransomware vs benign) by common names
label_col = None
for name in ["label", "Label", "is_malicious", "malicious", "class", "class_name", "target"]:
    if name in df.columns:       # the first name that exists in your table wins
        label_col = name
        break
print("Label column found:", label_col)

# STEP 5: Pick ~50 rows
if label_col is not None and df[label_col].nunique() <= 5:
    # Few classes (like 0/1): take up to 25 rows from EACH class so both appear
    parts = []
    for cls in df[label_col].unique():
        rows = df[df[label_col] == cls]                              # all rows of this class
        parts.append(rows.sample(min(len(rows), 25), random_state=42))   # random_state=42 = same pick every run
    sample = pd.concat(parts)                                        # stack the pieces into one table
    print("Class counts in sample:")
    print(sample[label_col].value_counts())                          # how many rows of each class
else:
    # No label column found (or too many classes): plain random 50 rows
    sample = df.sample(50, random_state=42)
    print("Used a plain random sample.")

# STEP 6: Keep ONLY the 28 feature columns (no labels, no IDs), because the app expects just these
sample = sample[feature_cols]

# STEP 7: Save as CSV; index=False stops pandas adding an extra row-number column
sample.to_csv("sample_input.csv", index=False)
print("Saved sample_input.csv with shape:", sample.shape)   # expect (50, 28)