"""
NEWS FETCHER – Berita Saham dari Sumber Terpercaya Indonesia
Menggunakan requests + XML parsing (tanpa feedparser).
Setiap berita menyertakan nama sumber dan link asli.
"""
import requests
import xml.etree.ElementTree as ET
import re
from datetime import datetime
from html import unescape

# ============================================================
# SUMBER BERITA TERPERCAYA (RSS FEEDS)
# ============================================================

NEWS_SOURCES = [
    {
        "name": "CNBC Indonesia",
        "icon": "📺",
        "url": "https://www.cnbcindonesia.com/market/rss",
        "color": "#0070f3"
    },
    {
        "name": "Kontan",  
        "icon": "📰",
        "url": "https://www.kontan.co.id/rss/saham",
        "color": "#e11d48"
    },
    {
        "name": "Bisnis.com",
        "icon": "💼",
        "url": "https://market.bisnis.com/rss",
        "color": "#059669"
    },
]

# Google News RSS untuk berita per saham
GOOGLE_NEWS_TEMPLATE = "https://news.google.com/rss/search?q={query}+saham&hl=id&gl=ID&ceid=ID:id"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def clean_html(text):
    """Bersihkan tag HTML dari deskripsi RSS"""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    clean = unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:250]


def parse_rss(xml_text):
    """Parse RSS XML menjadi list of dict"""
    items = []
    try:
        root = ET.fromstring(xml_text)
        # Cari semua <item> di dalam <channel>
        for item in root.iter('item'):
            title_el = item.find('title')
            link_el = item.find('link')
            desc_el = item.find('description')
            date_el = item.find('pubDate')
            
            title = title_el.text.strip() if title_el is not None and title_el.text else None
            if not title:
                continue
                
            items.append({
                "title": title,
                "link": link_el.text.strip() if link_el is not None and link_el.text else "#",
                "summary": clean_html(desc_el.text if desc_el is not None and desc_el.text else ""),
                "date_raw": date_el.text.strip() if date_el is not None and date_el.text else None,
            })
    except ET.ParseError as e:
        print(f"[WARN] XML parse error: {e}")
    return items


def format_date(date_str):
    """Parse berbagai format tanggal RSS ke format ringkas"""
    if not date_str:
        return "Baru"
    
    # Common RSS date formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%d %b %Y %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            return dt.strftime('%d %b %Y, %H:%M')
        except ValueError:
            continue
    
    return "Baru"


def fetch_general_news(max_per_source=5):
    """
    Ambil berita umum pasar saham dari semua sumber terpercaya.
    """
    all_news = []
    
    for source in NEWS_SOURCES:
        try:
            # Menggunakan verify=False untuk menghindari masalah sertifikat SSL pada beberapa sistem Windows
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            resp = requests.get(source["url"], headers=HEADERS, timeout=10, verify=False)
            if resp.status_code != 200:
                continue
            
            items = parse_rss(resp.text)
            
            for item in items[:max_per_source]:
                all_news.append({
                    "title": item["title"],
                    "link": item["link"],
                    "source": source["name"],
                    "source_icon": source["icon"],
                    "source_color": source["color"],
                    "date": format_date(item["date_raw"]),
                    "summary": item["summary"]
                })
                
        except Exception as e:
            print(f"[WARN] Gagal mengambil berita dari {source['name']}: {e}")
            continue
    
    return all_news


def fetch_stock_news(symbol, max_results=8):
    """
    Cari berita spesifik untuk saham tertentu via Google News RSS.
    Sumber asli setiap artikel tetap terlihat jelas.
    """
    url = GOOGLE_NEWS_TEMPLATE.format(query=symbol)
    news = []
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            return news
        
        items = parse_rss(resp.text)
        
        for item in items[:max_results]:
            title = item["title"]
            source_name = "Berita"
            
            # Google News format: "Judul Berita - Nama Sumber"
            if ' - ' in title:
                parts = title.rsplit(' - ', 1)
                if len(parts) == 2:
                    title = parts[0].strip()
                    source_name = parts[1].strip()
            
            news.append({
                "title": title,
                "link": item["link"],
                "source": source_name,
                "source_icon": "🔗",
                "source_color": "#6b7280",
                "date": format_date(item["date_raw"]),
                "summary": clean_html(item["summary"])
            })
            
    except Exception as e:
        print(f"[WARN] Gagal mengambil berita untuk {symbol}: {e}")
    
    return news


# ============================================================
# SENTIMEN BERITA (Keyword-Based Analysis)
# ============================================================

# Kata positif (Bahasa Indonesia + Inggris)
POSITIVE_WORDS = [
    # ID - kuat (bobot 2)
    'melonjak', 'meroket', 'cetak rekor', 'all time high', 'laba bersih naik',
    'dividen jumbo', 'akuisisi', 'ekspansi besar', 'pertumbuhan laba',
    'buyback', 'laba bersih melesat', 'dana segar', 'kerjasama strategis',
    'dividen meningkat', 'kinerja cemerlang', 'prospek positif',
    # ID - standar (bobot 1)
    'naik', 'untung', 'laba', 'profit', 'dividen', 'cerah', 'positif',
    'menguat', 'rally', 'rebound', 'bangkit', 'surplus', 'tumbuh',
    'optimis', 'prospek', 'peluang', 'kinerja baik', 'pendapatan naik',
    'target harga', 'rekomendasi beli', 'buy', 'outperform', 'overweight',
    'pemulihan', 'disetujui', 'lolos', 'proyek baru', 'efisiensi',
    # EN
    'bullish', 'upgrade', 'growth', 'revenue up', 'record high', 'breakout',
    'strong buy', 'accumulate', 'upside', 'beat estimates', 'exceeded',
]

