import os
import json
import sqlite3
import pandas as pd

# ==========================================
# 1. THE SQLITE PIPELINE CONNECTOR
# ==========================================
def pipe_dataframe_to_sqlite(df, ticker):
    """Safely injects the parsed Pandas dataframe into the SQLite file."""
    db_file = "financials.db"
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Ensure the table matches our exact 8-metric analyst schema
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_metrics (
        ticker TEXT NOT NULL,
        year INTEGER NOT NULL,
        revenue_billions REAL,
        net_income_billions REAL,
        op_margin_percent REAL,
        net_margin_percent REAL,
        roic_proxy_percent REAL,
        current_ratio REAL,
        debt_to_equity REAL,
        interest_coverage REAL,
        PRIMARY KEY (ticker, year)
    );
    """)
    
    # Insert or overwrite existing data to protect against duplicates
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO company_metrics 
            (ticker, year, revenue_billions, net_income_billions, op_margin_percent, 
             net_margin_percent, roic_proxy_percent, current_ratio, debt_to_equity, interest_coverage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker.upper(),
            int(row["Year"]),
            row["Revenue ($B)"],
            row["Net Income ($B)"],
            row["Op Margin (%)"],
            row["Net Margin (%)"],
            row["ROIC Proxy (%)"],
            row["Current Ratio"],
            row["Debt-to-Equity"],
            row["Interest Coverage"]
        ))
        
    conn.commit()
    conn.close()
    print(f"📊 Database Sync Complete: {ticker.upper()} data safely locked into '{db_file}'.")

# ==========================================
# 2. THE CHOSEN HORIZON PARSING ENGINE
# ==========================================
def process_ticker_history(ticker):
    """Processes local JSON facts files into our analyst-ready metric frame."""
    folder_name = "EDGARClient/JSON_FILES"
    target_file = f"{ticker.upper()}_facts.json"
    full_path = os.path.join(folder_name, target_file)
    
    if not os.path.exists(full_path):
        print(f"❌ Error: {full_path} not found. Please pull the file from the SEC directory first.")
        return
        
    with open(full_path, "r") as f:
        data = json.load(f)
        
    us_gaap = data["facts"]["us-gaap"]
    
    tags_map = {
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues"],
        "net_income": ["NetIncomeLoss"],
        "operating_income": ["OperatingIncomeLoss"],
        "current_assets": ["AssetsCurrent"],
        "current_liabilities": ["LiabilitiesCurrent"],
        "total_liabilities": ["Liabilities"],
        "equity": ["StockholdersEquity"],
        "interest_expense": ["InterestExpense", "InterestAndDebtExpense"]
    }
    
    def extract_annual_metric(tags_list):
        for tag in tags_list:
            if tag in us_gaap:
                units = us_gaap[tag].get("units", {})
                for unit_key in units.keys():
                    raw_entries = units[unit_key]
                    yearly_data = {}
                    for entry in raw_entries:
                        if entry.get("form") == "10-K":
                            year = None
                            if "frame" in entry and len(entry["frame"]) == 6 and entry["frame"].startswith("CY"):
                                year = int(entry["frame"][2:])
                            elif "fy" in entry:
                                year = int(entry["fy"])
                            if year:
                                yearly_data[year] = entry["val"]
                    if yearly_data:
                        return yearly_data
        return {}

    extracted_data = {}
    for metric_name, tags in tags_map.items():
        extracted_data[metric_name] = extract_annual_metric(tags)
        
    all_years = sorted(list(set([y for metric in extracted_data.values() for y in metric.keys()])))
    processed_records = []
    
    for year in all_years:
        rev = extracted_data["revenue"].get(year)
        net_inc = extracted_data["net_income"].get(year)
        op_inc = extracted_data["operating_income"].get(year)
        curr_assets = extracted_data["current_assets"].get(year)
        curr_liab = extracted_data["current_liabilities"].get(year)
        tot_liab = extracted_data["total_liabilities"].get(year)
        eq = extracted_data["equity"].get(year)
        interest = extracted_data["interest_expense"].get(year)
        
        op_margin = (op_inc / rev) * 100 if (op_inc and rev) else None
        net_margin = (net_inc / rev) * 100 if (net_inc and rev) else None
        roic_proxy = (net_inc / eq) * 100 if (net_inc and eq) else None
        current_ratio = (curr_assets / curr_liab) if (curr_assets and curr_liab) else None
        debt_to_equity = (tot_liab / eq) if (tot_liab and eq) else None
        interest_coverage = (op_inc / interest) if (op_inc and interest and interest != 0) else None
        
        processed_records.append({
            "Year": year,
            "Revenue ($B)": round(rev / 1_000_000_000, 2) if rev else None,
            "Net Income ($B)": round(net_inc / 1_000_000_000, 2) if net_inc else None,
            "Op Margin (%)": round(op_margin, 2) if op_margin else None,
            "Net Margin (%)": round(net_margin, 2) if net_margin else None,
            "ROIC Proxy (%)": round(roic_proxy, 2) if roic_proxy else None,
            "Current Ratio": round(current_ratio, 2) if current_ratio else None,
            "Debt-to-Equity": round(debt_to_equity, 2) if debt_to_equity else None,
            "Interest Coverage": round(interest_coverage, 2) if interest_coverage else None
        })
        
    df = pd.DataFrame(processed_records)
    final_df = df.dropna(subset=["Revenue ($B)", "Net Income ($B)"]).tail(10)
    
    # Send it to the database table!
    pipe_dataframe_to_sqlite(final_df, ticker)

# ==========================================
# 3. LOADER EXECUTION RUNNER
# ==========================================
if __name__ == "__main__":
    # Test your engine by looping through your current active local tracking files
    target_tickers = ["NVDA", "AMZN", "MU"]  # Add any other tickers you have locally inside JSON_FILES here!
    
    print("🚀 Initiating Bulk Pipeline SEC Database Load...")
    for ticker in target_tickers:
        process_ticker_history(ticker)