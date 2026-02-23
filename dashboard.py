"""
STOCKBIT ASTRONACCI PRO – Dashboard Web Server
Flask backend yang menyajikan analisis teknikal via API
Dengan fallback estimasi untuk emiten yang tidak tersedia di Yahoo Finance
"""
from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import traceback
from strategy import calculate_signals, get_ihsg_trend
from explainer import generate_commentary
from news_fetcher import fetch_general_news, fetch_stock_news, analyze_sentiment
from multi_timeframe import calculate_confluence
from backtester import quick_backtest
from database import init_db, add_to_watchlist, remove_from_watchlist, get_watchlist, save_to_cache, get_from_cache, get_screener_results
from telegram_bot import check_updates, send_telegram_msg
import subprocess
import threading

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Inisialisasi Database
init_db()


# ============================================================
# GLOBAL ERROR HANDLERS – Selalu return JSON, bukan HTML
# ============================================================

@app.errorhandler(400)
def bad_request(e):
    return jsonify({'error': 'Request tidak valid'}), 400

@app.errorhandler(404)
def not_found(e):
    # Hanya untuk API routes
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint tidak ditemukan'}), 404
    return render_template('index.html')

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Terjadi kesalahan internal server'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Log error ke console
    print(f"[ERROR] {traceback.format_exc()}")
    return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500


# ============================================================
# DATA FUNCTIONS
# ============================================================

# get_ihsg_trend moved to strategy.py


def get_stock_data(symbol, current_price=None):
    """Ambil data historis nyata dari Yahoo Finance (IDX = symbol.JK)"""
    ticker = f"{symbol}.JK"
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
        
        # Cek apakah data kosong
        if df is None or df.empty:
            return None, f"Emiten {symbol} tidak ditemukan di Yahoo Finance"
        
        # Flatten MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.columns = [c.lower() for c in df.columns]
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                return None, f"Data {symbol} tidak lengkap (kolom {col} tidak ada)"
        
        df = df[required_cols].copy()
        df.dropna(inplace=True)
        
        if len(df) < 30:
            return None, f"Data {symbol} hanya {len(df)} hari (minimal 30 hari)"
        
        if current_price:
            df.loc[df.index[-1], 'close'] = current_price
        
        # Build history for chart
        history = []
        for idx, row in df.iterrows():
            history.append({
                'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(row['volume'])
            })
        
        return df, history
    except Exception as e:
        print(f"[WARN] Yahoo Finance error for {symbol}: {e}")
        return None, str(e)


def get_fundamental_data(symbol):
    """Ambil data fundamental utama (Valuasi & Dividend)"""
    ticker = f"{symbol}.JK"
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        return {
            "pe_ratio": round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else 0,
            "pbv_ratio": round(info.get("priceToBook", 0), 2) if info.get("priceToBook") else 0,
            "dividend_yield": round(info.get("dividendYield", 0) * 100, 2) if info.get("dividendYield") else 0,
            "market_cap": info.get("marketCap", 0),
            "debt_to_equity": round(info.get("debtToEquity", 0), 2) if info.get("debtToEquity") else 0,
            "roe": round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else 0
        }
    except Exception as e:
        print(f"[WARN] Fundamental data error for {symbol}: {e}")
        return {
            "pe_ratio": 0, "pbv_ratio": 0, "dividend_yield": 0, 
            "market_cap": 0, "debt_to_equity": 0, "roe": 0
        }


