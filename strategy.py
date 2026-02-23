import pandas as pd
import pandas_ta as ta
import numpy as np

# ================================================================
# ASTRONACCI PRO STRATEGY ENGINE
# Metode: Fibonacci Retracement + Extension + Stochastic + Confluence
# ================================================================

def find_swing_points(df, lookback=20):
    """
    Mendeteksi Swing High dan Swing Low dalam data historis.
    Ini adalah fondasi Fibonacci Retracement & Extension.
    """
    highs = df['high'].values
    lows = df['low'].values
    
    swing_high = None
    swing_low = None
    swing_high_idx = None
    swing_low_idx = None
    
    # Cari titik tertinggi dan terendah dalam rentang lookback
    for i in range(len(df) - lookback, len(df)):
        if i < 0:
            continue
        window_start = max(0, i - lookback)
        window_end = min(len(df), i + lookback)
        
        # Swing High: titik yang lebih tinggi dari semua tetangganya
        if highs[i] == max(highs[window_start:window_end]):
            if swing_high is None or highs[i] > swing_high:
                swing_high = highs[i]
                swing_high_idx = i
        
        # Swing Low: titik yang lebih rendah dari semua tetangganya
        if lows[i] == min(lows[window_start:window_end]):
            if swing_low is None or lows[i] < swing_low:
                swing_low = lows[i]
                swing_low_idx = i
    
    # Fallback: gunakan max/min dari seluruh data jika tidak ditemukan
    if swing_high is None:
        swing_high = df['high'].max()
        swing_high_idx = df['high'].idxmax() if isinstance(df.index, pd.RangeIndex) else len(df) - 1
    if swing_low is None:
        swing_low = df['low'].min()
        swing_low_idx = df['low'].idxmin() if isinstance(df.index, pd.RangeIndex) else 0
    
    return swing_high, swing_low, swing_high_idx, swing_low_idx


def fibonacci_retracement(swing_high, swing_low):
    """
    Hitung level Fibonacci Retracement (metode inti Astronacci).
    Level kunci: 23.6%, 38.2%, 50%, 61.8%, 78.6%
    """
    diff = swing_high - swing_low
    levels = {
        '0.0%': swing_high,
        '23.6%': swing_high - (diff * 0.236),
        '38.2%': swing_high - (diff * 0.382),
        '50.0%': swing_high - (diff * 0.500),
        '61.8%': swing_high - (diff * 0.618),
        '78.6%': swing_high - (diff * 0.786),
        '100%': swing_low,
    }
    return levels


def fibonacci_extension(swing_high, swing_low):
    """
    Hitung level Fibonacci Extension (proyeksi target harga Astronacci).
    Digunakan untuk menentukan Take Profit yang presisi.
    """
    diff = swing_high - swing_low
    extensions = {
        '100%': swing_high,
        '127.2%': swing_high + (diff * 0.272),
        '161.8%': swing_high + (diff * 0.618),
        '200%': swing_high + diff,
        '261.8%': swing_high + (diff * 1.618),
    }
    return extensions


def find_fibonacci_zone(price, fib_levels):
    """
    Tentukan posisi harga saat ini di zona Fibonacci mana.
    Ini membantu mengidentifikasi area Support & Resistance.
    """
    sorted_levels = sorted(fib_levels.items(), key=lambda x: x[1], reverse=True)
    
    for i in range(len(sorted_levels) - 1):
        upper_name, upper_val = sorted_levels[i]
        lower_name, lower_val = sorted_levels[i + 1]
        if lower_val <= price <= upper_val:
            return {
                'zone': f"{lower_name} – {upper_name}",
                'upper': upper_val,
                'lower': lower_val,
                'upper_name': upper_name,
                'lower_name': lower_name
            }
    
    if price > sorted_levels[0][1]:
        return {'zone': 'Di atas Swing High (Breakout)', 
                'upper': None, 'lower': sorted_levels[0][1],
                'upper_name': 'Breakout', 'lower_name': sorted_levels[0][0]}
    else:
        return {'zone': 'Di bawah Swing Low (Breakdown)', 
                'upper': sorted_levels[-1][1], 'lower': None,
                'upper_name': sorted_levels[-1][0], 'lower_name': 'Breakdown'}


