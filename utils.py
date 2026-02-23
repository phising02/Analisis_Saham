import os
import re
import json

LOG_DIR = r"C:\Users\LENOVO\AppData\Roaming\Stockbit\com.stockbit.desktop\logs"

def get_latest_token():
    """
    Mencari token akses terbaru dari beberapa file log terakhir.
    """
    try:
        # Cari file log dan urutkan berdasarkan waktu modifikasi (terbaru dulu)
        files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.startswith("runtime.log")]
        if not files:
            return None
        
        files.sort(key=os.path.getmtime, reverse=True)
        
        # Cari di 3 file log terbaru
        for log_file in files[:3]:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Cari pola access_token di dalam log
                matches = re.findall(r'"access_token":\s*String\("([^"]+)"\)', content)
                if matches:
                    return matches[-1] # Ambil yang paling baru (terakhir) di file tersebut
                
    except Exception as e:
        print(f"Error extracting token: {e}")
    return None

if __name__ == "__main__":
    token = get_latest_token()
    if token:
        print(f"Token Berhasil Diambil: {token[:20]}...")
    else:
        print("Token Tidak Ditemukan.")
