import sqlite3

# This line creates 'financials.db' if it doesn't exist, or connects to it if it does
conn = sqlite3.connect("financials.db")
cursor = conn.cursor()

print("Connected to SQLite database successfully.")

# Define our structured analyst table
create_table_query = """
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
"""

# Execute and save changes
cursor.execute(create_table_query)
conn.commit()
conn.close()

print("🚀 SUCCESS: 'financials.db' created with a bulletproof analyst schema!")