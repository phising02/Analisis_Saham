def generate_commentary(data):
    """
    Menghasilkan narasi analisis investasi profesional (Investment Thesis)
    berdasarkan gabungan data Teknikal, Fundamental, dan Bandarmology.
    """
    symbol = data.get('symbol', 'Saham ini')
    sig = data.get('signal', 'NEUTRAL')
    score = data.get('score', 0)
    fund = data.get('fundamental', {})
    ff = data.get('money_flow', {})
    fib_zone = data.get('fib_zone', 'N/A')
    
    # 1. Opening & Signal Context
    intro = f"Berdasarkan algoritma Astronacci Pro, **{symbol}** menunjukkan sinyal **{sig.replace('_', ' ')}** dengan skor keyakinan **{score}/100**."
    
    # 2. Technical / Fibonacci Analysis
    tech_parts = []
    if "Golden Zone" in fib_zone:
        tech_parts.append(f"Harga saat ini berada di *Golden Zone* Fibonacci, area pantulan yang secara historis memiliki probabilitas tinggi untuk pembalikan arah.")
    elif "Deep Value" in fib_zone:
        tech_parts.append(f"Saham ini sedang berada di zona *Deep Value* (diskon besar), area yang sangat menarik bagi investor jangka panjang.")
    
    if any("Bullish Cross" in p for p in data.get('patterns', [])):
        tech_parts.append("Terdeteksi momentum positif dari indikator Stochastic yang baru saja melakukan *bullish cross*.")
    
    tech_txt = " ".join(tech_parts) if tech_parts else "Secara teknikal, harga masih berkonsolidasi di zona Fibonacci saat ini."
    
    # 3. Fundamental Context
    fund_parts = []
    pe = fund.get('pe_ratio', 0)
    pbv = fund.get('pbv_ratio', 0)
    div = fund.get('dividend_yield', 0)
    
    if pe > 0 and pe < 15:
        fund_parts.append(f"Valuasi P/E ({pe}x) tergolong kompetitif.")
    elif pe > 30:
        fund_parts.append(f"Namun perlu waspada karena P/E ({pe}x) sudah cukup tinggi secara historis.")
        
    if pbv > 0 and pbv < 1.2:
        fund_parts.append(f"Ditambah P/BV yang di bawah 1.2x, memberikan margin keamanan yang baik.")
        
    if div > 2:
        fund_parts.append(f"Adanya potensi *dividend yield* sebesar {div}% menjadi daya tarik tambahan bagi pemegang saham.")
        
    fund_txt = " ".join(fund_parts) if fund_parts else "Data fundamental menunjukkan kondisi emiten yang stabil saat ini."
    
    # 4. Bandarmology / Foreign Flow
    ff_txt = ""
    if ff.get('status') == "ACCUMULATION":
        ff_txt = f"Yang menarik, kami mendeteksi adanya **akumulasi agresif** dari investor besar (*Smart Money*) dalam 5 hari terakhir, yang memperkuat pondasi kenaikan harga."
    elif ff.get('status') == "DISTRIBUTION":
        ff_txt = f"Hati-hati, meskipun ada aspek teknikal yang menarik, terdeteksi adanya **distribusi** (penjualan) oleh pihak besar yang bisa menghambat laju kenaikan."
    else:
        ff_txt = "Pergerakan volume saat ini masih cenderung netral, menunjukkan pasar yang sedang menunggu momentum baru."
        
    # 5. Conclusion / Investment Thesis
    conclusion = ""
    if score >= 70:
        conclusion = "### 🚀 Kesimpulan: Konfluensi Sangat Kuat\nAnalisis kami menyimpulkan ini adalah peluang investasi yang solid. Perpaduan Fibonacci, akumulasi volume, dan dukungan fundamental memberikan probabilitas kemenangan yang tinggi."
    elif score >= 40:
        conclusion = "### 📈 Kesimpulan: Peluang Terukur\nSaham layak dipantau untuk entri bertahap. Pastikan untuk disiplin pada level Stop Loss yang telah ditentukan."
    else:
        conclusion = "### ⚠️ Kesimpulan: Wait & See\nBelum ada konfirmasi yang cukup kuat. Sebaiknya menunggu harga menyentuh level support kunci sebelum mengambil keputusan."

    return f"""
{intro}

**Anatomi Analisis:**
- **Analisis Teknikal:** {tech_txt}
- **Kondisi Fundamental:** {fund_txt}
- **Smart Money Flow:** {ff_txt}

{conclusion}
""".strip()
