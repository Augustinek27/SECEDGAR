import os
import json
import pandas as pd
import mysql.connector
from dotenv import load_dotenv


# MySQL Database Configuration
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'capstone_financials')
}

FOLDER_NAME = "EDGARClient/JSON_FILES"

def extract_annual_metric(us_gaap, tags_list):
    """Parses year and values reliably across SEC EDGAR JSON formats."""
    for tag in tags_list:
        if tag in us_gaap:
            units = us_gaap[tag].get("units", {})
            for unit_key in units.keys():
                raw_entries = units[unit_key]
                yearly_data = {}
                for entry in raw_entries:
                    form = entry.get("form", "")
                    fp = entry.get("fp", "")
                    
                    if form == "10-K" or fp == "FY":
                        year = None
                        if "fy" in entry and entry["fy"]:
                            year = int(entry["fy"])
                        elif "frame" in entry and len(entry["frame"]) >= 6 and "CY" in entry["frame"]:
                            try:
                                year = int(entry["frame"][2:6])
                            except ValueError:
                                pass
                        
                        if year and "val" in entry:
                            yearly_data[year] = entry["val"]
                            
                if yearly_data:
                    return yearly_data
    return {}

def pipe_dataframe_to_mysql(df, ticker):
    """Safely commits processed metrics into the MySQL database."""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        insert_query = """
        INSERT INTO company_metrics (
            ticker, year, revenue_billions, net_income_billions, 
            op_margin_percent, net_margin_percent, roic_proxy_percent, 
            current_ratio, debt_to_equity, interest_coverage
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            revenue_billions = VALUES(revenue_billions),
            net_income_billions = VALUES(net_income_billions),
            op_margin_percent = VALUES(op_margin_percent),
            net_margin_percent = VALUES(net_margin_percent),
            roic_proxy_percent = VALUES(roic_proxy_percent),
            current_ratio = VALUES(current_ratio),
            debt_to_equity = VALUES(debt_to_equity),
            interest_coverage = VALUES(interest_coverage);
        """

        for _, row in df.iterrows():
            data_tuple = (
                ticker,
                int(row["Year"]),
                None if pd.isna(row.get("Revenue ($B)")) else float(row["Revenue ($B)"]),
                None if pd.isna(row.get("Net Income ($B)")) else float(row["Net Income ($B)"]),
                None if pd.isna(row.get("Op Margin (%)")) else float(row["Op Margin (%)"]),
                None if pd.isna(row.get("Net Margin (%)")) else float(row["Net Margin (%)"]),
                None if pd.isna(row.get("ROIC Proxy (%)")) else float(row["ROIC Proxy (%)"]),
                None if pd.isna(row.get("Current Ratio")) else float(row["Current Ratio"]),
                None if pd.isna(row.get("Debt-to-Equity")) else float(row["Debt-to-Equity"]),
                None if pd.isna(row.get("Interest Coverage")) else float(row["Interest Coverage"])
            )
            cursor.execute(insert_query, data_tuple)

        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ MySQL Sync Complete: {ticker} records stored securely.")

    except mysql.connector.Error as err:
        print(f"❌ MySQL Database Error: {err}")

def process_ticker_history(ticker):
    """Processes local JSON facts and injects a 10-year matrix into MySQL."""
    filename = os.path.join(FOLDER_NAME, f"{ticker}_facts.json")
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        return

    with open(filename, "r") as f:
        data = json.load(f)
        
    if "facts" not in data or "us-gaap" not in data["facts"]:
        print(f"❌ Invalid SEC JSON payload structure for {ticker}.")
        return

    us_gaap = data["facts"]["us-gaap"]
    
    tags_map = {
        "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "Revenues", "RegulatedAndUnregulatedOperatingRevenues"],
        "net_income": ["NetIncomeLoss", "ProfitLoss"],
        "operating_income": ["OperatingIncomeLoss"],
        "current_assets": ["AssetsCurrent"],
        "current_liabilities": ["LiabilitiesCurrent"],
        "total_liabilities": ["Liabilities"],
        "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
        "interest_expense": ["InterestExpense", "InterestAndDebtExpense"]
    }
    
    extracted_data = {name: extract_annual_metric(us_gaap, tags) for name, tags in tags_map.items()}
    all_years = sorted(list(set([y for metric in extracted_data.values() for y in metric.keys()])))
    
    if not all_years:
        print(f"⚠️ Warning: No annual years could be parsed from SEC facts for {ticker}.")
        return

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
        
        processed_records.append({
            "Year": int(year),
            "Revenue ($B)": round(rev / 1_000_000_000, 2) if rev is not None else None,
            "Net Income ($B)": round(net_inc / 1_000_000_000, 2) if net_inc is not None else None,
            "Op Margin (%)": round((op_inc / rev) * 100, 2) if (op_inc and rev) else None,
            "Net Margin (%)": round((net_inc / rev) * 100, 2) if (net_inc and rev) else None,
            "ROIC Proxy (%)": round((net_inc / eq) * 100, 2) if (net_inc and eq) else None,
            "Current Ratio": round(curr_assets / curr_liab, 2) if (curr_assets and curr_liab) else None,
            "Debt-to-Equity": round(tot_liab / eq, 2) if (tot_liab and eq) else None,
            "Interest Coverage": round(op_inc / interest, 2) if (op_inc and interest and interest != 0) else None
        })
        
    df = pd.DataFrame(processed_records).tail(10)
    pipe_dataframe_to_mysql(df, ticker)
