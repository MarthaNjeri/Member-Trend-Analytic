import pandas as pd
import requests
import datetime
import io
import calendar

def fetch_erp_data(
    selected_route="All Routes",
    start_date=None,
    end_date=None,
    selected_month=None,
    year=2026,
    username="martha",
    password="Analyst26",
    companyid="1"
):
    base_url = "http://161.97.172.189/wisedigits/"
    dairy_base = base_url + "modules/dairy/"
    
    reg_df = pd.DataFrame()
    all_mps_records = []
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })
    
    # ------------------------------------------------------------------
    # 0. LOGIN
    # ------------------------------------------------------------------
    login_url = base_url + "modules/auth/users/login.php"
    login_data = {
        "companyid": companyid,
        "username": username,
        "password": password,
        "action": "Login",
        "doctor": ""
    }
    
    try:
        session.get(login_url, timeout=12)
        session.post(login_url, data=login_data, timeout=15, allow_redirects=True)
        print("✅ Login request sent")
    except Exception as e:
        print("Login error:", e)
    
    # ------------------------------------------------------------------
    # 1. FETCH REGISTER DATA
    # ------------------------------------------------------------------
    try:
        res = session.get(dairy_base + "members/members.php", params={"moduleid": "58"}, timeout=15)
        if res.status_code == 200:
            tables = pd.read_html(io.StringIO(res.text))
            if tables:
                reg_df = tables[0]
                print(f"✅ Register: {len(reg_df)} rows")
    except Exception as e:
        print("Register Fetch Error:", e)
    
    # ------------------------------------------------------------------
    # 2. ROUTE MAPPING + DATE RANGE
    # ------------------------------------------------------------------
    # Map display names → ERP codes
    route_map = {
        "Route 1": "R001", "Route 2": "R002", "Route 3": "R003", "Route 4": "R004",
        "Route 5": "R005", "Route 6": "R006", "Route 7": "R007", "Route 8": "R008",
        "Route 9": "R009", "Route 10": "R010", "Route 11": "R011", "Route 12": "R012",
        "Route 13": "R013", "Route 14": "R014", "Route 15": "R015", "Route 16": "R016",
        "Route 17": "R017", "Route 18": "R018", "Route 19": "R019", "Route 20": "R020",
        "Route 21": "R021", "Route 22": "R022", "Route 23": "R023", "Route 26": "R026",
        "Route 27": "R027", "Route 28": "R028", "Route 29": "R029", "Route 30": "R030",
        "Route 31": "R031", "Route 32": "R032", "Route 33": "R033", "Route 34": "R034",
        "Route 35": "R035", "Route 37": "R037", "Route 38": "R038", "Route 39": "R039",
        "Route 40": "R040", "Route 41": "R041", "Route 42": "R042", "Route 43": "R043",
    }
    
    known_routes = list(route_map.values())
    
    # Decide which routes to fetch
    if selected_route in [None, "", "Select...", "All Routes", "All"]:
        routes_to_fetch = known_routes
    else:
        # Convert "Route 5" → "R005"
        erp_route = route_map.get(selected_route, selected_route)
        routes_to_fetch = [erp_route]
    
    # Date range based on selected month
    if selected_month and selected_month not in ["All", "", None]:
        try:
            m_num = datetime.datetime.strptime(selected_month, "%B").month
            start_date = f"{year}-{m_num:02d}-01"
            last_day = calendar.monthrange(year, m_num)[1]
            end_date = f"{year}-{m_num:02d}-{last_day}"
        except Exception:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
    else:
        start_date = start_date or f"{year}-01-01"
        end_date = end_date or f"{year}-12-31"
    
    print(f"Fetching → Routes: {routes_to_fetch}")
    print(f"Period   → {start_date} to {end_date}")
    
    # ------------------------------------------------------------------
    # 3. FETCH DELIVERY DATA PER ROUTE
    # ------------------------------------------------------------------
    for r in routes_to_fetch:
        params = {
            "type": "4",
            "moduleid": "58",
            "fromdate": start_date,
            "todate": end_date,
            "route": r
        }
        
        try:
            res = session.get(
                dairy_base + "memberdeliverydetails/memberdeliverydetailss.php",
                params=params,
                timeout=30
            )
            
            if res.status_code != 200:
                print(f"❌ {r}: HTTP {res.status_code}")
                continue
            
            if "location.replace" in res.text and "login.php" in res.text:
                print(f"⚠️  {r}: Redirected to login")
                continue
            
            tables = pd.read_html(io.StringIO(res.text))
            
            for t in tables:
                cols = [str(c).upper() for c in t.columns]
                if any("MEMBER NO" in c for c in cols) and any("TOTAL" in c for c in cols):
                    t = t.copy()
                    t["Fetched_Route_Query"] = r
                    all_mps_records.append(t)
                    print(f"✅ {r}: {len(t)} rows")
                    break
            else:
                print(f"⚠️  {r}: No matching table")
                
        except Exception as e:
            print(f"❌ Error on route {r}: {e}")
    
    # ------------------------------------------------------------------
    # 4. CLEAN & RETURN
    # ------------------------------------------------------------------
    if all_mps_records:
        mps_df = pd.concat(all_mps_records, ignore_index=True)
    else:
        mps_df = pd.DataFrame()
        print("❌ No delivery data collected.")
    
    if not mps_df.empty:
        mps_df.columns = [str(c).strip() for c in mps_df.columns]
        
        mapping = {}
        for c in mps_df.columns:
            cu = c.upper()
            if "MEMBER NO" in cu:
                mapping[c] = "Member No"
            elif "MEMBER NAME" in cu or ("MEMBER" in cu and "NO" not in cu):
                mapping[c] = "Member"
            elif cu == "ROUTE":
                mapping[c] = "Route"
            elif cu == "ROUTE NAME":
                mapping[c] = "Route Name"
            elif cu == "TOTAL":
                mapping[c] = "Total"
            elif cu == "AM":
                mapping[c] = "AM"
            elif cu == "PM":
                mapping[c] = "PM"
            elif cu == "PM2":
                mapping[c] = "PM2"
            elif "PREVIOUS" in cu:
                mapping[c] = "Previous Month"
        
        mps_df = mps_df.rename(columns=mapping)
        mps_df = mps_df.loc[:, ~mps_df.columns.duplicated()]
        
        mps_df["Month"] = selected_month if (selected_month and selected_month != "All") else "Full Period"
        mps_df["Year"] = year
        
        keep = [
            "Member No", "Member", "Route", "Route Name",
            "AM", "PM", "PM2", "Total", "Previous Month",
            "Fetched_Route_Query", "Month", "Year"
        ]
        mps_df = mps_df[[c for c in keep if c in mps_df.columns]]
    
    if not reg_df.empty:
        reg_df.columns = [str(c).strip() for c in reg_df.columns]
    
    return reg_df, mps_df