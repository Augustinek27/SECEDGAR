import os
import json
import pandas as pd

# 1. Folder Setup
folder_name = "EDGARClient/JSON_FILES"  # Update this to match your exact directory!
target_file = "AAPL_facts.json"
full_path = os.path.join(folder_name, target_file)

print(f"Opening {full_path}...")

with open(full_path, "r") as f:
    data = json.load(f)

us_gaap = data["facts"]["us-gaap"]

# 2. Comprehensive CS Fallback Lists for all required primitives
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
    """Robust SEC parser that extracts annual (10-K) milestones using multi-tiered fallbacks."""
    for tag in tags_list:
        if tag in us_gaap:
            units = us_gaap[tag].get("units", {})
            for unit_key in units.keys():
                raw_entries = units[unit_key]
                
                yearly_data = {}
                for entry in raw_entries:
                    if entry.get("form") == "10-K":
                        year = None
                        # Check frame first, fallback to official fiscal year identifier
                        if "frame" in entry and len(entry["frame"]) == 6 and entry["frame"].startswith("CY"):
                            year = int(entry["frame"][2:])
                        elif "fy" in entry:
                            year = int(entry["fy"])
                            
                        if year:
                            yearly_data[year] = entry["val"]
                if yearly_data:
                    return yearly_data
    return {}

# 3. Mass harvest the building blocks
extracted_data = {}
print("Harvesting complete baseline financial parameters...")
for metric_name, tags in tags_map.items():
    extracted_data[metric_name] = extract_annual_metric(tags)

# 4. Consolidate timeline years
all_years = sorted(list(set([y for metric in extracted_data.values() for y in metric.keys()])))
processed_records = []

for year in all_years:
    # Safely pull the base values
    rev = extracted_data["revenue"].get(year)
    net_inc = extracted_data["net_income"].get(year)
    op_inc = extracted_data["operating_income"].get(year)
    curr_assets = extracted_data["current_assets"].get(year)
    curr_liab = extracted_data["current_liabilities"].get(year)
    tot_liab = extracted_data["total_liabilities"].get(year)
    eq = extracted_data["equity"].get(year)
    interest = extracted_data["interest_expense"].get(year)
    
    # 5. The Advanced Analytical Calculation Layer
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

# 6. Construct and display the pristine Data Matrix
df = pd.DataFrame(processed_records)
df_recent = df.dropna(subset=["Revenue ($B)", "Net Income ($B)"]).tail(10)

print("\n🚀 SUCCESS! Financial Analyst Screener Engine Is Online:")
print("=" * 110)
print(df_recent.to_string(index=False))
print("=" * 110)