import streamlit as st
import pandas as pd
from modules.erp_connector import fetch_erp_data
from modules.processing import build_member_master_table

st.set_page_config(
    page_title="Membership & Production Analytics",
    page_icon="🥛",
    layout="wide"
)

st.title("📊 Dairy Membership & Movement Analytics Dashboard")
st.markdown("Automated ERP integration mirroring your Power BI logic.")

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Data Management")
if st.sidebar.button("🔄 Fetch & Parse from ERP", type="primary"):
    with st.spinner("Syncing Register and MPS tables from ERP..."):
        reg_df, mps_df = fetch_erp_data()
        master_df = build_member_master_table(reg_df, mps_df)
        
        if not master_df.empty:
            st.session_state['master_df'] = master_df
            st.success("Data successfully synchronized and parsed!")
        else:
            st.warning("No data returned from ERP sources.")

# --- DASHBOARD VIEW ---
if 'master_df' in st.session_state:
    df = st.session_state['master_df']

    # KPI Metrics Summary Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Members", f"{len(df):,}")
    with col2:
        st.metric("Total Volume (Ltrs)", f"{df['total'].sum():,.2f}")
    with col3:
        st.metric("Continuing", f"{len(df[df['status'].str.contains('Continuing')]):,}")
    with col4:
        st.metric("Resumed", f"{len(df[df['status'].str.contains('Resumed')]):,}")
    with col5:
        st.metric("Stopped", f"{len(df[df['status'].str.contains('Stopped')]):,}")

    st.markdown("---")

    # Filters (Slicers)
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filters")
    
    routes = sorted(df['route'].dropna().unique().tolist()) if 'route' in df.columns else []
    selected_routes = st.sidebar.multiselect("Select Route(s)", routes, default=routes[:5] if routes else [])

    statuses = sorted(df['status'].dropna().unique().tolist()) if 'status' in df.columns else []
    selected_statuses = st.sidebar.multiselect("Select Status", statuses, default=statuses)

    # Filter dataframe
    filtered_df = df.copy()
    if selected_routes and 'route' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['route'].isin(selected_routes)]
    if selected_statuses and 'status' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]

    # Main Interactive Data Table & Reports
    st.subheader("📋 Member Master & Movement Report")
    st.dataframe(filtered_df, use_container_width=True)

    # Download Report Button
    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Report as CSV",
        data=csv_data,
        file_name="membership_movement_report.csv",
        mime="text/csv"
    )
else:
    st.info("👈 Click **'Fetch & Parse from ERP'** in the sidebar to load your master table and reports.")