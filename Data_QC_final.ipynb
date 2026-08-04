# Import libraries
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
from IPython.display import display

# Unzip file
file_path = "/content/data_v3.zip"
file_output = "/content"

!unzip {file_path} -d {file_output}

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

# print a per-column data-quality summary
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
