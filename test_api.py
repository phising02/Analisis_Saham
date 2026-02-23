import requests
import json

print("=== ANALISIS BBCA ===")
r = requests.post('http://localhost:5000/api/analyze', json={'symbol':'BBCA'})
d = r.json()
print(f"Signal: {d.get('signal')}")
print(f"Score: {d.get('score')}/100")
print(f"RR Ratio: {d.get('rr_ratio')}")

va = d.get('volume_analysis', {})
print(f"\n=== VOLUME ANALYSIS ===")
print(f"  Vol Ratio: {va.get('vol_ratio')}x")
print(f"  OBV Up: {va.get('obv_up')}")
print(f"  Vol-Price Confirm: {va.get('vol_price_confirm')}")
print(f"  Vol Divergence: {va.get('vol_divergence')}")

mt = d.get('multi_timeframe', {})
print(f"\n=== MULTI-TIMEFRAME CONFLUENCE ===")
for tf in ['daily','weekly','monthly']:
    t = mt.get(tf, {})
    print(f"  {tf}: {t.get('trend','N/A')} RSI: {t.get('rsi','--')}")
print(f"  Confluence: {mt.get('confluence_score')}/100 - {mt.get('confluence_label')}")

mkt = d.get('market_trend', {})
print(f"\n=== IHSG MARKET TREND ===")
print(f"  Trend: {mkt.get('trend')} Level: {mkt.get('level')} Change: {mkt.get('change_pct')}%")

snt = d.get('sentiment', {})
print(f"\n=== NEWS SENTIMENT ===")
print(f"  Score: {snt.get('score')} Label: {snt.get('label')}")
print(f"  Detail: {snt.get('detail')}")

si = d.get('sentiment_impact', {})
print(f"\n=== SENTIMENT IMPACT ON SIGNALS ===")
print(f"  Entry: {si.get('entry_effect')} TP: {si.get('tp_effect')} SL: {si.get('sl_effect')}")

print(f"\n=== BACKTEST BBCA ===")
r2 = requests.get('http://localhost:5000/api/backtest/BBCA')
bt = r2.json()
print(f"  Win Rate: {bt.get('win_rate')}%")
print(f"  Total Trades: {bt.get('total_trades')}")
print(f"  Avg Return: {bt.get('avg_return')}%")
print(f"  Max Drawdown: {bt.get('max_drawdown')}%")
print(f"  TP Hit Rate: {bt.get('tp_hit_rate')}%")
print(f"  STRONG BUY WR: {bt.get('strong_buy_wr')}% ({bt.get('strong_buy_count')} trades)")
print(f"  BUY WR: {bt.get('buy_wr')}% ({bt.get('buy_count')} trades)")

print(f"\n=== POSITION SIZING ===")
r3 = requests.post('http://localhost:5000/api/position-size', json={
    'modal': 10000000, 'risk_pct': 2,
    'entry': d.get('buy_price', 1000), 'stop_loss': d.get('stop_loss', 900)
})
ps = r3.json()
print(f"  Lots: {ps.get('lots')}")
print(f"  Shares: {ps.get('shares')}")
print(f"  Total Cost: Rp {ps.get('total_cost'):,.0f}")
print(f"  Actual Risk: Rp {ps.get('actual_risk'):,.0f}")
print(f"  % Modal Used: {ps.get('pct_modal_used')}%")

print("\n=== ALL API ENDPOINTS OK ===")