def get_ihsg_trend():
    """Ambil trend IHSG (^JKSE) untuk korelasi market"""
    try:
        df = yf.download('^JKSE', period='3mo', interval='1d',
                        progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 21:
            return {"trend": "N/A", "change_pct": 0, "level": 0}
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.columns = [c.lower() for c in df.columns]
        
        # Import local to avoid circular dep if needed, or use existing imports
        import pandas_ta as ta
        ema9 = ta.ema(df['close'], length=9)
        ema21 = ta.ema(df['close'], length=21)
        last_close = float(df['close'].iloc[-1])
        prev_close = float(df['close'].iloc[-2])
        last_ema9 = float(ema9.iloc[-1]) if ema9 is not None else last_close
        last_ema21 = float(ema21.iloc[-1]) if ema21 is not None else last_close
        change_pct = round(((last_close - prev_close) / prev_close) * 100, 2)
        
        if last_ema9 > last_ema21:
            trend = "BULLISH"
        elif last_ema9 < last_ema21:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return {
            "trend": trend,
            "change_pct": change_pct,
            "level": round(last_close, 0),
        }
    except Exception as e:
        print(f"[WARN] IHSG trend: {e}")
        return {"trend": "N/A", "change_pct": 0, "level": 0}


def calculate_foreign_flow(df):
    """
    Estimasi Pergerakan Investor Besar (Bandarmology / Foreign Flow).
    Karena API Broker Summary tertutup, kita menggunakan korelasi Volume & Price:
    - Akumulasi: Harga Naik + Volume > Rata-rata (Smart Money Entry)
    - Distribusi: Harga Turun + Volume > Rata-rata (Big Player Exit)
    """
    last_5 = df.tail(5)
    vol_avg = df['volume'].rolling(window=20).mean().iloc[-1]
    
    accumulation_days = 0
    distribution_days = 0
    
    for _, row in last_5.iterrows():
        change = row['close'] - row['open']
        is_high_volume = row['volume'] > vol_avg
        
        if change > 0 and is_high_volume:
            accumulation_days += 1
        elif change < 0 and is_high_volume:
            distribution_days += 1
            
    if accumulation_days > distribution_days:
        label = "ACCUMULATION"
        score = 25 * (accumulation_days / 5)
    elif distribution_days > accumulation_days:
        label = "DISTRIBUTION"
        score = -25 * (distribution_days / 5)
    else:
        label = "NEUTRAL"
        score = 0
        
    return {
        "status": label,
        "score": round(score, 1),
        "desc": f"{accumulation_days} hari akumulasi vs {distribution_days} hari distribusi (Volume > Rata-rata)"
    }


def calculate_signals(df, sentiment_score=0, fundamental=None):
    """
    ENGINE ANALISIS ASTRONACCI PRO
    Menggabungkan:
    1. Fibonacci Retracement & Extension (Astronacci Core)
    2. Stochastic Oscillator (Momentum)
    3. MACD, RSI, ADX, ATR, Bollinger Bands
    4. Volume Analysis (OBV, Vol-Price, Divergence)
    5. Candlestick Patterns
    6. Sentimen Berita (parameter sentiment_score: -100..+100)
    7. Fundamental Context (Valuasi)
    
    Args:
        df: DataFrame OHLCV
        sentiment_score: Skor sentimen berita (-100 s/d +100, 0 = netral)
        fundamental: Dictionary berisi data fundamental (e.g., {'pe_ratio': 10, 'pbv_ratio': 1.5, 'dividend_yield': 5})
    
    Output: Skor berbobot 0-100
    """
    if df is None or df.empty:
        return None
    
    # Pre-check Fundamental
    fund_data = fundamental if fundamental else {}
    is_undervalued = fund_data.get('pe_ratio', 20) < 12 and fund_data.get('pbv_ratio', 2) < 1.2
    is_high_dividend = fund_data.get('dividend_yield', 0) > 4
    
    if len(df) < 30:
        return "NEUTRAL"

    # ============================================================
    # BAGIAN 1: KALKULASI INDIKATOR
    # ============================================================
    
    # 1. EMA (Trend Direction)
    ema9 = ta.ema(df['close'], length=9)
    df['ema_9'] = ema9 if ema9 is not None else df['close']
    ema21 = ta.ema(df['close'], length=21)
    df['ema_21'] = ema21 if ema21 is not None else df['close']
    ema50 = ta.ema(df['close'], length=50)
    df['ema_50'] = ema50.fillna(df['close'].mean()) if ema50 is not None else df['close'].mean()

    # 2. MACD (Momentum)
    macd = ta.macd(df['close'])
    if macd is not None and not macd.empty:
        df['macd'] = macd.iloc[:, 0]
        df['macd_signal'] = macd.iloc[:, 1]
        df['macd_hist'] = macd.iloc[:, 2]
    else:
        df['macd'] = 0
        df['macd_signal'] = 0
        df['macd_hist'] = 0

    # 3. RSI
    rsi_result = ta.rsi(df['close'], length=14)
    df['rsi'] = rsi_result.fillna(50) if rsi_result is not None else 50

    # 4. Bollinger Bands
    bbands = ta.bbands(df['close'], length=20, std=2)
    if bbands is not None and not bbands.empty:
        df['bb_lower'] = bbands.iloc[:, 0]
        df['bb_mid'] = bbands.iloc[:, 1]
        df['bb_upper'] = bbands.iloc[:, 2]
    else:
        df['bb_lower'] = df['close'].min() * 0.98
        df['bb_mid'] = df['close'].mean()
        df['bb_upper'] = df['close'].max() * 1.02

    # 5. ATR (Dynamic Stop Loss)
    atr_result = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['atr'] = atr_result.fillna(df['close'] * 0.02) if atr_result is not None else df['close'] * 0.02

    # 6. ADX (Trend Strength)
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
    if adx_df is not None and not adx_df.empty:
        df['adx'] = adx_df.iloc[:, 0]
    else:
        df['adx'] = 15

    # 7. STOCHASTIC OSCILLATOR (Astronacci Confirmation)
    stoch = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
    if stoch is not None and not stoch.empty:
        df['stoch_k'] = stoch.iloc[:, 0].fillna(50)
        df['stoch_d'] = stoch.iloc[:, 1].fillna(50)
    else:
        df['stoch_k'] = 50
        df['stoch_d'] = 50

    # 8. FIBONACCI (Astronacci Core)
    swing_high, swing_low, sh_idx, sl_idx = find_swing_points(df)
    fib_levels = fibonacci_retracement(swing_high, swing_low)
    fib_ext = fibonacci_extension(swing_high, swing_low)

    # 9. Smart Money Flow (Bandarmology)
    money_flow = calculate_foreign_flow(df)

    # ============================================================
    # BAGIAN 2: LOGIKA SINYAL & SCORING BERBOBOT
    # ============================================================
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = last['close']

    # --- Foreign Flow Impact ---
    is_accumulation = money_flow['status'] == "ACCUMULATION"
    is_distribution = money_flow['status'] == "DISTRIBUTION"

    # --- Fibonacci Zone Analysis ---
    fib_zone = find_fibonacci_zone(price, fib_levels)
    
    # Apakah harga di zona GOLDEN (38.2% - 61.8%)? Area paling penting Astronacci
    fib_382 = fib_levels['38.2%']
    fib_618 = fib_levels['61.8%']
    is_golden_zone = fib_618 <= price <= fib_382
    is_deep_value = price <= fib_levels['61.8%']  # Di bawah 61.8% = diskon besar

    # --- Stochastic Analysis ---
    stoch_k = last['stoch_k'] if not pd.isna(last['stoch_k']) else 50
    stoch_d = last['stoch_d'] if not pd.isna(last['stoch_d']) else 50
    is_stoch_oversold = stoch_k < 20
    is_stoch_overbought = stoch_k > 80
    is_stoch_bullish_cross = stoch_k > stoch_d and stoch_k < 50  # Golden cross area bawah

    # --- Classic Indicators ---
    is_bullish_trend = last['ema_9'] > last['ema_21']
    is_above_ema50 = price > last['ema_50']
    is_macd_bullish = last['macd'] > last['macd_signal']
    is_macd_hist_rising = last['macd_hist'] > prev['macd_hist'] if not pd.isna(prev['macd_hist']) else False
    rsi_val = last['rsi'] if not pd.isna(last['rsi']) else 50
    is_rsi_oversold = rsi_val < 30
    is_rsi_overbought = rsi_val > 70
    adx_val = last['adx'] if not pd.isna(last['adx']) else 15
    is_strong_trend = adx_val > 20
    
    is_near_bb_lower = price <= last['bb_lower'] * 1.02
    is_near_bb_upper = price >= last['bb_upper'] * 0.98
    
    # --- Volume Analysis (Enhanced) ---
    vol_avg = df['volume'].rolling(window=20).mean().iloc[-1]
    is_volume_above_avg = last['volume'] > vol_avg * 1.2
    is_volume_spike = last['volume'] > vol_avg * 1.8
    vol_ratio = round(float(last['volume'] / vol_avg), 2) if vol_avg > 0 else 1.0
    
    # OBV Trend (On-Balance Volume)
    obv = ta.obv(df['close'], df['volume'])
    if obv is not None and len(obv) >= 10:
        obv_sma = obv.rolling(10).mean()
        obv_trending_up = obv.iloc[-1] > obv_sma.iloc[-1] if not pd.isna(obv_sma.iloc[-1]) else False
    else:
        obv_trending_up = False
    
    # Volume-Price Confirmation
    last5_close = df['close'].iloc[-5:]
    last5_vol = df['volume'].iloc[-5:]
    price_up = last5_close.iloc[-1] > last5_close.iloc[0]
    vol_up = last5_vol.iloc[-1] > last5_vol.mean()
    vol_price_confirm = (price_up and vol_up) or (not price_up and not vol_up)
    
    # Volume Divergence (harga naik tapi volume turun = divergence bearish)
    vol_divergence = price_up and not vol_up

    # --- Candlestick Patterns ---
    body = abs(price - last['open'])
    candle_range = last['high'] - last['low']
    lower_shadow = min(last['open'], price) - last['low']
    upper_shadow = last['high'] - max(last['open'], price)
    
    is_hammer = (lower_shadow > 2 * body) and (body > 0) and (candle_range > 0)
    is_bullish_engulfing = (price > prev['open']) and (last['open'] < prev['close']) and (prev['close'] < prev['open'])
    is_doji = (body < candle_range * 0.1) and (candle_range > 0)

    # ============================================================
    # BAGIAN 3: SCORING BERBOBOT (0-100) — REBALANCED
    # ============================================================
    
    score = 0
    max_score = 100
    details = {}
    
    # A. FIBONACCI ASTRONACCI (Bobot: 25 poin)
    fib_score = 0
    if is_golden_zone:
        fib_score += 12
        details['fib'] = "Golden Zone (38.2%-61.8%)"
    elif is_deep_value:
        fib_score += 16
        details['fib'] = "Deep Value Zone (>61.8%)"
    elif price <= fib_levels['23.6%']:
        fib_score += 6
        details['fib'] = "Retracement Zone (23.6%)"
    else:
        details['fib'] = f"Zona: {fib_zone['zone']}"
    
    if is_stoch_bullish_cross and (is_golden_zone or is_deep_value):
        fib_score += 9
        details['astro_confirm'] = "Stochastic ✓ di Fibonacci Zone"
    score += min(fib_score, 25)

    # B. MOMENTUM (Bobot: 20 poin)
    mom_score = 0
    if is_macd_bullish: mom_score += 6
    if is_macd_hist_rising: mom_score += 4
    if is_stoch_oversold: mom_score += 6
    elif is_stoch_bullish_cross: mom_score += 4
    if is_rsi_oversold: mom_score += 4
    elif 30 <= rsi_val <= 50: mom_score += 2
    score += min(mom_score, 20)

    # C. TREND (Bobot: 15 poin)
    trend_score = 0
    if is_bullish_trend: trend_score += 6
    if is_above_ema50: trend_score += 4
    if is_strong_trend: trend_score += 5
    score += min(trend_score, 15)

    # D. VOLUME ANALYSIS (Bobot: 20 poin) — DITINGKATKAN
    vol_score = 0
    if is_volume_above_avg: vol_score += 5
    if is_volume_spike: vol_score += 4
    if obv_trending_up: vol_score += 5      # OBV naik = uang masuk
    if vol_price_confirm: vol_score += 4    # Volume confirm price direction
    if vol_divergence: vol_score -= 3       # Warning: price naik tapi volume turun
    if is_near_bb_lower and is_volume_above_avg: vol_score += 2  # Volume bounce dari support
    score += max(min(vol_score, 20), 0)

    # E. CANDLESTICK PATTERNS (Bobot: 10 poin)
    candle_score = 0
    if is_hammer: candle_score += 5
    if is_bullish_engulfing: candle_score += 5
    if is_doji and is_near_bb_lower: candle_score += 3
    score += min(candle_score, 10)
    
    # G. SMART MONEY FLOW (Bobot: 10 poin)
    if is_accumulation:
        score += 10
        details['money_flow'] = "Deteksi Akumulasi (Big Player Entry)"
    elif is_distribution:
        score -= 5
        details['money_flow'] = "Deteksi Distribusi (Big Player Exit)"
    
    # F. BONUS: Volume-Price Alignment (+10 poin max)
    bonus = 0
    if vol_price_confirm and obv_trending_up and is_volume_above_avg: bonus += 6
    if is_volume_spike and is_golden_zone: bonus += 4
    score += min(bonus, 10)
    
    score = min(score, 100)

    # ============================================================
    # BAGIAN 4: REKOMENDASI HARGA (Multi-Indikator Adaptif)
    # ============================================================
    
    # --- Base: Fibonacci Levels ---
    fib_supports = [v for k, v in fib_levels.items() if v < price]
    fib_resistances = [v for k, v in fib_levels.items() if v > price]
    
    nearest_support = max(fib_supports) if fib_supports else price * 0.97
    nearest_resistance = min(fib_resistances) if fib_resistances else fib_ext['127.2%']
    
    atr_val = last['atr'] if not pd.isna(last['atr']) else price * 0.02
    bb_lower = last['bb_lower'] if not pd.isna(last['bb_lower']) else price * 0.95
    bb_upper = last['bb_upper'] if not pd.isna(last['bb_upper']) else price * 1.05
    
    # --- ENTRY (BELI) — Multi-Indikator ---
    entry_base = nearest_support
    entry_adj = 0
    
    # Bollinger: Jika harga dekat BB lower, entry = max(fib, BB lower)
    if is_near_bb_lower:
        entry_base = max(entry_base, bb_lower)
    
    # Volume: Lemah → geser entry turun (kurang confidence)
    if not is_volume_above_avg:
        entry_adj -= price * 0.005  # −0.5%
    
    # EMA: Di bawah EMA50 → trend lemah, geser entry turun
    if not is_above_ema50:
        entry_adj -= price * 0.005  # −0.5%
    
    # Sentimen berita: positif naik, negatif turun
    if sentiment_score > 20:
        entry_adj += price * 0.005  # Boleh entry sedikit lebih mahal
    elif sentiment_score < -20:
        entry_adj -= price * 0.005  # Entry lebih rendah
    
    buy_price = round(entry_base + entry_adj, 0)
    
    # Penyesuaian Fundamental: Undervalued -> entry boleh lebih agresif
    if is_undervalued:
        buy_price = round(buy_price * 1.005, 0) # +0.5% agresif
    
    # --- TAKE PROFIT — Multi-Indikator ---
    tp_base = nearest_resistance if fib_resistances else fib_ext['127.2%']
    tp_adj = 0
    
    # ADX: Trend kuat → TP lebih jauh (gunakan extension lebih tinggi)
    if adx_val > 25 and is_bullish_trend:
        tp_base = max(tp_base, fib_ext['161.8%'])
    elif adx_val > 35:
        tp_base = max(tp_base, fib_ext['200%'])  # Very strong trend
    
    # RSI: Sudah tinggi → kurangi TP (dekat overbought)
    if rsi_val > 65:
        tp_adj -= tp_base * 0.01  # −1%
    elif rsi_val > 75:
        tp_adj -= tp_base * 0.02  # −2%
    
    # Volume Spike: Momentum kuat → TP dinaikkan
    if is_volume_spike:
        tp_adj += tp_base * 0.01  # +1%
    
    # OBV: Money flow naik → TP dinaikkan
    if obv_trending_up and is_volume_above_avg:
        tp_adj += tp_base * 0.005  # +0.5%
    
    # Sentimen berita
    if sentiment_score > 20:
        tp_adj += tp_base * 0.01  # Berita positif -> TP +1%
    elif sentiment_score < -20:
        tp_adj -= tp_base * 0.01  # Berita negatif -> TP −1%
    
    # Bandarmology Adjustment: Akumulasi Masif -> TP lebih jauh
    if is_accumulation:
        tp_adj += tp_base * 0.02 # Berani tahan lebih lama (+2%)
    
    sell_target = round(tp_base + tp_adj, 0)
    
    # --- STOP LOSS — Multi-Indikator ---
    sl_atr = nearest_support - (1.5 * atr_val)
    sl_bb = bb_lower - (price * 0.005)
    
    # Gunakan level yang lebih protektif (lebih tinggi = lebih ketat)
    stop_loss_base = max(sl_atr, sl_bb)
    
    # Swing Low terakhir: SL tidak boleh di atas swing low
    recent_low = df['low'].iloc[-10:].min()
    if stop_loss_base > recent_low:
        stop_loss_base = min(stop_loss_base, recent_low - (0.5 * atr_val))
    
    # Sentimen negatif → SL lebih ketat (protektif)
    sl_adj = 0
    if sentiment_score < -20:
        sl_adj += price * 0.005  # SL naik 0.5% (lebih dekat ke entry)
    elif sentiment_score < -50:
        sl_adj += price * 0.01   # SL naik 1% (sangat protektif)
    
    # Overvaluation Adjustment: Jika PE / PBV terlalu tinggi, SL diperketat
    pe = fund_data.get('pe_ratio', 0)
    if pe > 35: # Contoh threshold overvalued
        sl_adj += price * 0.005 # SL lebih ketat untuk saham mahal
    
    stop_loss = round(stop_loss_base + sl_adj, 0)
    
    # Safety: SL tidak boleh >= entry
    if stop_loss >= buy_price:
        stop_loss = round(buy_price - atr_val, 0)
    
    # Risk-Reward Ratio
    risk = price - stop_loss
    reward = sell_target - price
    rr_ratio = round(reward / risk, 2) if risk > 0 else 0
    
    # Sentiment impact summary
    sentiment_impact = {
        "score": sentiment_score,
        "entry_effect": "naik" if sentiment_score > 20 else ("turun" if sentiment_score < -20 else "netral"),
        "tp_effect": "+1%" if sentiment_score > 20 else ("-1%" if sentiment_score < -20 else "0%"),
        "sl_effect": "diperketat" if sentiment_score < -20 else "normal",
    }

    # ============================================================
    # BAGIAN 5: KEPUTUSAN SINYAL
    # ============================================================
    
    patterns = []
    if is_golden_zone: patterns.append("🎯 Fibonacci Golden Zone")
    if is_deep_value: patterns.append("💎 Deep Value Zone")
    if is_stoch_bullish_cross: patterns.append("⚡ Stochastic Bullish Cross")
    if is_stoch_oversold: patterns.append("📉 Stochastic Oversold")
    if is_hammer: patterns.append("🔨 Hammer")
    if is_bullish_engulfing: patterns.append("🟢 Bullish Engulfing")
    if is_doji: patterns.append("⭐ Doji")
    if is_volume_spike: patterns.append("📊 Volume Spike")
    if is_strong_trend: patterns.append("💪 Strong Trend")
    if is_near_bb_lower: patterns.append("📏 Near BB Support")
    if is_rsi_oversold: patterns.append("🔻 RSI Oversold")
    if is_accumulation: patterns.append("🐋 Smart Money Accumulation")
    if is_distribution: patterns.append("⚠️ Distribution Detected")
    
    # Sinyal berdasarkan skor berbobot
    signal = "NEUTRAL"
    if score >= 70 and rr_ratio >= 2:
        signal = "STRONG_BUY ⭐⭐⭐"
    elif score >= 55 and rr_ratio >= 1.5:
        signal = "BUY ⭐⭐"
    elif score >= 40:
        signal = "BUY ⭐"
    elif is_rsi_overbought and is_near_bb_upper:
        signal = "STRONG_SELL 🔴🔴"
    elif is_rsi_overbought or is_stoch_overbought:
        signal = "SELL 🔴"
    
    return {
        "signal": signal,
        "score": score,
        "max_score": max_score,
        "current_price": price,
        "buy_price": buy_price,
        "sell_target": sell_target,
        "stop_loss": stop_loss,
        "rr_ratio": rr_ratio,
        "patterns": patterns,
        "adx": round(adx_val, 1),
        "rsi": round(rsi_val, 1),
        "stoch_k": round(stoch_k, 1),
        "stoch_d": round(stoch_d, 1),
        "fib_levels": {k: round(v, 0) for k, v in fib_levels.items()},
        "fib_extensions": {k: round(v, 0) for k, v in fib_ext.items()},
        "fib_zone": fib_zone['zone'],
        "swing_high": round(swing_high, 0),
        "swing_low": round(swing_low, 0),
        "volume_analysis": {
            "vol_ratio": vol_ratio,
            "obv_up": obv_trending_up,
            "vol_price_confirm": vol_price_confirm,
            "vol_divergence": vol_divergence,
        },
        "money_flow": money_flow,
        "sentiment_impact": sentiment_impact,
    }


if __name__ == "__main__":
    # Quick test
    price_list = [100, 102, 105, 103, 108, 110, 112, 115, 113, 118,
                  116, 114, 112, 110, 108, 106, 104, 102, 100, 98,
                  96, 94, 92, 95, 97, 99, 101, 103, 100, 98,
                  96, 94, 97, 99, 101, 103, 105, 107, 104, 102,
                  100, 98, 96, 99, 101, 103, 105, 107, 109, 106,
                  104, 102, 100, 103, 105, 107, 109, 111, 108, 106]
    data = {
        'close': price_list,
        'volume': [int(1000 + i * 50) for i in range(60)],
        'high': [p * 1.015 for p in price_list],
        'low': [p * 0.985 for p in price_list],
        'open': [price_list[i-1] if i > 0 else 100 for i in range(60)]
    }
    df = pd.DataFrame(data)
    result = calculate_signals(df)
    if isinstance(result, dict):
        print(f"Signal: {result['signal']} | Score: {result['score']}/100")
        print(f"Fibonacci Zone: {result['fib_zone']}")
        print(f"Swing H/L: {result['swing_high']}/{result['swing_low']}")
        print(f"RR Ratio: {result['rr_ratio']}")
        print(f"Patterns: {result['patterns']}")
