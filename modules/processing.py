import pandas as pd

def add_member_status(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'Status' column based on the Power BI DAX logic.
    Expects columns: Member No, Month, Year, Total
    """
    if df.empty:
        return df

    df = df.copy()

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Create a helper Month Number
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12,
        "June 2026": 6, "July 2026": 7, "Aug 2026": 8, "August 2026": 8
    }

    # Try to extract month number
    def get_month_num(val):
        val = str(val).strip()
        if val in month_map:
            return month_map[val]
        # fallback: try first word
        first = val.split()[0] if val else ""
        return month_map.get(first, 0)

    df["Month Number"] = df["Month"].apply(get_month_num)
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce").fillna(2026).astype(int)

    # We will calculate status month by month
    status_list = []

    # Unique year-month combinations sorted
    periods = df[["Year", "Month Number"]].drop_duplicates().sort_values(["Year", "Month Number"])

    for _, row in periods.iterrows():
        y = int(row["Year"])
        m = int(row["Month Number"])

        current = df[(df["Year"] == y) & (df["Month Number"] == m)].copy()

        # Previous month
        if m == 1:
            prev_m, prev_y = 12, y - 1
        else:
            prev_m, prev_y = m - 1, y

        prev = df[(df["Year"] == prev_y) & (df["Month Number"] == prev_m)]

        prev_members = set(prev["Member No"].dropna().unique()) if not prev.empty else set()
        prev_max = prev["Member No"].max() if not prev.empty else 0

        def get_status(mno):
            if pd.isna(mno):
                return None
            # Special exclusions from your DAX
            if mno in {53830, 53891, 60961}:
                return None

            in_prev = mno in prev_members
            in_curr = True   # we are already in current month rows

            if not in_prev and in_curr and mno > prev_max:
                return "🆕 Newly Joined"
            elif in_prev and in_curr:
                return "🔄 Continuing"
            elif not in_prev and in_curr and mno < prev_max:
                return "🔄 Resumed"
            elif in_prev and not in_curr:
                return "🛑 Stopped"
            else:
                return None

        current["Status"] = current["Member No"].apply(get_status)
        status_list.append(current)

    result = pd.concat(status_list, ignore_index=True)
    return result