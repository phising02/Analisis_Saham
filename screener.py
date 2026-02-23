import yfinance as yf
import pandas as pd
import time
from strategy import calculate_signals
from database import save_screener_result, init_db
from telegram_bot import broadcast_signal

import json
import os

# Load semua saham dari JSON jika tersedia, jika tidak gunakan fallback
TICKER_FILE = "idx_tickers.json"
if os.path.exists(TICKER_FILE):
    with open(TICKER_FILE, "r") as f:
        LQ45_SYMBOLS = json.load(f)
else:
    # Fallback (Top active stocks as before)
    LQ45_SYMBOLS = [
        "ADRO", "AKRA", "AMRT", "ANTM", "ASII", "BBCA", "BBNI", "BBRI", "BBTN", "BMRI",
        "BRIS", "BRPT", "BUKA", "CPIN", "EMTK", "ESSA", "GOTO", "HRUM", "ICBP", "INCO",
        "INDF", "INKP", "INTP", "ITMG", "KLBF", "MAPI", "MBMA", "MDKA", "MEDC", "MIKA",
        "PTBA", "SQR", "TLKM", "TOWR", "TPIA", "UNTR", "UNVR", "WIFI",
        "ADMR", "AMMN", "AUTO", "AVIA", "BBYB", "BCIC", "BDMN", "BEBS", "BELI", "BFIN",
        "BIRD", "BKSL", "BNGA", "BNII", "BNLI", "BSDE", "BTPS", "CARE", "CARS", "CEKA",
        "CLEO", "CNMA", "CTRA", "DART", "DGIK", "DMAS", "DOID", "DSNG", "DYAN", "ELSA",
        "ELTY", "ENRG", "ERAA", "EXCL", "FREN", "GGRM", "HEAL", "HMSP", "IMAS", "INDY",
        "IPTV", "ISAT", "JKON", "JPFA", "JRPT", "JSMR", "KAEF", "KIJA", "KINO", "KPIG",
        "LPKR", "LPPF", "MAIN", "MAPA", "MARK", "MCAS", "META", "MLIA", "MLPL", "MNCN",
        "MPPA", "MPRO", "MSKY", "MYOR", "NATO", "NFCX", "PADI", "PANR", "PANS", "PBAW",
        "PBNI", "PBRX", "PBSA", "PEHA", "PGAS", "PGUN", "PJAW", "PJAA", "PNLF", "PPRO",
        "PRAS", "PSAB", "PSDN", "PSKT", "PTPP", "PWON", "RAJA", "RALS", "RMKE", "ROTI",
        "SAME", "SCMA", "SIDO", "SILO", "SIMP", "SMDR", "SMGR", "SMRA", "SMSM", "SOBI",
        "SPMA", "SRIL", "SSMS", "TARA", "TAYS", "TBIG", "TELE", "TINS", "TKIM", "TMAS",
        "TOPS", "TOTL", "TOWR", "TRAM", "TRIM", "TRIS", "TRUE", "ULTJ", "UNIT", "VICO",
        "VIVA", "VOKS", "WAPO", "WEGE", "WICO", "WIDI", "WIIM", "WIKA", "WINS", "WIRG",
        "WOOD", "WSBP", "WSKT", "WTON", "YPAS", "ZATA", "ZINC", "ACES", "ARTO", "BULL",
        "CHIP", "CUAN", "FIRE", "HUMI", "KREN", "MBSS", "MITI", "NCKL", "PTPS", "STRK"
    ]

def get_clean_data(symbol):
    ticker = f"{symbol}.JK"
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.columns = [c.lower() for c in df.columns]
        return df
    except Exception:
        return None

def run_screener():
    print(f"--- MEMULAI LQ45 SCREENER ({len(LQ45_SYMBOLS)} SAHAM) ---")
    init_db()
    
    for symbol in LQ45_SYMBOLS:
        print(f"[SCREEN] Memproses {symbol}...", end="", flush=True)
        df = get_clean_data(symbol)
        
        if df is not None:
            try:
                # Analisis menggunakan strategi utama
                res = calculate_signals(df)
                
                # Sederhanakan hasil untuk database
                data_to_save = {
                    'signal': res['signal'],
                    'score': res['score'],
                    'buy_price': res['buy_price'],
                    'sell_target': res['sell_target'],
                    'stop_loss': res['stop_loss']
                }
                
                save_screener_result(symbol, data_to_save)
                print(f" Done! Sinyal: {res['signal']} ({res['score']})")
                
                # Kirim Alert Telegram jika skor tinggi (>= 70) dan sinyal BUY
                if res['score'] >= 70 and "BUY" in res['signal']:
                    broadcast_signal(symbol, data_to_save)
            except Exception as e:
                print(f" Error: {e}")
        else:
            print(" Gagal ambil data.")
        
        # Jeda agar tidak terkena rate limit Yahoo Finance
        time.sleep(1)

    print("--- SCREENER SELESAI ---")

if __name__ == "__main__":
    run_screener()