def make_estimated_data(price):
    """
    Buat data estimasi realistis untuk emiten yang tidak ada di Yahoo Finance.
    Menggunakan random walk dengan volatilitas khas saham IDX (1.5-2% daily).
    """
    np.random.seed(hash(str(price)) % (2**31))
    n = 60
    
    # Random walk yang realistis
    daily_returns = np.random.normal(0.0005, 0.018, n)  # Slight upward bias, 1.8% daily vol
    prices = [price * 0.90]  # Start 10% below current
    for r in daily_returns[:-1]:
        prices.append(prices[-1] * (1 + r))
    prices[-1] = price
    
    highs = [p * (1 + abs(np.random.normal(0.008, 0.006))) for p in prices]
    lows = [p * (1 - abs(np.random.normal(0.008, 0.006))) for p in prices]
    opens = [prices[i-1] if i > 0 else prices[0] for i in range(n)]
    volumes = [int(np.random.uniform(200000, 8000000)) for _ in range(n)]
    
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
    
    df = pd.DataFrame({
        'open': opens, 'high': highs, 'low': lows,
        'close': prices, 'volume': volumes
    }, index=dates)
    
    history = []
    for idx, row in df.iterrows():
        history.append({
            'date': idx.strftime('%Y-%m-%d'),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume'])
        })
    
    return df, history


# ============================================================
# API ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({'error': 'Request body harus berupa JSON'}), 400
        
        symbol = data.get('symbol', '').upper().strip()
        price = data.get('price')
        
        if not symbol:
            return jsonify({'error': 'Masukkan kode saham'}), 400
        
        if price is not None and price != '':
            try:
                price = float(price)
            except (ValueError, TypeError):
                return jsonify({'error': 'Harga harus berupa angka'}), 400
        else:
            price = None

        # Cek Cache (Hanya jika analisis tanpa price manual)
        if price is None:
            cached = get_from_cache(symbol)
            if cached:
                print(f"[CACHE] Mengembalikan data kilat untuk {symbol}")
                return jsonify(cached)
        
        # Coba ambil data dari Yahoo Finance
        df, history_or_error = get_stock_data(symbol, price)
        
        is_estimated = False
        if df is None:
            # FALLBACK: Jika tidak ada di Yahoo Finance, gunakan estimasi
            if price and price > 0:
                df, estimated_history = make_estimated_data(price)
                history_or_error = estimated_history
                is_estimated = True
            else:
                return jsonify({
                    'error': f'{history_or_error}. Masukkan harga manual untuk analisis estimasi (contoh: {symbol} 1000)',
                    'need_price': True
                }), 404
        
        # Analisis sentimen berita (sebelum sinyal)
        sentiment = {'score': 0, 'label': 'Netral', 'detail': '', 'headlines': []}
        try:
            if not is_estimated:
                # 6. Analisis Sentimen (Canggih)
                sentiment = analyze_sentiment(symbol)
        except Exception:
            pass
        
        # 7. Data Fundamental (Valuasi)
        fundamental = get_fundamental_data(symbol)
        
        # 8. Hitung Sinyal (Gabungkan semua data)
        result = calculate_signals(df, sentiment_score=sentiment['score'], fundamental=fundamental)
        
        # 9. AI Expert Commentary (Naratif)
        result['symbol'] = symbol
        result['sentiment'] = sentiment
        result['fundamental'] = fundamental
        result['ai_commentary'] = generate_commentary(result)
        
        # Tambahkan data tambahan
        result['history'] = history_or_error
        
        # Analisis Multi-Timeframe
        try:
            result['mtf'] = calculate_confluence(symbol)
        except Exception:
            result['mtf'] = None

        # Skor IHSG
        ihsg = get_ihsg_trend()
        result['ihsg_context'] = ihsg
        
        # Hitung Efek IHSG ke Signal
        si = result.get('sentiment_impact', {})
        if ihsg['trend'] == 'BEARISH':
            si['market_effect'] = 'Negatif (IHSG Melemah)'
        elif ihsg['trend'] == 'BULLISH':
            si['market_effect'] = 'Positif (IHSG Menguat)'
        else:
            si['market_effect'] = 'Netral'
        result['sentiment_impact'] = si
        
        # Tambahkan sentiment ke result
        result['sentiment'] = sentiment
        
        # Convert numpy types to native Python
        clean_result = {}
        for k, v in result.items():
            if isinstance(v, dict):
                clean_result[k] = {}
                for kk, vv in v.items():
                    try:
                        if isinstance(vv, (np.bool_, np.integer, np.floating)):
                            clean_result[k][kk] = vv.item()
                        else:
                            clean_result[k][kk] = float(vv)
                    except (ValueError, TypeError):
                        clean_result[k][kk] = str(vv)
            elif isinstance(v, list):
                clean_result[k] = [str(item) if not isinstance(item, (int, float)) else item for item in v]
            elif isinstance(v, (int, float)):
                clean_result[k] = float(v)
            else:
                try:
                    clean_result[k] = float(v)
                except (ValueError, TypeError):
                    clean_result[k] = str(v)
        
        clean_result['symbol'] = symbol
        clean_result['history'] = history_or_error
        clean_result['is_estimated'] = is_estimated
        clean_result['sentiment'] = sentiment
        
        if is_estimated:
            clean_result['data_warning'] = f'⚠️ Data {symbol} tidak tersedia di Yahoo Finance. Analisis menggunakan estimasi volatilitas pasar berdasarkan harga {price}.'
        
        # Multi-Timeframe Confluence (async-friendly, non-blocking)
        try:
            if not is_estimated:
                mtf = calculate_confluence(symbol)
                clean_result['multi_timeframe'] = mtf
        except Exception:
            pass
        
        # IHSG Market Trend
        try:
            clean_result['market_trend'] = get_ihsg_trend()
        except Exception:
            clean_result['market_trend'] = {'trend': 'N/A', 'change_pct': 0, 'level': 0}
        
        # Simpan ke Cache (Hanya jika analisis standar tanpa price manual)
        if price is None:
            save_to_cache(symbol, clean_result)

        return jsonify(clean_result)
    
    except Exception as e:
        print(f"[ERROR] analyze: {traceback.format_exc()}")
        return jsonify({'error': f'Terjadi kesalahan: {str(e)}'}), 500

