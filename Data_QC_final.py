# Step 1: Import new cleaned dataset
# Path to cleaned dataset folder
cleaned_folder = Path("cleaned_datasets")

# Dictionary to store cleaned datasets
cleaned_datasets = {}

# Load all CSV files
for file in cleaned_folder.glob("*.csv"):
    
    df = pd.read_csv(file)
    
    # Store using filename (without .csv) as key
    cleaned_datasets[file.stem] = df

print("Loaded datasets:")
print(cleaned_datasets.keys())

#=====================================================================================
Step 2: 
demographics = cleaned_datasets["demographics"]
antibodies = cleaned_datasets["antibodies"]
mrss = cleaned_datasets["mrss"]
bal = cleaned_datasets["bal"]
medications = cleaned_datasets["medications"]

pft_wide = cleaned_datasets["pft_wide"]
vitals_wide = cleaned_datasets["vitals_wide"]
lab_report_wide = cleaned_datasets["lab_report_wide"]

ssc_subtype = cleaned_datasets["ssc_subtype"]
skin_biopsies = cleaned_datasets["skin_biopsies"]
libraries = cleaned_datasets["libraries"]
