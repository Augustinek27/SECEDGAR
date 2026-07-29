import os
import sqlite3
import pandas as pd
import streamlit as st

# Inherit your beautifully modular backend functions
try:
    from EDGARClient import download_sec_json
    from load_to_db import process_ticker_history
except ImportError as e:
    st.error(f"Structural Layout Error: Missing core scripts. {e}")
    st.stop()

DB_FILE = "financials.db"

# Page configuration
st.set_page_config(page_title="SEC EDGAR Pipeline Portal", page_icon="📈", layout="centered")

# =====================================================================
# HELPER DATA LAYER
# =====================================================================
def get_existing_tickers():
    """Reads the local SQLite database and returns a list of unique tickers already stored."""
    if not os.path.exists(DB_FILE):
        return []
    try:
        conn = sqlite3.connect(DB_FILE)
        # Fetch unique tickers stored in our relational primary keys
        query = "SELECT DISTINCT ticker FROM company_metrics ORDER BY ticker ASC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df["ticker"].tolist()
    except Exception:
        return []

def get_preview_data():
    """Fetches a small sample of the latest database entries to display on screen."""
    if not os.path.exists(DB_FILE):
        return None
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM company_metrics ORDER BY ticker, year DESC", conn)
        conn.close()
        return df
    except Exception:
        return None

# =====================================================================
# WEB INTERFACE LAYOUT
# =====================================================================
st.title("SEC EDGAR Data Pipeline Portal")
st.markdown("Extract raw SEC XBRL corporate payloads, transform financial metrics, and load them directly into your database.")

# 1. Live Inventory Tracker Sidebar
existing_tickers = get_existing_tickers()
with st.sidebar:
    st.header("🗄️ Database Inventory")
    if existing_tickers:
        st.success(f"Tracking {len(existing_tickers)} Companies:")
        # Display as a clean read-only tag system
        st.multiselect("Currently Loaded Tickers", options=existing_tickers, default=existing_tickers, disabled=True)
    else:
        st.info("Database is currently empty or initialized.")

# 2. Interactive Data Ingestion Form
st.subheader("Ingest New Financial Profiles")

with st.form(key="ingest_form", clear_on_submit=True):
    user_input = st.text_input(
        label="Enter Ticker Symbols (comma-separated)", 
        placeholder="e.g., TSLA, AOS, MKTX, UI",
        help="App will automatically cross-reference inventory and skip existing records."
    )
    submit_button = st.form_submit_button(label="Execute ETL Pipeline Loop")

# 3. Execution Pipeline Processing Logic
if submit_button and user_input:
    # Clean up user strings
    raw_tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    
    # Sift out duplicates using our live inventory lookup
    tickers_to_process = [t for t in raw_tickers if t not in existing_tickers]
    skipped_tickers = [t for t in raw_tickers if t in existing_tickers]
    
    # Notify users immediately about skipped assets
    if skipped_tickers:
        st.warning(f"ℹ Skipped: {', '.join(skipped_tickers)} already exist in database storage.")
        
    if not tickers_to_process:
        st.info("No new tickers to process.")
    else:
        st.info(f"🎬 Initiating background processing sequence for: {tickers_to_process}")
        
        # Build a live progress container on screen
        status_box = st.container()
        
        for ticker in tickers_to_process:
            with status_box:
                st.write(f"⚡ Processing **{ticker}**...")
                
                # Step A: Inherited Network Extractor
                download_success = download_sec_json(ticker)
                
                if download_success:
                    try:
                        # Step B: Inherited Transform and Load Engine
                        process_ticker_history(ticker)
                        st.write(f" **{ticker}** parsed and loaded successfully!")
                    except Exception as e:
                        st.error(f" Transformation Layer error on {ticker}: {e}")
                else:
                    st.error(f"Extraction Layer failed for {ticker}.")
        
        st.success("🏁 Pipeline routine completed successfully!")
        # Force rerun to update our dynamic inventory lists instantly
        st.rerun()

# 4. Live Database Visualizer Grid
st.subheader("Relational Database Preview")
preview_df = get_preview_data()

if preview_df is not None and not preview_df.empty:
    st.dataframe(preview_df, use_container_width=True, hide_index=True)
else:
    st.info("No records to preview. Use the ingest engine above to pull data down from the SEC.")