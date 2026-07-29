import json
import os
import time
import requests

# Create the directory path name
folder_name = "EDGARClient/JSON_FILES"
os.makedirs(folder_name, exist_ok=True) # Ensures folder exists out of the box

headers = {
    'User-Agent': 'CapstoneApp/1.0 (karl.augustine@student.csuglobal.edu)'
}

# =====================================================================
# MASTER MAP DOWNLOAD (Run once at startup)
# =====================================================================
print("Step 1: Fetching master ticker map from www.sec.gov...")
map_url = "https://www.sec.gov/files/company_tickers.json"
map_response = requests.get(map_url, headers=headers)

if map_response.status_code == 200:
    ticker_map = map_response.json()
    print("🎯 Master ticker map loaded successfully.")
else:
    print("❌ Failed to download master map.")
    ticker_map = None

# =====================================================================
# OPTIMIZED MULTI-TICKER PULL FUNCTION
# =====================================================================
def download_sec_json(target_ticker):
    """Downloads and saves SEC facts for a given ticker using the pre-loaded map."""
    if not ticker_map:
        print(f"❌ Cannot process {target_ticker}: Master map unavailable.")
        return False
        
    target_ticker = target_ticker.upper()
    filename = os.path.join(folder_name, f"{target_ticker}_facts.json")
    
    # Optimization: If we already have the data locally, skip the network hit!
    if os.path.exists(filename):
        print(f"ℹ️ {target_ticker} local file already exists. Skipping download.")
        return True

    print(f"\nLooking up CIK for '{target_ticker}'...")
    padded_cik = None
    for key, info in ticker_map.items():
        if info['ticker'] == target_ticker:
            padded_cik = str(info['cik_str']).zfill(10)
            break
            
    if padded_cik:
        print(f"🎯 Found CIK: {padded_cik}")
        facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded_cik}.json"
        print(f"Fetching financial facts from {facts_url}...")
        
        # Enforce SEC rate-limiting safety gap (0.2 seconds minimum)
        time.sleep(0.2) 
        facts_response = requests.get(facts_url, headers=headers)
        
        if facts_response.status_code == 200:
            company_facts = facts_response.json()
            
            print(f"Saving raw data directly to {filename}...")
            with open(filename, "w") as f:
                json.dump(company_facts, f, indent=4)
                
            print(f"🚀 SUCCESS! {target_ticker} data safely tucked away!")
            return True
        else:
            print(f"❌ Failed to pull facts payload for {target_ticker}. Status: {facts_response.status_code}")
            return False
    else:
        print(f"❌ Ticker '{target_ticker}' not found in SEC master map.")
        return False

# =====================================================================
# BATCH EXECUTION TESTING BLOCK
# =====================================================================
if __name__ == "__main__":
    # Test your new loop capability here
    test_watchlist = ["NVDA", "AMZN", "MU"]
    
    print(f"\n🎬 Starting batch download for: {test_watchlist}")
    for ticker in test_watchlist:
        download_sec_json(ticker)
    print("\n🏁 Batch processing cycle complete.")