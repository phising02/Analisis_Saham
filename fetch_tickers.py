import requests
import re
import json

def fetch_all_idx_tickers():
    print("Fetching tickers from laporankeuangan.com...")
    url = "https://www.laporankeuangan.com/daftar-saham-bei/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        # Look for 4-letter uppercase words that are stock codes
        # In this site, they are usually in table cells or list items
        # Let's try to find all 4 letter uppercase words
        raw_tickers = re.findall(r'\b[A-Z]{4}\b', r.text)
        
        # Filter common words and duplicates
        exclude = {"IDX", "IHSG", "LIST", "NAME", "POST", "DATE", "JSON", "HTTP", "HTML", "NEWS", "OPEN"}
        valid_tickers = [t for t in set(raw_tickers) if t not in exclude]
        
        if len(valid_tickers) > 500: # We expect around 800-900
            return sorted(valid_tickers)
        else:
            print(f"Warning: Only found {len(valid_tickers)} tickers. This might be incomplete.")
            return sorted(valid_tickers)
            
    except Exception as e:
        print(f"Scraper failed: {e}")
    return []

if __name__ == "__main__":
    tickers = fetch_all_idx_tickers()
    if tickers:
        print(f"Success! Found {len(tickers)} tickers.")
        with open("idx_tickers.json", "w") as f:
            json.dump(tickers, f)
        print("Final List Saved.")
    else:
        print("Failed to fetch tickers.")
        # Fallback to current list if search failed completely
        fallback = ["ADRO", "ASII", "BBCA", "BBRI", "BMRI", "GOTO", "TLKM", "UNVR"] # and many more...