@app.route('/api/news', methods=['GET'])
def get_news():
    """Ambil berita umum pasar saham dari sumber terpercaya"""
    try:
        news = fetch_general_news(max_per_source=5)
        return jsonify({'news': news, 'count': len(news)})
    except Exception as e:
        print(f"[ERROR] news: {traceback.format_exc()}")
        return jsonify({'news': [], 'count': 0, 'error': str(e)})


@app.route('/api/news/<symbol>', methods=['GET'])
def get_stock_news(symbol):
    """Ambil berita spesifik untuk saham tertentu"""
    try:
        symbol = symbol.upper().strip()
        news = fetch_stock_news(symbol, max_results=8)
        return jsonify({'news': news, 'symbol': symbol, 'count': len(news)})
    except Exception as e:
        print(f"[ERROR] stock_news: {traceback.format_exc()}")
        return jsonify({'news': [], 'symbol': symbol, 'count': 0, 'error': str(e)})


@app.route('/api/backtest/<symbol>', methods=['GET'])
def backtest(symbol):
    """Backtesting: uji akurasi sinyal pada data historis"""
    try:
        symbol = symbol.upper().strip()
        result = quick_backtest(symbol)
        return jsonify(result)
    except Exception as e:
        print(f"[ERROR] backtest: {traceback.format_exc()}")
        return jsonify({'win_rate': 0, 'total_trades': 0, 'error': str(e)})


# ============================================================
# WATCHLIST ENDPOINTS
# ============================================================

@app.route('/api/watchlist', methods=['GET'])
def watchlist_get():
    return jsonify(get_watchlist())

@app.route('/api/watchlist', methods=['POST'])
def watchlist_add():
    try:
        data = request.get_json(force=True)
        symbol = data.get('symbol', '').upper().strip()
        if not symbol:
            return jsonify({'error': 'Symbol diperlukan'}), 400
        
        # Ambil data minimal jika ada di payload
        price = data.get('price', 0)
        signal = data.get('signal', '')
        score = data.get('score', 0)
        
        success = add_to_watchlist(symbol, price, signal, score)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlist/<symbol>', methods=['DELETE'])
