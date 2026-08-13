import pandas as pd
import numpy as np

def build_member_master_table(reg_df, mps_df):
    """
    Passes through the raw ERP delivery data directly while enriching 
    it with human-readable Month labels and mapping portal columns.
    """
    if mps_df is None or mps_df.empty:
        return pd.DataFrame()

    df = mps_df.copy()
    
    # Standardize column names (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]

    # Map month numbers to readable Month labels if available
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April", 
        5: "May", 6: "June", 7: "July", 8: "August", 
        9: "September", 10: "October", 11: "November", 12: "December"
    }

    if 'Month' not in df.columns and 'Month Number' in df.columns:
        df['Month'] = df['Month Number'].map(month_names)

    return df