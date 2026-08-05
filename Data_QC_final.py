# Import libraries
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
from IPython.display import display

#========================================================================================
# Step 1: Unzip the files
# Unzip file
file_path = "/content/data_v3.zip"
file_output = "/content"

!unzip {file_path} -d {file_output}

#========================================================================================
# Step 2: Store Datasets as a dictionary

# Path to folder containing CSV files
data_folder = Path("/content/data_v3")

# Store datasets
datasets = {}

# Function to clean column names
def clean_columns(df):
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w]+", "_", regex=True)
        .str.replace(r"_+", "_", regex=True)
        .str.strip("_")
    )
    return df

#========================================================================================
#Step 3: Print a per-column data-quality summary

# Read and process each CSV
for file in data_folder.glob("*.csv"):

    name = file.stem

    # Read CSV
    df = pd.read_csv(file)

    # Clean columns
    df = clean_columns(df)

    # Store dataframe
    datasets[name] = df

    print("=" * 80)
    print(f"Dataset: {name}")
    print(f"Rows: {df.shape[0]:,}")
    print(f"Columns: {df.shape[1]}")

    # Create column summary table
    column_info = pd.DataFrame({
        "Column": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Missing Values": df.isna().sum().values,
        "Duplicate Values": [
          df[col].duplicated().sum()
          for col in df.columns
      ],
        "Duplicate (%)": [
        round((df[col].duplicated().sum() / len(df)) * 100, 2)
        for col in df.columns
    ]
  })
    display(column_info)

#========================================================================================
# Step 4: Pivot selected long-format tables into wide format

# Retrieve tables from the datasets dictionary
pft = datasets["pft"].copy()
vitals = datasets["vitals"].copy()
lab_report = datasets["lab_report"].copy()

# ------------------------------------------------------------
# 1. Pulmonary Function Tests (PFT)

pft_wide = (
    pft.pivot_table(
        index=["case_number", "pft_dts"],
        columns="name",
        values="ord_value",
        aggfunc="first"
    )
    .reset_index()
)
pft_wide = clean_columns(pft_wide)

# ------------------------------------------------------------
# 2. Vitals

vitals_wide = (
    vitals.pivot_table(
        index=["reg_id", "date"],
        columns="vital_type_name_category",
        values="vital_value",
        aggfunc="first"
    )
    .reset_index()
)
vitals_wide = clean_columns(vitals_wide)

print("=" * 80)

# ------------------------------------------------------------
# 3. Lab Reports

lab_report["value"] = pd.to_numeric(
    lab_report["value"],
    errors="coerce"
)

lab_report_wide = (
    lab_report.pivot_table(
        index=["reg_id", "order_date"],
        columns="component_name",
        values="value",
        aggfunc="first"
    )
    .reset_index()
)
lab_report_wide = clean_columns(lab_report_wide)

print("=" * 80)

#========================================================================================
# Step 5: Summary of pivoted tables
from IPython.display import display, Markdown

pivoted_tables = {
    "PFT": pft_wide,
    "Vitals": vitals_wide,
    "Lab Reports": lab_report_wide
}
for name, df in pivoted_tables.items():

    print("=" * 80)
    print(f"{name} Dataset")
    print(f"Rows: {df.shape[0]:,}")
    print(f"Columns: {df.shape[1]}")

    # Create quality summary table
    summary = pd.DataFrame({
        "Column": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Missing Values": df.isna().sum().values,
        "Missing (%)": (
            (df.isna().mean() * 100)
            .round(2)
            .values
        ),
        "Duplicate Values": [
            df[col].duplicated().sum()
            for col in df.columns
        ],
        "Duplicate (%)": [
            round(
                (df[col].duplicated().sum() / len(df)) * 100,
                2
            )
            for col in df.columns
        ]
    })

    display(summary.style.hide(axis="index"))

#========================================================================================
# Step 6: Generate Relationship Summary Table

relationships = []

tables = list(datasets.keys())

for i in range(len(tables)):
    for j in range(i + 1, len(tables)):

        table1 = tables[i]
        table2 = tables[j]

        df1 = datasets[table1]
        df2 = datasets[table2]

        # Find common columns
        common_cols = set(df1.columns).intersection(df2.columns)

        for col in common_cols:

            # Focus on identifier columns
            if (
                "id" in col.lower()
                or "case" in col.lower()
                or "number" in col.lower()
            ):

                # Determine relationship type
                table1_unique = df1[col].is_unique
                table2_unique = df2[col].is_unique

                if table1_unique and table2_unique:
                    relationship = "One-to-One"

                elif table1_unique and not table2_unique:
                    relationship = "One-to-Many"

                elif not table1_unique and table2_unique:
                    relationship = "One-to-Many"

                else:
                    relationship = "Many-to-Many"

                relationships.append({
                    "Table 1": table1,
                    "Table 2": table2,
                    "Relationship Key": col,
                    "Relationship Type": relationship
                })

# Print relatiosnhip summary
# Create summary dataframe
relationship_summary = pd.DataFrame(relationships)

# Remove duplicate relationships if any
relationship_summary = relationship_summary.drop_duplicates()

display(relationship_summary)

#===============================================================================
# Step 7: Change to common identifier and date column names

# Identify possible ID column names
id_columns = [
    "case_number",
    "study_code",
    "patient_id",
    "subject_id",
    "participant_id",
    "case_id",
    "record_id"
]

# Identify possible date column names
date_columns = [
    "date",
    "visit_date",
    "collection_date",
    "record_date",
    "test_date",
    "encounter_date",
    "assessment_date",
    "sample_date"
]

# Rename matching columns to common names
for name, df in datasets.items():
    rename_dict = {}

    # Rename identifier column
    for col in df.columns:
        if col.lower() in id_columns:
            rename_dict[col] = "reg_id"

    # Rename date column
    for col in df.columns:
        if col.lower() in date_columns:
            rename_dict[col] = "date_recorded"

    # Apply renaming
    if rename_dict:
        df.rename(columns=rename_dict, inplace=True)
        print(f"{name}: {rename_dict}")
#======================================================================================================
Step 8: Export cleaned datasets

output_folder = Path("cleaned_datasets")
output_folder.mkdir(exist_ok=True)

# Save original datasets
for name, df in datasets.items():
    df.to_csv(output_folder / f"{name}.csv", index=False)

# Save pivoted datasets
pft_wide.to_csv(output_folder / "pft_wide.csv", index=False)
vitals_wide.to_csv(output_folder / "vitals_wide.csv", index=False)
lab_report_wide.to_csv(output_folder / "lab_report_wide.csv", index=False)

print("All datasets saved successfully.")

#==============================================================================================================

