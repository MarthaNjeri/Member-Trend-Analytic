import pandas as pd

file_path = r"Member Trend(FY26).xlsx"

# Show sheet names
xl = pd.ExcelFile(file_path)
print("Sheets:", xl.sheet_names)

# Show first sheet structure
df = pd.read_excel(file_path, sheet_name=0)
print("\nColumns:", list(df.columns))
print("\nShape:", df.shape)
print("\nFirst 5 rows:")
print(df.head())