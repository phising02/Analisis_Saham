import yfinance as yf
import json

def debug_unhealthy(symbol):
    ticker = f"{symbol}.JK"
    print(f"--- DEBUGGING {symbol} ---")
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        # Key metrics for health check
        metrics = {
            "Symbol": symbol,
            "Price": info.get("currentPrice"),
            "Market Cap": info.get("marketCap"),
            "ROE": info.get("returnOnEquity"),
            "PBV": info.get("priceToBook"),
            "Total Debt": info.get("totalDebt"),
            "Total Cash": info.get("totalCash"),
            "Total Revenue": info.get("totalRevenue"),
            "Gross Profits": info.get("grossProfits"),
            "Net Income": info.get("netIncomeToCommon"),
            "Debt/Equity": info.get("debtToEquity"),
            "Operating Margin": info.get("operatingMargins"),
            "Book Value": info.get("bookValue"),
            "Financial Currency": info.get("financialCurrency")
        }
        
        print(json.dumps(metrics, indent=4))
        
        if metrics["Book Value"] and metrics["Book Value"] < 0:
            print(f"!!! ALERT: {symbol} has NEGATIVE EQUITY (Book Value < 0)")
            
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")

if __name__ == "__main__":
    debug_unhealthy("ALTO")
    debug_unhealthy("BUKA") # Another small cap to compare
