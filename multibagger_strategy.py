import pandas as pd
import pandas_ta as ta
import numpy as np
from news_fetcher import fetch_stock_news

# ================================================================
# MULTIBAGGER POTENTIAL STRATEGY
# Fokus: Early Entry, Low Price, Base Building, & Acquisition Catalyst
# ================================================================

import yfinance as yf

CONGLO_KEYWORDS = [
    "salim", "sinarmas", "barito", "astra", "lippo", "djarum", 
    "panigoro", "tanoesoedibjo", "prajogo", "boy thohir", "chairul tanjung",
    "akuisisi", "acquisition", "pengendali baru", "new controller", 
    "tender offer", "backdoor listing", "konsolidasi grup",
    "ikn", "hilirisasi", "lithium", "nickel", "renewable", "energy transition"
]

def calculate_relative_strength(df):
    """
    Menghitung Relative Strength (RS) saham vs IHSG (^JKSE).
    Saham yang outperform market saat IHSG sideways/turun adalah calon suberbagger.
    """
    try:
        # Ambil data IHSG (6 bulan terakhir)
        ihsg = yf.download("^JKSE", period="6mo", interval="1d", progress=False, auto_adjust=True)
        if isinstance(ihsg.columns, pd.MultiIndex):
            ihsg.columns = ihsg.columns.droplevel(1)
        
        # Calculate returns
        stock_ret = df['close'].pct_change(20).iloc[-1] # 1 month return
        ihsg_ret = ihsg['Close'].pct_change(20).iloc[-1]
        
        # Compare
        rs_score = stock_ret - ihsg_ret
        return rs_score
    except Exception:
        return 0

def detect_base_building(df, window=90):
    """
    Mendeteksi apakah saham sedang dalam fase 'Base Building' (Sideways panjang).
    Saham multibagger seringkali 'tidur' lama sebelum meledak.
    """
    if len(df) < window:
        return False, 0
    
    recent_df = df.tail(window)
    max_price = recent_df['close'].max()
    min_price = recent_df['close'].min()
    avg_price = recent_df['close'].mean()
    
    # Rentang harga dalam % (Volatility)
    price_range_pct = (max_price - min_price) / avg_price * 100
    
    # Jika rentang harga < 15% selama 3 bulan, dianggap sideways kuat (Base Building)
    is_base = price_range_pct < 15
    return is_base, round(price_range_pct, 1)

def detect_momentum_stage2(df):
    """
    Mark Minervini Stage 2 - Trend Pemulihan/Naik.
    Multibagger butuh konfirmasi trend sebelum benar-benar lari.
    """
    if len(df) < 200:
        return False, 0
    
    last = df.iloc[-1]
    ma20 = df['close'].rolling(window=20).mean().iloc[-1]
    ma50 = df['close'].rolling(window=50).mean().iloc[-1]
    ma200 = df['close'].rolling(window=200).mean().iloc[-1]
    
    # 1. Harga di atas MA200
    # 2. MA50 di atas MA200
    # 3. MA20 di atas MA50
    is_stage2 = last['close'] > ma200 and ma50 > ma200 and ma20 > ma50
    
    # Distance from low (Stage 2 awal biasanya baru naik 20-40% dari bottom)
    low_252 = df['close'].tail(252).min()
    dist_from_low = (last['close'] - low_252) / low_252 * 100
    
    return is_stage2, round(dist_from_low, 1)

def detect_early_accumulation(df):
    """
    Mendeteksi akumulasi dini: Volume naik signifikan tapi harga belum lari.
    (Early signs of Smart Money entering)
    """
    if len(df) < 20:
        return False, 0
    
    last = df.iloc[-1]
    vol_avg = df['volume'].rolling(window=20).mean().iloc[-1]
    
    vol_ratio = last['volume'] / vol_avg if vol_avg > 0 else 1
    price_change = abs(last['close'] - last['open']) / last['open'] * 100
    
    # Kriteria: Volume > 1.8x rata-rata, tapi harga berubah < 3.5%
    is_early = vol_ratio > 1.8 and price_change < 3.5
    return is_early, round(vol_ratio, 1)

