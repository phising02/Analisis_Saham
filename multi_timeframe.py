"""
MULTI-TIMEFRAME CONFLUENCE ANALYZER
Memeriksa sinyal di Daily, Weekly, dan Monthly timeframe.
Semakin banyak timeframe yang setuju → semakin tinggi kepercayaan sinyal.
"""
import yfinance as yf
import pandas as pd
import pandas_ta as ta


def get_timeframe_data(symbol):
    """Ambil data dari 3 timeframe sekaligus"""
    ticker = f"{symbol}.JK"
    frames = {}
    
    configs = [
        ("daily", "6mo", "1d"),
        ("weekly", "2y", "1wk"),
        ("monthly", "5y", "1mo"),
    ]
    
    for name, period, interval in configs:
        try:
            df = yf.download(ticker, period=period, interval=interval, 
                           progress=False, auto_adjust=True)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                df.columns = [c.lower() for c in df.columns]
                df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
                if len(df) >= 21:
                    frames[name] = df
        except Exception as e:
            print(f"[WARN] MTF {name}: {e}")
    
    return frames


def analyze_timeframe(df):
    """Analisis trend di satu timeframe"""
    if len(df) < 21:
        return {"trend": "UNKNOWN", "strength": 0, "rsi": 50}
    
    # EMA
    ema9 = ta.ema(df['close'], length=9)
    ema21 = ta.ema(df['close'], length=21)
    rsi = ta.rsi(df['close'], length=14)
    
    last_close = df['close'].iloc[-1]
    last_ema9 = ema9.iloc[-1] if ema9 is not None else last_close
    last_ema21 = ema21.iloc[-1] if ema21 is not None else last_close
    last_rsi = rsi.iloc[-1] if rsi is not None and not pd.isna(rsi.iloc[-1]) else 50
    
    # Trend determination
    if last_ema9 > last_ema21 and last_close > last_ema9:
        trend = "BULLISH"
        strength = 2
    elif last_ema9 > last_ema21:
        trend = "BULLISH"
        strength = 1
    elif last_ema9 < last_ema21 and last_close < last_ema9:
        trend = "BEARISH"
        strength = -2
    elif last_ema9 < last_ema21:
        trend = "BEARISH"
        strength = -1
    else:
        trend = "NEUTRAL"
        strength = 0
    
    return {
        "trend": trend,
        "strength": strength,
        "rsi": round(float(last_rsi), 1),
        "ema9": round(float(last_ema9), 0),
        "ema21": round(float(last_ema21), 0),
        "close": round(float(last_close), 0),
    }


def calculate_confluence(symbol):
    """
    Hitung Multi-Timeframe Confluence Score.
    
    Returns dict:
        daily, weekly, monthly: trend analysis per timeframe
        confluence_score: 0-100 (semakin tinggi = semakin setuju semua TF)
        confluence_label: "Strong", "Moderate", "Weak", "Conflicting"
    """
    frames = get_timeframe_data(symbol)
    
    if not frames:
        return {
            "daily": {"trend": "N/A", "strength": 0, "rsi": 50},
            "weekly": {"trend": "N/A", "strength": 0, "rsi": 50},
            "monthly": {"trend": "N/A", "strength": 0, "rsi": 50},
            "confluence_score": 50,
            "confluence_label": "Data Tidak Tersedia",
        }
    
    results = {}
    for tf_name in ["daily", "weekly", "monthly"]:
        if tf_name in frames:
            results[tf_name] = analyze_timeframe(frames[tf_name])
        else:
            results[tf_name] = {"trend": "N/A", "strength": 0, "rsi": 50}
    
    # Confluence calculation
    trends = []
    for tf in ["daily", "weekly", "monthly"]:
        if results[tf]["trend"] != "N/A":
            trends.append(results[tf]["strength"])
    
    if not trends:
        score = 50
    else:
        # Semua bullish → 100, semua bearish → 0, campuran → 50-ish
        avg_strength = sum(trends) / len(trends)  # range: -2 to +2
        score = int(((avg_strength + 2) / 4) * 100)  # normalize to 0-100
        score = max(0, min(100, score))
    
    # Label
    bullish_count = sum(1 for t in trends if t > 0)
    bearish_count = sum(1 for t in trends if t < 0)
    total = len(trends)
    
    if bullish_count == total:
        label = "Strong Bullish ✅"
    elif bearish_count == total:
        label = "Strong Bearish 🔴"
    elif bullish_count > bearish_count:
        label = "Moderate Bullish ⚡"
    elif bearish_count > bullish_count:
        label = "Moderate Bearish ⚠️"
    else:
        label = "Mixed/Conflicting ↔️"
    
    return {
        "daily": results.get("daily", {}),
        "weekly": results.get("weekly", {}),
        "monthly": results.get("monthly", {}),
        "confluence_score": score,
        "confluence_label": label,
    }


if __name__ == "__main__":
    result = calculate_confluence("BBCA")
    print(f"=== Multi-Timeframe Confluence: BBCA ===")
    for tf in ["daily", "weekly", "monthly"]:
        d = result[tf]
        print(f"  {tf:8s}: {d['trend']:8s} | RSI: {d['rsi']}")
    print(f"  Confluence: {result['confluence_score']}/100 — {result['confluence_label']}")
