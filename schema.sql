CREATE DATABASE IF NOT EXISTS capstone_financials;
USE capstone_financials;

CREATE TABLE IF NOT EXISTS company_metrics (
    ticker VARCHAR(10) NOT NULL,
    year INT NOT NULL,
    revenue_billions DECIMAL(12, 2),
    net_income_billions DECIMAL(12, 2),
    op_margin_percent DECIMAL(8, 2),
    net_margin_percent DECIMAL(8, 2),
    roic_proxy_percent DECIMAL(8, 2),
    current_ratio DECIMAL(8, 2),
    debt_to_equity DECIMAL(8, 2),
    interest_coverage DECIMAL(8, 2),
    PRIMARY KEY (ticker, year)
);