def scan_acquisition_catalyst(symbol):
    """
    Memindai berita untuk mencari kata kunci akuisisi atau nama konglomerat.
    """
    try:
        news = fetch_stock_news(symbol, max_results=10)
        found_keywords = []
        for item in news:
            text = (item['title'] + " " + item['summary']).lower()
            for kw in CONGLO_KEYWORDS:
                if kw in text:
                    found_keywords.append(kw)
        
        # Return unique keywords
        return list(set(found_keywords))
    except Exception:
        return []

def calculate_multibagger_signals(df, symbol, fundamental=None):
    """
    Engine Utama Pendeteksi Multibagger (Versi Akurat/Refined).
    Bobot: Technical (35%), Valuation (20%), Growth (25%), Quality (10%), Catalyst (10%).
    Metrik Berbasis: Peter Lynch, William O'Neil, & Lo Kheng Hong.
    """
    if df is None or df.empty or len(df) < 60:
        return None

    score = 0
    details = []
    fund = fundamental if fundamental else {}
    last_price = df['close'].iloc[-1]
    
    # --- 0. SAFETY FILTER (PREVENT BANKRUPT/TRASH STOCKS) ---
    pbv = fund.get('pbv_ratio', 2)
    roe = fund.get('roe', 0)
    der = fund.get('debt_to_equity', 2.0)
    op_margin = fund.get('operating_margins', 0)
    rev_growth = fund.get('revenue_growth', 0)
    
    # Kriteria 'Sampah' / Collapse:
    # 1. PBV < 0 (Ekuitas Negatif / Bangkrut secara teknis)
    # 2. Operating Margin sangat negatif (< -50%)
    # 3. DER sangat tinggi (> 5.0) tanpa pertumbuhan
    if pbv and pbv < 0:
        details.append("❌ SAFETY REJECT: Ekuitas Negatif (Potensi Delisting)")
        return { "symbol": symbol, "signal": "TRASH/RISK", "score": 0, "patterns": details, "current_price": last_price, "buy_price": 0, "sell_target": 0, "stop_loss": 0 }

    if der and der > 5.0 and rev_growth < 0:
        details.append("❌ SAFETY REJECT: Hutang Ekstrim & Revenue Turun")
        return { "symbol": symbol, "signal": "HIGH DEBT RISK", "score": 10, "patterns": details, "current_price": last_price, "buy_price": 0, "sell_target": 0, "stop_loss": 0 }

    # --- 1. TECHNICAL & MOMENTUM (35 POIN) ---
    rs_val = calculate_relative_strength(df)
    if rs_val > 0.05: # Outperform IHSG by 5% in 1 month
        score += 5 # Dikurangi (RS seringkali tinggi setelah harga naik banyak)
        details.append(f"Market Leader (Outperform IHSG {round(rs_val*100)}%)")

    # Base building (Value entry) - PRIORITAS UTAMA
    is_base, range_pct = detect_base_building(df, window=90)
    if is_base:
        score += 25 # Ditingkatkan dari 15
        details.append(f"BASE BUILDING (Sideways {range_pct}%): Saham masih 'Tidur' & Murah")
    
    # Momentum (Growth entry) - Cek apakah sudah terlambat (High Price)
    is_stage2, dist_low = detect_momentum_stage2(df)
    
    # PENALTY: Jika harga sudah naik > 100% dari Low 52-minggu
    if dist_low > 100:
        score -= 20
        details.append(f"⚠️ HARGA SUDAH TINGGI: Naik {dist_low}% dari Low (Resiko Pucuk)")
    elif dist_low > 200:
        score -= 40
        details.append(f"❌ TERLALU TINGGI: Naik {dist_low}% (Bukan Calon Multibagger lagi)")

    if is_stage2:
        if dist_low < 50:
            score += 15 # Stage 2 Awal
            details.append(f"STAGE 2 AWAL: Trend Baru Mulai")
        else:
            score += 5 # Stage 2 Lanjutan (Poin Kecil)
            details.append(f"Stage 2 (Trend Lanjut)")
    
    is_early_vol, vol_ratio = detect_early_accumulation(df)
    if is_early_vol:
        score += 15 # Ditingkatkan (Akumulasi Dini)
        details.append(f"EARLY ACCUMULATION (Vol Spike {vol_ratio}x)")

    # --- 2. VALUATION (20 POIN) - Kriteria LKH & Deep Value ---
    per = fund.get('pe_ratio')
    div_yield = fund.get('dividend_yield', 0)
    
    # Skor PBV (LKH favorit < 1.0)
    if pbv is not None:
        if 0 < pbv < 0.8: # Deep Discount
            score += 15
            details.append(f"Deep Value (PBV {round(pbv, 2)})")
        elif 0.8 <= pbv < 1.2:
            score += 10
            details.append(f"Undervalued (PBV {round(pbv, 2)})")
        elif 1.2 <= pbv < 1.8:
            score += 5
            details.append(f"Fair Price (PBV {round(pbv, 2)})")
    else:
        score += 5
        details.append("PBV Data N/A (Skor Netral)")
        
    # Skor PER (LKH favorit < 5x, Peter Lynch < 10x)
    if per is not None:
        if 0 < per < 6: # Ultra Low
            score += 15
            details.append(f"Ultra Low PER ({round(per, 1)})")
        elif 6 <= per < 12:
            score += 10
            details.append(f"Low PER ({round(per, 1)})")
        elif 12 <= per < 18:
            score += 5
            details.append(f"Moderate PER ({round(per, 1)})")
    else:
        score += 5
        details.append("PER Data N/A (Skor Netral)")

    # Bonus Dividend (LKH Love)
    if div_yield and div_yield > 0.04: # > 4% yield
        score += 10
        details.append(f"Dividend Jewel (Yield {round(div_yield*100, 1)}%)")

    # --- 3. GROWTH & BUSINESS MOMENTUM (20 POIN) ---
    eps_growth = fund.get('earnings_growth')
    
    if eps_growth is not None:
        if eps_growth >= 0.20: 
            score += 15
            details.append(f"Eksplosif EPS Growth ({round(eps_growth*100)}%)")
        elif eps_growth > 0:
            score += 5
            details.append(f"Positive EPS Growth ({round(eps_growth*100)}%)")
    else:
        if rev_growth and rev_growth > 0:
            score += 10
            details.append(f"Revenue Growth ({round(rev_growth*100)}%) substitute for EPS")

    # --- 4. QUALITY, SIZE & SAFETY (15 POIN) ---
    # Penny Stock Bonus & High Price Penalty
    if last_price < 1000:
        if score > 20: # Hanya jika fundamental & teknikal dasar oke
            score += 15 # Ditingkatkan dari 5
            details.append(f"Penny Stock Multiplier: Harga Rp{int(last_price)} (Potensi Upside Tinggi)")
    else:
        score -= 50 # PENALTY KERAS untuk harga > 1000
        details.append(f"⚠️ BUKAN PENNY STOCK: Harga Rp{int(last_price)} (Terlalu Mahal untuk Multibagger)")

    if roe and roe >= 0.12: 
        score += 5
        details.append(f"Healthy ROE ({round(roe*100)}%)")
    
    if der is not None:
        if der < 1.2: 
            score += 5
            details.append(f"Safe Debt ({round(der, 2)})")
    else:
        score += 3
        details.append("Debt Data N/A")

    # --- 5. CATALYST & CONGLOMERATE (10 POIN) ---
    catalysts = scan_acquisition_catalyst(symbol)
    if catalysts:
        score += 15 # Ditingkatkan bobotnya
        details.append(f"Katalis: {', '.join(catalysts[:2])}")
    
    # Sinyal Final (Threshold diperketat tapi lebih akurat)
    signal = "WAIT & SEE"
    if score >= 70:
        signal = "SUPER MULTIBAGGER 💎💎"
    elif score >= 50:
        signal = "STRONG GROWTH STOCK 🚀"
    elif score >= 30:
        signal = "ACCUMULATION WATCH 🔦"

    # Prediksi target
    sell_target = last_price * 2.0
    stop_loss = last_price * 0.82 # SL 18% (Multibagger butuh napas)

    return {
        "symbol": symbol,
        "signal": signal,
        "score": score,
        "current_price": last_price,
        "buy_price": last_price,
        "sell_target": sell_target,
        "stop_loss": stop_loss,
        "patterns": details,
        "is_base": is_base,
        "is_stage2": is_stage2,
        "dist_low": dist_low,
        "pbv": pbv,
        "per": per,
        "roe": roe,
        "der": der,
        "catalysts": catalysts
    }
