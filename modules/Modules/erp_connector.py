import pandas as pd
from sqlalchemy import create_engine
import streamlit as st

def fetch_erp_data():
    """
    Connects to the ERP database or pulls source data 
    to fetch Register and MPS tables.
    """
    try:
        # Option A: Connect via Streamlit Secrets (for live ERP database)
        # db_url = st.secrets["erp_database"]["url"]
        # engine = create_engine(db_url)
        # register_df = pd.read_sql("SELECT * FROM vw_member_register", con=engine)
        # mps_df = pd.read_sql("SELECT * FROM vw_monthly_production", con=engine)
        
        # Option B: Local development fallback / test CSV load
        register_df = pd.read_csv("data/raw/register.csv")
        mps_df = pd.read_csv("data/raw/mps.csv")
        
        return register_df, mps_df
    except Exception as e:
        st.error(f"Failed to fetch data from ERP source: {e}")
        return pd.DataFrame(), pd.DataFrame()