def watchlist_delete(symbol):
    remove_from_watchlist(symbol)
    return jsonify({'success': True})


# ============================================================
# SCREENER ENDPOINTS
# ============================================================

@app.route('/api/screener', methods=['GET'])
def screener_get():
    """Ambil hasil scan (LQ45 atau MULTIBAGGER) dari DB"""
    scanner_type = request.args.get('type', 'LQ45').upper()
    return jsonify(get_screener_results(scanner_type))

@app.route('/api/screener/run', methods=['POST'])
def screener_run():
    """Trigger scan background (non-blocking)"""
    scanner_type = request.args.get('type', 'LQ45').upper()
    
    def task():
        if scanner_type == 'MULTIBAGGER':
            subprocess.run(["python", "multibagger_screener.py"])
        else:
            subprocess.run(["python", "screener.py"])
    
    threading.Thread(target=task).start()
    return jsonify({'message': f'Screener {scanner_type} started in background'})


@app.route('/api/position-size', methods=['POST'])
def position_size():
    """Hitung position sizing berdasarkan modal dan risiko"""
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({'error': 'Request body harus berupa JSON'}), 400
        
        modal = float(data.get('modal', 10000000))
        risk_pct = float(data.get('risk_pct', 2)) / 100
        entry = float(data.get('entry', 0))
        stop_loss = float(data.get('stop_loss', 0))
        
        if entry <= 0 or stop_loss <= 0 or entry <= stop_loss:
            return jsonify({'error': 'Entry harus lebih besar dari Stop Loss'}), 400
        
        risk_amount = modal * risk_pct
        risk_per_share = entry - stop_loss
        shares = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
        lots = shares // 100
        total_cost = lots * 100 * entry
        actual_risk = lots * 100 * risk_per_share
        
        return jsonify({
            'modal': modal,
            'risk_pct': round(risk_pct * 100, 1),
            'risk_amount': round(risk_amount, 0),
            'lots': lots,
            'shares': lots * 100,
            'total_cost': round(total_cost, 0),
            'actual_risk': round(actual_risk, 0),
            'pct_modal_used': round((total_cost / modal) * 100, 1) if modal > 0 else 0,
        })
    except Exception as e:
        print(f"[ERROR] position_size: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


# ============================================================
# TELEGRAM ENDPOINTS
# ============================================================

@app.route('/api/telegram/sync', methods=['GET'])
def telegram_sync():
    """Trigger pengecekan pendaftar baru di Telegram"""
    try:
        check_updates()
        return jsonify({'success': True, 'message': 'Sinkronisasi Telegram selesai'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/telegram/test', methods=['POST'])
def telegram_test():
    """Kirim pesan uji coba ke semua user terdaftar"""
    from database import get_all_chat_ids
    chat_ids = get_all_chat_ids()
    if not chat_ids:
        return jsonify({'error': 'Belum ada Chat ID terdaftar. Silakan ketik /start di bot.'}), 400
    
    success_count = 0
    for cid in chat_ids:
        res = send_telegram_msg(cid, "<b>Test Notifikasi!</b>\nJika Anda menerima ini, integrasi Telegram Anda sudah AKTIF. 🚀")
        if res and res.get('ok'):
            success_count += 1
            
    return jsonify({'success': True, 'delivered_to': success_count})


if __name__ == '__main__':
    print("\n  ╔═══════════════════════════════════════════╗")
    print("  ║  ASTRONACCI PRO DASHBOARD                 ║")
    print("  ║  Buka: http://localhost:5000               ║")
    print("  ╚═══════════════════════════════════════════╝\n")
    app.run(debug=True, port=5000)
