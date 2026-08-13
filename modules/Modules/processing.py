import pandas as pd
import numpy as np

def build_member_master_table(register_df: pd.DataFrame, mps_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merges Register and MPS tables and calculates precise membership statuses:
    1: 🆕 Newly Joined
    2: 🔄 Resumed
    3: 🛑 Stopped
    4: 🔄 Continuing
    """
    if register_df.empty or mps_df.empty:
        return pd.DataFrame()

    # Standardize column names (lowercase, no spaces)
    register_df.columns = [c.strip().lower().replace(" ", "_") for c in register_df.columns]
    mps_df.columns = [c.strip().lower().replace(" ", "_") for c in mps_df.columns]

    # Clean member numbers
    register_df['member_no'] = pd.to_numeric(register_df['member_no'], errors='coerce')
    mps_df['member_no'] = pd.to_numeric(mps_df['member_no'], errors='coerce')

    # Define exception IDs to ignore when evaluating newly joined max thresholds
    ignored_exceptions = [53830, 53891, 60961]

    # Find the last member number in the register (ignoring exceptions)
    valid_register_nos = register_df[~register_df['member_no'].isin(ignored_exceptions)]['member_no']
    last_member_no = valid_register_nos.max() if not valid_register_nos.empty else 0

    # Full outer join to create the unified Member Master Table
    master_df = pd.merge(
        register_df,
        mps_df[['member_no', 'total']],
        on='member_no',
        how='outer',
        suffixes=('', '_mps')
    )

    # Fill missing values for total production
    master_df['total'] = pd.to_numeric(master_df['total'], errors='coerce').fillna(0.0)

    # Boolean flags for condition checks
    in_register = master_df['member_no'].isin(register_df['member_no'])
    in_mps = master_df['member_no'].isin(mps_df['member_no'])
    is_above_last = master_df['member_no'] > last_member_no
    is_below_last = master_df['member_no'] < last_member_no
    is_exception = master_df['member_no'].isin(ignored_exceptions)

    # Define the 4 Status Rules
    conditions = [
        # 1. Newly Joined: Member No > last member no OR explicit exception list
        is_exception | is_above_last,
        
        # 2. Resumed: Missing in register, present in MPS, and Member No < last member no
        (~in_register & in_mps & is_below_last),
        
        # 3. Stopped: Present in register, missing in MPS, and Member No < last member no
        (in_register & ~in_mps & is_below_last),
        
        # 4. Continuing: Present in both Register and MPS
        (in_register & in_mps)
    ]

    statuses = [
        "🆕 Newly Joined",
        "🔄 Resumed",
        "🛑 Stopped",
        "🔄 Continuing"
    ]

    master_df['status'] = np.select(conditions, statuses, default="Unknown")

    # Select final requested columns
    output_columns = ["member_no", "member", "route", "gender", "dob", "contact", "total", "status"]
    available_cols = [col for col in output_columns if col in master_df.columns]

    return master_df[available_cols]