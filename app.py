import streamlit as st
import pandas as pd
from modules.erp_connector import fetch_erp_data

st.set_page_config(
    page_title="Dairy Membership & Movement Analytics Dashboard",
    page_icon="🥛",
    layout="wide"
)

# --- SIDEBAR NAVIGATION & FILTERS ---
st.sidebar.title("Membership Trend and Analytics")
page = st.sidebar.radio("Select Workspace", ["Overview", "Mps", "Register"])

st.sidebar.markdown("---")
st.sidebar.header("Data Parameters")

# Sidebar filter selectors
route_options = ["All Routes", "R001", "R002", "R003", "R004", "R005", "R006", 
                 "R007", "R008", "R009", "R010", "R011", "NYATHUNA"]
selected_route = st.sidebar.selectbox("Select Route", route_options)

months_list = ["January", "February", "March", "April", "May", "June", 
               "July", "August", "September", "October", "November", "December"]
selected_month = st.sidebar.selectbox("Select Month", months_list, index=7)  # Default August

selected_year = st.sidebar.number_input("Year", value=2026, step=1)

st.sidebar.markdown("---")
st.sidebar.header("Data Management")

if st.sidebar.button("🚀 Fetch & Parse Portal Data", type="primary"):
    with st.spinner("Authenticating and syncing Register & Delivery records from ERP portal..."):
        
        # Force Jan 1 → Aug 31 2026 (or use selected month if you prefer)
        reg_df, mps_df = fetch_erp_data(
            selected_route=selected_route,
            start_date="2026-01-01",
            end_date="2026-08-31",          # whole of August
            selected_month=None,            # ignore single month for full range
            year=selected_year,
            username="martha",
            password="Analyst26",
            companyid="1"
        )
        
        if not reg_df.empty or not mps_df.empty:
            st.session_state['reg_df'] = reg_df
            st.session_state['mps_df'] = mps_df
            st.success(f"Data synchronized successfully! Delivery rows: {len(mps_df):,}")
        else:
            st.warning("No data returned from ERP sources. Check login credentials or portal reachability.")

# --- SHARED DATA CHECK ---
if 'mps_df' in st.session_state or 'reg_df' in st.session_state:
    df = st.session_state.get('mps_df', pd.DataFrame())
    reg_df = st.session_state.get('reg_df', pd.DataFrame())

    # ================= PAGE 1: OVERVIEW =================
    if page == "Overview":
        st.title("📊 Dairy Member Delivery & Collection Overview")

        filtered_df = df.copy()
        
        if not filtered_df.empty:
            # Optional extra filtering (if you later store month per row)
            if selected_route != "All Routes" and 'Route' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['Route'] == selected_route]

        total_members = filtered_df['Member No'].nunique() if not filtered_df.empty and 'Member No' in filtered_df.columns else 0
        total_vol = filtered_df['Total'].sum() if not filtered_df.empty and 'Total' in filtered_df.columns else 0.0

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Total Active Members", f"{total_members:,}")
        with kpi2:
            st.metric("Total Volume (Ltrs)", f"{total_vol:,.2f}")
        with kpi3:
            st.metric("Selected Period", "Jan – Aug 2026")

        st.markdown("---")
        st.subheader(f"Delivery Details for Route: {selected_route} | Period: Jan – Aug {selected_year}")
        st.dataframe(filtered_df, use_container_width=True, height=500)

    # ================= PAGE 2: MPS (MEMBER DELIVERIES) =================
    elif page == "Mps":
        st.title("📈 Member Deliveries (MPS)")
        st.subheader("Performance Records (Jan – Aug 2026)")
        st.dataframe(df, use_container_width=True, height=500)

        if not df.empty:
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download MPS Data (CSV)",
                data=csv_data,
                file_name=f"mps_deliveries_{selected_route}_{selected_year}.csv",
                mime="text/csv"
            )

    # ================= PAGE 3: REGISTER =================
    elif page == "Register":
        st.title("📋 Full Member Register Database")
        st.markdown("Master directory of registered dairy members fetched directly from the portal.")
        
        search_query = st.text_input("🔍 Search Register by Member Name or Number", "")
        reg_filtered = reg_df.copy() if not reg_df.empty else pd.DataFrame()
        
        if search_query and not reg_filtered.empty:
            reg_filtered = reg_filtered[
                reg_filtered.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
            ]
        
        st.dataframe(reg_filtered, use_container_width=True, height=500)

        if not reg_filtered.empty:
            csv_data = reg_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Member Register CSV",
                data=csv_data,
                file_name="member_register_export.csv",
                mime="text/csv"
            )

else:
    st.title("📊 Dairy Membership & Movement Analytics Dashboard")
    st.info("👈 Set your route and period filters in the sidebar, then click **'Fetch & Parse Portal Data'** to load records.")