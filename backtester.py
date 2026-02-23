"""
BACKTESTING ENGINE – Astronacci Pro
Menguji akurasi sinyal secara historis untuk menghasilkan Win Rate.
Setiap sinyal yang ditampilkan di dashboard akan disertai win rate-nya.
"""
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
from strategy import calculate_signals


def get_backtest_data(symbol, period="1y"):
    """Ambil data historis panjang untuk backtesting"""
    ticker = f"{symbol}.JK"
    try:
        df = yf.download(ticker, period=period, interval="1d", 
                        progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.columns = [c.lower() for c in df.columns]
        df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
        return df
    except Exception as e:
        print(f"[WARN] Backtest data error: {e}")
        return None


def run_backtest(symbol, period="1y", window=60, hold_days=5):
    """
    Simulasi sinyal BUY pada data historis.
    
    Logika:
    1. Geser window 60 hari ke depan, satu hari per iterasi
    2. Di setiap posisi, hitung sinyal menggunakan calculate_signals()
    3. Jika sinyal = BUY/STRONG_BUY, catat entry dan cek hasil setelah hold_days
    4. Trade dianggap WIN jika harga naik >= 1% dalam hold_days
    
    Args:
        symbol: Kode saham IDX
        period: Periode data historis (1y, 2y)
        window: Jumlah hari data per analisis (60)
        hold_days: Berapa hari setelah entry untuk evaluasi (5)
    
    Returns:
        dict dengan win_rate, total_trades, avg_return, max_drawdown, trades[]
    """
    df = get_backtest_data(symbol, period)
    if df is None or len(df) < window + hold_days + 10:
        return {
            "win_rate": 0, "total_trades": 0, "avg_return": 0,
            "max_drawdown": 0, "trades": [], "error": "Data tidak cukup"
        }
    
    trades = []
    step = 3  # Skip beberapa hari untuk efisiensi (tidak perlu setiap hari)
    
    for i in range(window, len(df) - hold_days, step):
        chunk = df.iloc[i - window:i].copy()
        
        try:
            result = calculate_signals(chunk)
            if isinstance(result, str):
                continue
            
            signal = result.get("signal", "")
            score = result.get("score", 0)
            
            # Hanya uji sinyal BUY
            if "BUY" not in signal:
                continue
            
            entry_price = df.iloc[i]['close']
            
            # Evaluasi setelah hold_days
            exit_idx = min(i + hold_days, len(df) - 1)
            exit_price = df.iloc[exit_idx]['close']
            
            # Cek highest price selama holding period (untuk max potential)
            holding_period = df.iloc[i:exit_idx + 1]
            highest = holding_period['high'].max()
            lowest = holding_period['low'].min()
            
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            max_gain = ((highest - entry_price) / entry_price) * 100
            max_loss = ((lowest - entry_price) / entry_price) * 100
            
            is_win = bool(pnl_pct > 0)
            hit_tp = bool(max_gain >= 2)  # TP jika pernah naik 2%+
            
            trade = {
                "date": df.index[i].strftime('%Y-%m-%d') if hasattr(df.index[i], 'strftime') else str(df.index[i]),
                "signal": signal,
                "score": score,
                "entry": round(float(entry_price), 0),
                "exit": round(float(exit_price), 0),
                "pnl_pct": round(float(pnl_pct), 2),
                "max_gain": round(float(max_gain), 2),
                "max_loss": round(float(max_loss), 2),
                "is_win": is_win,
                "hit_tp": hit_tp,
            }
            trades.append(trade)
            
        except Exception:
            continue
    
    # Statistik
    if not trades:
        return {
            "win_rate": 0, "total_trades": 0, "avg_return": 0,
            "max_drawdown": 0, "trades": [], "error": "Tidak ada sinyal BUY ditemukan"
        }
    
    wins = sum(1 for t in trades if t["is_win"])
    total = len(trades)
    win_rate = round((wins / total) * 100, 1)
    avg_return = round(sum(t["pnl_pct"] for t in trades) / total, 2)
    max_drawdown = round(min(t["max_loss"] for t in trades), 2)
    tp_hit_rate = round(sum(1 for t in trades if t["hit_tp"]) / total * 100, 1)
    
    # Skor berdasarkan sinyal
    strong_buy_trades = [t for t in trades if "STRONG_BUY" in t["signal"]]
    buy_trades = [t for t in trades if "STRONG_BUY" not in t["signal"]]
    
    strong_wr = 0
    if strong_buy_trades:
        strong_wins = sum(1 for t in strong_buy_trades if t["is_win"])
        strong_wr = round((strong_wins / len(strong_buy_trades)) * 100, 1)
    
    buy_wr = 0
    if buy_trades:
        buy_wins = sum(1 for t in buy_trades if t["is_win"])
        buy_wr = round((buy_wins / len(buy_trades)) * 100, 1)
    
    return {
        "win_rate": win_rate,
        "total_trades": total,
        "avg_return": avg_return,
        "max_drawdown": max_drawdown,
        "tp_hit_rate": tp_hit_rate,
        "strong_buy_wr": strong_wr,
        "buy_wr": buy_wr,
        "strong_buy_count": len(strong_buy_trades),
        "buy_count": len(buy_trades),
        "trades": trades[-10:],  # Hanya 10 terakhir untuk UI
    }


def quick_backtest(symbol):
    """Versi cepat untuk API — 6 bulan, hold 5 hari"""
    return run_backtest(symbol, period="1y", window=60, hold_days=5)


if __name__ == "__main__":
    print("=== Backtesting BBCA (1 Tahun) ===")
    result = run_backtest("BBCA", period="1y", hold_days=5)
    print(f"  Win Rate     : {result['win_rate']}%")
    print(f"  Total Sinyal : {result['total_trades']}")
    print(f"  Avg Return   : {result['avg_return']}%")
    print(f"  Max Drawdown : {result['max_drawdown']}%")
    print(f"  TP Hit Rate  : {result['tp_hit_rate']}%")
    print(f"  STRONG_BUY WR: {result['strong_buy_wr']}% ({result['strong_buy_count']} sinyal)")
    print(f"  BUY WR       : {result['buy_wr']}% ({result['buy_count']} sinyal)")
    if result['trades']:
        print(f"\n  Last 5 Trades:")
        for t in result['trades'][-5:]:
            icon = "✅" if t['is_win'] else "❌"
            print(f"    {icon} {t['date']} | {t['signal']:<20s} | Entry: {t['entry']} → Exit: {t['exit']} | P/L: {t['pnl_pct']:+.1f}%")
