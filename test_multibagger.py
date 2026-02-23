import yfinance as yf
import pandas as pd
from multibagger_strategy import calculate_multibagger_signals

def test_multibagger():
    symbol = "ELSA" # Example energy stock often considered cyclical/potential
    print(f"Testing Multibagger Logic for {symbol}...")
    
    ticker = f"{symbol}.JK"
    df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
    
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    df.columns = [c.lower() for c in df.columns]
    
    # Mock fundamental info (Kriteria Multibagger Akurat)
    fund = {
        "pbv_ratio": 0.6,
        "pe_ratio": 5.0,
        "market_cap": 2.5e12, # 2.5T
        "roe": 0.18, # 18% (Lynch/O'Neil target > 15%)
        "earnings_growth": 0.35, # 35% (O'Neil target > 25%)
        "revenue_growth": 0.22, # 22%
        "debt_to_equity": 0.45, # 0.45 (Lynch target < 1.0)
    }
    
    # --- TEST 2: DISTRESSED STOCK (ALTO Scenario) ---
    print("\nTesting DISTRESSED stock (ALTO-like)...")
    distressed_fund = {
        "pbv_ratio": -0.5, # Negative Equity
        "pe_ratio": None,
        "market_cap": 0.5e12,
        "roe": -0.40,
        "earnings_growth": -0.80,
        "debt_to_equity": 15.0, # Huge debt
        "operating_margins": -1.2
    }
    res_bad = calculate_multibagger_signals(df, "ALTO", fundamental=distressed_fund)
    if res_bad:
        print(f"Result for ALTO: {res_bad['signal']} (Score: {res_bad['score']})")
        print(f"Details: {res_bad['patterns']}")

if __name__ == "__main__":
    test_multibagger()
