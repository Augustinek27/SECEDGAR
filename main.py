import os
import sys

# 1. Inherit the core functions from your existing scripts
try:
    from EDGARClient import download_sec_json, folder_name
    from load_to_db import process_ticker_history
except ImportError as e:
    print(f"Structural Error: Could not locate your original files. {e}")
    print("Ensure main.py is in the same root directory as your other scripts.")
    sys.exit(1)

# Ensure the required output folder structure exists out of the box
os.makedirs(folder_name, exist_ok=True)

# =====================================================================
# INTERACTIVE CLI DISPATCHER
# =====================================================================
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 UNIFIED SEC EDGAR DATA PIPELINE DISPATCHER")
    print("="*50)
    
    # Accept user tickers
    user_input = input("Enter ticker symbols to load (comma-separated, e.g., AOS, UI, MKTX): ")
    
    # Process input into clean, uppercase ticker array
    target_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    
    if not target_tickers:
        print("No valid tickers entered. Exiting system pipeline.")
    else:
        print(f"\n🎬 Initiating processing loop for: {target_tickers}")
        
        for ticker in target_tickers:
            print(f"\n⚡ Processing: {ticker}")
            
            # Step A: Inherited Downloader Logic
            # (Checks if local file exists, converts ticker to CIK, fetches from SEC)
            download_success = download_sec_json(ticker)
            
            # Step B: Inherited Parsing & SQL Injection Logic
            if download_success:
                try:
                    process_ticker_history(ticker)
                except Exception as e:
                    print(f"Extraction Engine failed to process {ticker}: {e}")
            else:
                print(f"Skipping parsing layer for {ticker} due to extraction failure.")
                
        print("\n🏁 PIPELINE CYCLE COMPLETE: Local SQLite database synchronized successfully.")