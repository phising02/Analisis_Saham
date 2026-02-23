import requests
import json
import sys

try:
    print("Memanggil API untuk BBCA...")
    r = requests.post('http://localhost:5000/api/analyze', json={'symbol':'BBCA'}, timeout=30)
    if r.status_code != 200:
        print(f"Error: Server returned status {r.status_code}")
        print(r.text)
        sys.exit(1)
    
    d = r.json()
    print("\n--- HASIL ANALISIS ---")
    print(f"Symbol: {d.get('symbol')}")
    print(f"Signal: {d.get('signal')}")
    print(f"Score:  {d.get('score')}/100")
    
    print("\n--- SENTIMEN ---")
    snt = d.get('sentiment', {})
    print(f"Label:  {snt.get('label')}")
    print(f"Score:  {snt.get('score')}")
    
    si = d.get('sentiment_impact', {})
    print(f"Impact: Entry {si.get('entry_effect')}, TP {si.get('tp_effect')}, SL {si.get('sl_effect')}")
    
    print("\n--- REKOMENDASI ---")
    print(f"Buy:    {d.get('buy_price')}")
    print(f"TP:     {d.get('sell_target')}")
    print(f"SL:     {d.get('stop_loss')}")
    
    print("\nVERIFIKASI BERHASIL!")
except Exception as e:
    print(f"TERJADI KESALAHAN: {e}")
