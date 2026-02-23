import yfinance as yf
import pandas as pd
from multibagger_strategy import calculate_multibagger_signals
from multibagger_screener import get_ticker_info

def case_study(symbol):
    print(f"\n=== CASE STUDY: {symbol} ===")
    ticker = f"{symbol}.JK"
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.columns = [c.lower() for c in df.columns]
        
        fund = get_ticker_info(symbol)
        res = calculate_multibagger_signals(df, symbol, fundamental=fund)
        
        print(f"Signal: {res['signal']} (Score: {res['score']})")
        print(f"Base Building: {'YES' if res.get('is_base') else 'NO'}")
        print(f"Dist from Low: {res.get('dist_low', 0)}%")
        print("Scoring Details:")
        for p in res['patterns']:
            print(f" - {p}")
            
        print("\nFundamental Metrics used:")
        print(f" - PBV: {fund.get('pbv_ratio')}")
        print(f" - PER: {fund.get('pe_ratio')}")
        print(f" - ROE: {fund.get('roe')}")
        print(f" - Debt/Equity: {fund.get('debt_to_equity')}")
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")

if __name__ == "__main__":
    # 1. PTRO: Value + Conglomerate (Prajogo Pangestu)
    case_study("PTRO")
    # 2. CUAN: High Growth/Hype (Prajogo Pangestu)
    case_study("CUAN")
    # 3. BBNI: Big Cap for baseline
    case_study("BBNI")
