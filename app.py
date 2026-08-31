import streamlit as st
import pandas as pd
from pathlib import Path

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Dairy Membership & Movement Analytics Dashboard",
    page_icon="🥛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------
# CUSTOM CSS
# -------------------------------------------------
st.markdown("""
<style>
.stApp { background-color: #f8fafc; }
section[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
}
div[data-testid="stMetric"] {
    background: white;
    padding: 18px 20px;
    border-radius: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
div[data-testid="stMetric"] label {
    color: #64748b !important;
    font-size: 0.82rem !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    color: #0f172a !important;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# STATUS LOGIC (clean version matching working DAX)
# -------------------------------------------------
def add_member_status(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # Normalize Member No
    df["Member No"] = pd.to_numeric(df["Member No"], errors="coerce")

    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12,
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
        "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
        "June 2026": 6, "July 2026": 7, "Aug 2026": 8, "August 2026": 8,
        "June": 6, "July": 7, "Aug": 8, "August": 8,
    }

    def get_month_num(val):
        val = str(val).strip()
        if val in month_map:
            return month_map[val]
        first = val.split()[0] if val else ""
        return month_map.get(first, 0)

    df["Month Number"] = df["Month"].apply(get_month_num)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").fillna(2026).astype(int)

    EXCEPTIONAL = {53830, 53891, 60961}

    # Pre-compute members + max per period (excluding exceptional numbers)
    period_info = {}
    for (y, m), group in df.groupby(["Year", "Month Number"]):
        members = set(group["Member No"].dropna().unique())
        valid = group[~group["Member No"].isin(EXCEPTIONAL)]
        prev_max = valid["Member No"].max() if not valid.empty else 0
        period_info[(int(y), int(m))] = {"members": members, "max": prev_max}

    def get_status(row):
        mno = row["Member No"]
        if pd.isna(mno) or mno in EXCEPTIONAL:
            return None

        y = int(row["Year"])
        m = int(row["Month Number"])

        if m == 1:
            prev_y, prev_m = y - 1, 12
        else:
            prev_y, prev_m = y, m - 1

        prev = period_info.get((prev_y, prev_m), {"members": set(), "max": 0})
        in_prev = mno in prev["members"]
        prev_max = prev["max"]

        if (not in_prev) and (mno > prev_max):
            return "🆕 Newly Joined"
        elif in_prev:
            return "🔄 Continuing"
        elif (not in_prev) and (mno < prev_max):
            return "🔄 Resumed"
        return None

    # Status for members present in the current month
    df["Status"] = df.apply(get_status, axis=1)

    # Add Stopped members (present in previous month but missing in current)
    stopped_rows = []
    periods = sorted(period_info.keys())
    for i in range(1, len(periods)):
        curr = periods[i]
        prev = periods[i - 1]

        is_consecutive = (
            (curr[0] == prev[0] and curr[1] == prev[1] + 1) or
            (curr[0] == prev[0] + 1 and prev[1] == 12 and curr[1] == 1)
        )
        if not is_consecutive:
            continue

        stopped = period_info[prev]["members"] - period_info[curr]["members"] - EXCEPTIONAL
        for smno in stopped:
            mask = (
                (df["Year"] == prev[0]) &
                (df["Month Number"] == prev[1]) &
                (df["Member No"] == smno)
            )
            if mask.any():
                row = df[mask].iloc[0].copy()
                row["Status"] = "🛑 Stopped"
                stopped_rows.append(row)

    if stopped_rows:
        df = pd.concat([df, pd.DataFrame(stopped_rows)], ignore_index=True)

    return df

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------
EXCEL_PATH = Path("Member Trend(FY26).xlsx")

@st.cache_data
def load_data():
    register = pd.read_excel(EXCEL_PATH, sheet_name="Register")
    register.columns = [str(c).strip() for c in register.columns]

    # Fix DoB – this prevents the ArrowTypeError
    if "DoB" in register.columns:
        register["DoB"] = pd.to_datetime(register["DoB"], errors="coerce", dayfirst=True)

    monthly_sheets = ["June26", "July26", "Aug26"]
    frames = []
    for sheet in monthly_sheets:
        try:
            temp = pd.read_excel(EXCEL_PATH, sheet_name=sheet)
            temp.columns = [str(c).strip() for c in temp.columns]
            frames.append(temp)
        except Exception:
            pass

    mps = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    mps = add_member_status(mps)
    return register, mps

register_df, mps_df = load_data()

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.title("🥛 Membership Analytics")
page = st.sidebar.radio(
    "Select Workspace",
    ["Overview", "Mps", "Register"],
    label_visibility="collapsed"
)

# -------------------------------------------------
# FILTER OPTIONS
# -------------------------------------------------
all_routes = sorted(mps_df["Route"].dropna().unique().tolist()) if not mps_df.empty else []
months = ["All Months"] + sorted(mps_df["Month"].dropna().unique().tolist()) if not mps_df.empty else ["All Months"]
statuses = ["All Status"] + sorted([s for s in mps_df["Status"].dropna().unique().tolist() if s]) if not mps_df.empty else ["All Status"]

# -------------------------------------------------
# OVERVIEW PAGE
# -------------------------------------------------
if page == "Overview":
    st.title("📊 Member Monthly Status Summary")
    st.caption("FY2025/2026 Active Membership Analysis")

    # ========== FILTERS ==========
    st.markdown("### Filters")

    col_a, col_b = st.columns([4, 1])
    with col_a:
        selected_routes = st.multiselect(
            "Select Route(s)",
            options=all_routes,
            default=[],
            placeholder="Choose routes...",
            key="route_filter"
        )
    with col_b:
        st.write("")
        st.write("")
        if st.button("Select All Routes", use_container_width=True):
            st.session_state["route_filter"] = all_routes
            st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        selected_month = st.selectbox("Select Month", months, key="month_filter")
    with col2:
        selected_status = st.selectbox("Select Status", statuses, key="status_filter")
    with col3:
        genders = ["All Genders"]
        if not register_df.empty and "Gender" in register_df.columns:
            genders += sorted(register_df["Gender"].dropna().astype(str).unique().tolist())
        selected_gender = st.selectbox("Select Gender", genders, key="gender_filter")

    st.markdown("---")

    # ========== APPLY FILTERS ==========
    filtered = mps_df.copy()

    if selected_routes:
        filtered = filtered[filtered["Route"].isin(selected_routes)]

    if selected_month != "All Months":
        filtered = filtered[filtered["Month"] == selected_month]

    if selected_status != "All Status":
        filtered = filtered[filtered["Status"] == selected_status]

    # Join with Register
    reg = register_df.copy()
    reg.columns = [str(c).strip() for c in reg.columns]

    filtered["Member No"] = pd.to_numeric(filtered["Member No"], errors="coerce")
    reg["Member No"] = pd.to_numeric(reg["Member No"], errors="coerce")

    merge_cols = ["Member No"]
    for col in ["Gender", "DoB", "Contact"]:
        if col in reg.columns:
            merge_cols.append(col)

    merged = filtered.merge(reg[merge_cols], on="Member No", how="left")

    if "DoB" in merged.columns:
        merged["DoB"] = pd.to_datetime(merged["DoB"], errors="coerce")

    if selected_gender != "All Genders" and "Gender" in merged.columns:
        merged = merged[merged["Gender"].astype(str) == selected_gender]

    # ========== TOP KPIs ==========
    max_mps_member = int(mps_df["Member No"].max()) if not mps_df.empty else 0
    max_reg_member = int(register_df["Member No"].max()) if not register_df.empty else 0

    continuing = merged[merged["Status"] == "🔄 Continuing"]["Member No"].nunique()
    resuming   = merged[merged["Status"] == "🔄 Resumed"]["Member No"].nunique()
    newly      = merged[merged["Status"] == "🆕 Newly Joined"]["Member No"].nunique()
    stopped    = merged[merged["Status"] == "🛑 Stopped"]["Member No"].nunique() if "🛑 Stopped" in merged["Status"].values else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Max MPS Member No", f"{max_mps_member:,}")
    with k2:
        st.metric("Max Register Member No", f"{max_reg_member:,}")
    with k3:
        st.metric("Continuing Members", f"{continuing:,}")
    with k4:
        st.metric("Resuming Members", f"{resuming:,}")
    with k5:
        st.metric("Exceptional Members", "3")

    # ========== STATUS SUMMARY CARDS ==========
    st.markdown("##### Status Breakdown")
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.metric("🆕 Newly Joined", f"{newly:,}")
    with s2:
        st.metric("🔄 Continuing", f"{continuing:,}")
    with s3:
        st.metric("🔄 Resumed", f"{resuming:,}")
    with s4:
        st.metric("🛑 Stopped", f"{stopped:,}")

    st.markdown("---")

    # ========== MAIN TABLE ==========
    st.subheader("Active Members – Financial Year 2025/2026")

    if merged.empty:
        st.info("No data for the selected filters. Try selecting routes or changing filters.")
    else:
        display_cols = [
            "Member No", "Member", "Route", "Gender", "DoB", "Contact",
            "Total", "Status", "Month", "Year"
        ]
        display_cols = [c for c in display_cols if c in merged.columns]

        table = merged[display_cols].copy()
        if "Total" in table.columns:
            table = table.rename(columns={"Total": "Total (Ltrs)"})

        st.dataframe(
            table.sort_values("Member No"),
            use_container_width=True,
            height=500,
            hide_index=True
        )

        total_vol = merged["Total"].sum() if "Total" in merged.columns else 0
        st.markdown(f"### **Total Volume: {total_vol:,.2f} Ltrs**")

# -------------------------------------------------
# MPS PAGE
# -------------------------------------------------
elif page == "Mps":
    st.title("📈 Member Deliveries (MPS)")
    st.dataframe(mps_df, use_container_width=True, height=520, hide_index=True)

    if not mps_df.empty:
        csv = mps_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download MPS Data",
            data=csv,
            file_name="mps_with_status.csv",
            mime="text/csv"
        )

# -------------------------------------------------
# REGISTER PAGE
# -------------------------------------------------
elif page == "Register":
    st.title("📋 Full Member Register Database")

    search = st.text_input("🔍 Search by Member Name or Number")
    reg = register_df.copy()

    if search:
        reg = reg[
            reg.astype(str).apply(
                lambda x: x.str.contains(search, case=False, na=False)
            ).any(axis=1)
        ]

    st.dataframe(reg, use_container_width=True, height=520, hide_index=True)

    if not reg.empty:
        csv = reg.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Download Register",
            data=csv,
            file_name="member_register.csv",
            mime="text/csv"
        )