import sqlite3
import json
from datetime import datetime
import os

DB_NAME = "saham_v2.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inisialisasi schema database jika belum ada"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Tabel Watchlist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS watchlist (
        symbol TEXT PRIMARY KEY,
        added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_price REAL,
        last_signal TEXT,
        last_score REAL
    )
    ''')
    
    # 2. Tabel Cache Analisis (untuk kecepatan)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS analysis_cache (
        symbol TEXT PRIMARY KEY,
        data TEXT, -- JSON string
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 3. Tabel Jurnal Jual-Beli (Portofolio)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        entry_date DATE,
        entry_price REAL,
        lots INTEGER,
        status TEXT DEFAULT 'OPEN', -- 'OPEN' or 'CLOSED'
        exit_date DATE,
        exit_price REAL,
        notes TEXT
    )
    ''')

    # 4. Tabel Hasil Screener (Ditingkatkan dengan scanner_type)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS screener_results (
        symbol TEXT,
        scanner_type TEXT DEFAULT 'LQ45', -- 'LQ45' or 'MULTIBAGGER'
        signal TEXT,
        score REAL,
        buy_price REAL,
        sell_target REAL,
        stop_loss REAL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (symbol, scanner_type)
    )
    ''')
    
    # 5. Tabel Pengaturan Telegram
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS telegram_settings (
        chat_id TEXT PRIMARY KEY,
        is_active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[DB] Database {DB_NAME} berhasil diinisialisasi.")

# --- Fungsi Watchlist ---

def add_to_watchlist(symbol, price=0, signal="", score=0):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO watchlist (symbol, last_price, last_signal, last_score) VALUES (?, ?, ?, ?)",
            (symbol.upper(), price, signal, score)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB Error] add_to_watchlist: {e}")
        return False
    finally:
        conn.close()

def remove_from_watchlist(symbol):
    conn = get_db_connection()
    conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
    conn.commit()
    conn.close()

def get_watchlist():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM watchlist ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Fungsi Cache ---

def save_to_cache(symbol, data):
    conn = get_db_connection()
    try:
        json_data = json.dumps(data)
        conn.execute(
            "INSERT OR REPLACE INTO analysis_cache (symbol, data, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (symbol.upper(), json_data)
        )
        conn.commit()
    except Exception as e:
        print(f"[DB Error] save_to_cache: {e}")
    finally:
        conn.close()

def get_from_cache(symbol, max_age_minutes=30):
    """Ambil data dari cache jika belum kadaluarsa"""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT data, timestamp FROM analysis_cache WHERE symbol = ?", 
        (symbol.upper(),)
    ).fetchone()
    conn.close()
    
    if row:
        timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
        age = (datetime.now() - timestamp).total_seconds() / 60
        if age <= max_age_minutes:
            return json.loads(row['data'])
    return None

# --- Fungsi Screener ---

def save_screener_result(symbol, result, scanner_type='LQ45'):
    conn = get_db_connection()
    try:
        conn.execute(
            '''INSERT OR REPLACE INTO screener_results 
               (symbol, scanner_type, signal, score, buy_price, sell_target, stop_loss, updated_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
            (symbol.upper(), scanner_type, result['signal'], result['score'], 
             result['buy_price'], result['sell_target'], result['stop_loss'])
        )
        conn.commit()
    except Exception as e:
        print(f"[DB Error] save_screener_result: {e}")
    finally:
        conn.close()

def get_screener_results(scanner_type=None):
    conn = get_db_connection()
    if scanner_type:
        rows = conn.execute("SELECT * FROM screener_results WHERE scanner_type = ? ORDER BY score DESC", (scanner_type,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM screener_results ORDER BY score DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- Fungsi Telegram ---

def save_chat_id(chat_id):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO telegram_settings (chat_id) VALUES (?)",
            (str(chat_id),)
        )
        conn.commit()
    except Exception as e:
        print(f"[DB Error] save_chat_id: {e}")
    finally:
        conn.close()

def get_all_chat_ids():
    conn = get_db_connection()
    rows = conn.execute("SELECT chat_id FROM telegram_settings WHERE is_active = 1").fetchall()
    conn.close()
    return [row['chat_id'] for row in rows]

if __name__ == "__main__":
    init_db()
