import requests
from database import save_chat_id, get_all_chat_ids

# Token dari user
BOT_TOKEN = "8337142693:AAEJNoCxjKzfl9pgsRHjh1Al261imRIVSDM"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_telegram_msg(chat_id, text):
    """Kirim pesan teks ke chat_id tertentu"""
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json()
    except Exception as e:
        print(f"[TELEGRAM] Error sending message to {chat_id}: {e}")
        return None

def broadcast_signal(symbol, result):
    """Kirim notifikasi sinyal ke semua user yang terdaftar"""
    chat_ids = get_all_chat_ids()
    if not chat_ids:
        print("[TELEGRAM] Tidak ada user terdaftar (Chat ID kosong)")
        return

    # Emoji berdasarkan sinyal
    sig = result['signal']
    emoji = "🟢" if "BUY" in sig else ("🔴" if "SELL" in sig else "⚪")
    score_emoji = "🔥" if result['score'] >= 80 else "⭐"

    msg = (
        f"<b>{emoji} SINYAL BARU: {symbol}</b>\n\n"
        f"{score_emoji} Skor: <b>{result['score']}/100</b>\n"
        f"📢 Sinyal: <b>{sig.replace('_', ' ')}</b>\n\n"
        f"🎯 Entry: Rp {format_num(result['buy_price'])}\n"
        f"🚀 Target: Rp {format_num(result['sell_target'])}\n"
        f"🛑 Stop Loss: Rp {format_num(result['stop_loss'])}\n\n"
        f"<i>Astronacci Pro Analysis</i>"
    )

    for cid in chat_ids:
        send_telegram_msg(cid, msg)
        print(f"[TELEGRAM] Notifikasi {symbol} dikirim ke {cid}")

def format_num(n):
    return "{:,}".format(int(n)).replace(",", ".")

def check_updates():
    """Cek pesan masuk bot untuk mendapatkan Chat ID"""
    url = f"{BASE_URL}/getUpdates"
    try:
        resp = requests.get(url, timeout=10).json()
        if not resp.get("ok"):
            return
        
        for update in resp.get("result", []):
            msg = update.get("message")
            if msg and "chat" in msg:
                cid = msg["chat"]["id"]
                text = msg.get("text", "")
                
                if text == "/start":
                    save_chat_id(cid)
                    send_telegram_msg(cid, "<b>Selamat Datang!</b>\n\nChat ID Anda telah terdaftar. Anda akan menerima notifikasi sinyal saham otomatis dari Astronacci Pro.")
                    print(f"[TELEGRAM] User baru terdaftar: {cid}")
    except Exception as e:
        print(f"[TELEGRAM] Error checking updates: {e}")

if __name__ == "__main__":
    # Test running
    print("[TELEGRAM] Memeriksa pendaftar baru...")
    check_updates()
