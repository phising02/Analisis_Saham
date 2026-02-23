import pandas as pd
import yfinance as yf
import os
from strategy import calculate_signals

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_real_data(symbol, current_price=None):
    """Ambil data historis nyata dari Yahoo Finance (IDX = symbol.JK)"""
    ticker = f"{symbol}.JK"
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 30:
            print(f"   [!] Data tidak cukup dari Yahoo Finance untuk {symbol}.")
            return None
        
        # Flatten MultiIndex columns dari yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.columns = [c.lower() for c in df.columns]
        df = df[['open', 'high', 'low', 'close', 'volume']].copy()
        df.dropna(inplace=True)
        
        if len(df) < 30:
            return None
        
        # Update harga terakhir jika pengguna memasukkan harga terkini
        if current_price:
            df.loc[df.index[-1], 'close'] = current_price
        
        return df
    except Exception as e:
        print(f"   [!] Gagal mengambil data: {e}")
        return None

def make_dummy_df(price):
    """Fallback: buat data estimasi jika Yahoo Finance gagal"""
    import numpy as np
    np.random.seed(42)
    n = 60
    returns = np.random.normal(0, 0.015, n)
    closes = [price]
    for r in returns[:-1]:
        closes.append(closes[-1] * (1 + r))
    closes[-1] = price
    highs = [c * (1 + abs(np.random.normal(0.005, 0.005))) for c in closes]
    lows = [c * (1 - abs(np.random.normal(0.005, 0.005))) for c in closes]
    opens = [closes[i-1] if i > 0 else price for i in range(n)]
    volumes = [int(np.random.uniform(500000, 5000000)) for _ in range(n)]
    return pd.DataFrame({'open': opens, 'high': highs, 'low': lows,
                         'close': closes, 'volume': volumes})

def score_bar(score, max_score=100, width=20):
    """Buat visual bar skor"""
    filled = int((score / max_score) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {score}/{max_score}"

def signal_assistant():
    clear_screen()
    print("=" * 65)
    print("     ╔═══════════════════════════════════════════════╗")
    print("     ║   STOCKBIT SIGNAL ASSISTANT – ASTRONACCI PRO  ║")
    print("     ╚═══════════════════════════════════════════════╝")
    print("=" * 65)
    print(" Input: KODE HARGA   (contoh: INET 412)")
    print(" Cukup ketik KODE saja untuk harga penutupan terakhir.")
    print(" Ketik 'exit' untuk keluar.")
    print("-" * 65)

    while True:
        try:
            user_input = input("\n [?] Input: ").strip().upper()
            if user_input == 'EXIT':
                print("\n Sampai jumpa, semoga profit konsisten! 💰")
                break

            parts = user_input.split()
            if len(parts) < 1 or len(parts) > 2:
                print(" [!] Format: SIMBOL atau SIMBOL HARGA")
                continue

            symbol = parts[0]
            price = float(parts[1]) if len(parts) == 2 else None

            print(f"\n [*] Mengambil data {symbol} dari Yahoo Finance...")
            df = get_real_data(symbol, price)
            
            if df is None:
                if price is None:
                    print(" [!] Data tidak tersedia. Coba: SIMBOL HARGA (e.g. INET 412)")
                    continue
                print(f" [>] Menggunakan estimasi volatilitas untuk {symbol}...")
                df = make_dummy_df(price)

            analysis = calculate_signals(df)

            if isinstance(analysis, str):
                print(f" [!] {analysis}")
                continue

            a = analysis  # shorthand
            current_price = a['current_price']

            # ADX Label
            adx_val = a['adx']
            adx_label = "Kuat" if adx_val > 25 else ("Sedang" if adx_val > 15 else "Lemah")

            # Stochastic Label
            stoch_label = "Oversold" if a['stoch_k'] < 20 else ("Overbought" if a['stoch_k'] > 80 else "Normal")

            # RR Label
            rr = a['rr_ratio']
            rr_label = "Baik ✓" if rr >= 2 else ("Cukup" if rr >= 1 else "Buruk ✗")

            # Output
            print()
            print("╔" + "═" * 63 + "╗")
            print(f"║  HASIL ANALISIS: {symbol:45s} ║")
            print("╠" + "═" * 63 + "╣")
            
            print(f"║  Harga Terkini  : {current_price:>10,.0f}                              ║")
            print(f"║  Sinyal         : {a['signal']:<44s} ║")
            print(f"║  Skor           : {score_bar(a['score']):<44s} ║")
            print("╠" + "═" * 63 + "╣")
            
            print(f"║  📐 FIBONACCI ASTRONACCI                                      ║")
            print(f"║  Swing High     : {a['swing_high']:>10,.0f}                              ║")
            print(f"║  Swing Low      : {a['swing_low']:>10,.0f}                              ║")
            print(f"║  Zona Saat Ini  : {a['fib_zone']:<44s} ║")
            
            # Fibonacci Levels
            fib = a['fib_levels']
            print(f"║  ── Level Retracement ──                                      ║")
            for name, val in fib.items():
                marker = " ◄── HARGA" if abs(val - current_price) < (current_price * 0.02) else ""
                print(f"║    {name:>6s}  : {val:>10,.0f}{marker:<33s}  ║")
            
            print("╠" + "═" * 63 + "╣")
            
            print(f"║  📊 INDIKATOR                                                 ║")
            print(f"║  RSI            : {a['rsi']:>5.1f}                                       ║")
            print(f"║  Stochastic %K  : {a['stoch_k']:>5.1f}  ({stoch_label:<10s})                      ║")
            print(f"║  ADX            : {adx_val:>5.1f}  ({adx_label:<10s})                      ║")
            
            if a['patterns']:
                print("╠" + "═" * 63 + "╣")
                print(f"║  🔍 POLA TERDETEKSI                                           ║")
                for p in a['patterns']:
                    print(f"║    • {p:<57s} ║")

            print("╠" + "═" * 63 + "╣")
            print(f"║  💰 REKOMENDASI HARGA                                         ║")
            print(f"║  Entry (Beli)   : {a['buy_price']:>10,.0f}                              ║")
            print(f"║  Take Profit    : {a['sell_target']:>10,.0f}                              ║")
            print(f"║  Stop Loss      : {a['stop_loss']:>10,.0f}                              ║")
            print(f"║  Risk:Reward    : 1:{rr:>5.2f}  ({rr_label:<10s})                      ║")
            
            print("╚" + "═" * 63 + "╝")

        except ValueError:
            print(" [!] Harga harus berupa angka.")
        except Exception as e:
            print(f" [!] Terjadi kesalahan: {e}")

if __name__ == "__main__":
    signal_assistant()
