import yfinance as yf
import pandas as pd
import time
from multibagger_strategy import calculate_multibagger_signals
from database import save_screener_result, init_db
from telegram_bot import broadcast_signal

import json
import os

# Load semua saham dari JSON jika tersedia, jika tidak gunakan fallback
TICKER_FILE = "idx_tickers.json"
if os.path.exists(TICKER_FILE):
    with open(TICKER_FILE, "r") as f:
        MULTIBAGGER_POOL = json.load(f)
else:
    # Fallback jika file tidak ditemukan
    MULTIBAGGER_POOL = [
        "ELSA", "ENRG", "MEDC", "RAJA", "RMKE", "ADMR", "DOID", "WINS", "SGER",
        "GOTO", "BUKA", "WIRG", "MCAS", "NFCX", "MTDL", "BELI",
        "AMRT", "MPPA", "LPPF", "RALS", "ACES", "MAPI", "MAPA",
        "BSDE", "PWON", "SMRA", "CTRA", "ASRI", "PTPP", "WIKA", "ADHI", "JKON",
        "BRIS", "BTPS", "BBYB", "BVIC", "BABP", "ARTO", "AGRO", "DNAR",
        "WIFI", "CLEO", "VOKS", "SMDR", "FILM", "WOOD", "PBSA", "RAAM", "HEAL",
        "SIDO", "TLKM", "EXCL", "ISAT", "ADRO", "ITMG", "PTBA", "UNTR"
    ]

def get_ticker_info(symbol):
    """Ambil info fundamental esensial berbasis kriteria akurat (Lynch/O'Neil/LKH)"""
    ticker = f"{symbol}.JK"
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "pbv_ratio": info.get("priceToBook"),
            "pe_ratio": info.get("trailingPE"),
            "market_cap": info.get("marketCap"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "earnings_growth": info.get("earningsGrowth"),
            "revenue_growth": info.get("revenueGrowth"),
            "dividend_yield": info.get("dividendYield"),
            "operating_margins": info.get("operatingMargins")
        }
    except Exception:
        return {}

def run_multibagger_screener():
    print(f"--- MEMULAI MULTIBAGGER SCREENER ({len(MULTIBAGGER_POOL)} SAHAM) ---")
    init_db()
    
    for symbol in MULTIBAGGER_POOL:
        print(f"[MB-SCAN] Memproses {symbol}...", end="", flush=True)
        ticker = f"{symbol}.JK"
        try:
            # 1. Download data harian (6 bulan untuk base building detection)
            df = yf.download(ticker, period="6mo", interval="1d", progress=False, auto_adjust=True)
            
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                df.columns = [c.lower() for c in df.columns]
                
                # 2. Ambil data fundamental (esensial untuk multibagger)
                fund = get_ticker_info(symbol)
                
                # 3. Analisis menggunakan strategi Multibagger
                res = calculate_multibagger_signals(df, symbol, fundamental=fund)
                
                if res:
                    # 4. Simpan ke database dengan scanner_type = 'MULTIBAGGER'
                    data_to_save = {
                        'signal': res['signal'],
                        'score': res['score'],
                        'buy_price': res['buy_price'],
                        'sell_target': res['sell_target'],
                        'stop_loss': res['stop_loss']
                    }
                    
                    save_screener_result(symbol, data_to_save, scanner_type='MULTIBAGGER')
                    print(f" Done! Sinyal: {res['signal']} ({res['score']})")
                    
                    # 5. Notifikasi Telegram jika skor tinggi (>= 65)
                    # Multibagger threshold sedikit lebih rendah (65) karena kriteria lebih ketat
                    if res['score'] >= 65:
                        # Modifikasi broadcast untuk label Multibagger
                        res_copy = data_to_save.copy()
                        res_copy['signal'] = "🚀 MULTIBAGGER: " + res['signal']
                        broadcast_signal(symbol, res_copy)
                else:
                    print(" Gagal analisis.")
            else:
                print(" Gagal ambil data.")
        except Exception as e:
            print(f" Error: {e}")
        
        # Jeda 1 detik agar tidak terkena rate limit
        time.sleep(1)

    print("--- MULTIBAGGER SCREENER SELESAI ---")

if __name__ == "__main__":
    run_multibagger_screener()