# Kata negatif (Bahasa Indonesia + Inggris)
NEGATIVE_WORDS = [
    # ID - kuat (bobot 2)
    'anjlok', 'ambruk', 'terjun bebas', 'bangkrut', 'gagal bayar',
    'fraud', 'korupsi', 'default', 'delisting', 'suspensi', 'wanprestasi',
    'gugatan', 'kasus hukum', 'pailit', 'aset disita',
    # ID - standar (bobot 1)
    'turun', 'rugi', 'merosot', 'jatuh', 'melemah', 'tertekan',
    'negatif', 'defisit', 'utang', 'susut', 'terkoreksi', 'bearish',
    'tekanan', 'risiko', 'pelemahan', 'penurunan', 'kinerja buruk',
    'rekomendasi jual', 'sell', 'downgrade', 'underperform', 'underweight',
    'prospek suram', 'pendapatan turun', 'rugi bersih', 'inflasi', 'beban naik',
    # EN
    'crash', 'decline', 'loss', 'miss estimates', 'downside', 'warning',
    'cut', 'reduce', 'weak', 'below', 'concern', 'disappointment',
]

STRONG_POSITIVE = {'melonjak', 'meroket', 'cetak rekor', 'all time high',
                   'dividen jumbo', 'pertumbuhan laba', 'strong buy',
                   'laba bersih melesat', 'akuisisi'}
STRONG_NEGATIVE = {'anjlok', 'ambruk', 'terjun bebas', 'bangkrut',
                   'gagal bayar', 'fraud', 'korupsi', 'default', 'crash',
                   'pailit', 'suspensi'}


def analyze_sentiment(symbol, max_news=10):
    """
    Analisis sentimen berita untuk saham tertentu.
    Return: { score: -100..+100, positive: N, negative: N, neutral: N, 
              label: str, headlines: list }
    """
    news = fetch_stock_news(symbol, max_results=max_news)
    
    if not news:
        return {
            "score": 0, "positive": 0, "negative": 0, "neutral": 0,
            "label": "Tidak Ada Berita", "headlines": [],
            "detail": "Tidak ada berita ditemukan"
        }
    
    pos_count = 0
    neg_count = 0
    neutral_count = 0
    total_weight = 0
    headlines = []
    
    for item in news:
        title = item.get("title", "").lower()
        summary = item.get("summary", "").lower()
        text = title + " " + summary
        
        pos_hits = 0
        neg_hits = 0
        
        for word in POSITIVE_WORDS:
            if word in text:
                weight = 2 if word in STRONG_POSITIVE else 1
                pos_hits += weight
        
        for word in NEGATIVE_WORDS:
            if word in text:
                weight = 2 if word in STRONG_NEGATIVE else 1
                neg_hits += weight
        
        if pos_hits > neg_hits:
            pos_count += 1
            sentiment = "positive"
        elif neg_hits > pos_hits:
            neg_count += 1
            sentiment = "negative"
        else:
            neutral_count += 1
            sentiment = "neutral"
        
        total_weight += (pos_hits - neg_hits)
        headlines.append({
            "title": item.get("title", ""),
            "sentiment": sentiment,
            "source": item.get("source", "")
        })
    
    # Normalize score ke -100..+100
    max_possible = max(len(news) * 4, 1)  # Asumsi max 4 keywords per article
    raw_score = total_weight / max_possible * 100
    score = max(-100, min(100, round(raw_score)))
    
    # Label
    if score >= 30:
        label = "Sangat Positif"
    elif score >= 10:
        label = "Positif"
    elif score >= -10:
        label = "Netral"
    elif score >= -30:
        label = "Negatif"
    else:
        label = "Sangat Negatif"
    
    return {
        "score": score,
        "positive": pos_count,
        "negative": neg_count,
        "neutral": neutral_count,
        "label": label,
        "headlines": headlines,
        "detail": f"{pos_count} positif, {neg_count} negatif, {neutral_count} netral"
    }


if __name__ == "__main__":
    print("=== Berita Umum Pasar Saham ===")
    news = fetch_general_news(max_per_source=3)
    if news:
        for n in news[:8]:
            print(f"  [{n['source']}] {n['title']}")
            print(f"    {n['date']} | {n['link'][:80]}")
    else:
        print("  Tidak ada berita yang berhasil diambil.")
    
    print(f"\n  Total: {len(news)} berita")
    
    print("\n=== Berita Spesifik BBCA ===")
    stock_news = fetch_stock_news("BBCA", max_results=3)
    for n in stock_news:
        print(f"  [{n['source']}] {n['title']}")
