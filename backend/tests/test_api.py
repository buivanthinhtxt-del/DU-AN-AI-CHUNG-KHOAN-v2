import argparse
from fastapi.testclient import TestClient
import sys
import os
import json

from pathlib import Path
# Add backend directory to sys.path so we can import api
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api import app

client = TestClient(app)

def pretty_print(label: str, data):
    """In dữ liệu JSON sang định dạng có thụt lề, dễ copy."""
    print(f"\n--- {label} ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("--- End ---\n")

print("--- Testing /api/market_data ---")
response_market = client.post("/api/market_data", json={"symbol": "HPG"})
print("Status Code:", response_market.status_code)
assert response_market.status_code == 200, f"Expected 200, got {response_market.status_code}: {response_market.text}"

data = response_market.json()
print("Keys in response:", data.keys())
print("History length:", len(data.get('history', [])))
assert len(data.get('history', [])) > 0, "Market history should not be empty"

latest_hist = data['history'][-1]
print("Latest history item date:", latest_hist.get('Date'))
print("Latest indicators:", data.get('indicators', {}))
assert 'RSI' in data.get('indicators', {}), "Indicators should contain RSI"
assert 'EMA10' in data.get('indicators', {}), "Indicators should contain EMA10"
assert 'SMA20' in data.get('indicators', {}), "Indicators should contain SMA20"

print("\n--- Testing /api/ai_report ---")
response_ai = client.post("/api/ai_report", json={"symbol": "HPG"})
print("Status Code:", response_ai.status_code)
assert response_ai.status_code == 200, f"Expected 200, got {response_ai.status_code}: {response_ai.text}"

data_ai = response_ai.json()
ai_report = data_ai.get('ai_report', {})
pretty_print("AI Report JSON", ai_report)

print("Overall Score:", ai_report.get('overall_score'))
print("AI Analysis length:", len(ai_report.get('analysis', '')))
print("AI Predictions length:", len(ai_report.get('predictions', [])))

assert ai_report.get('overall_score') is not None, "Overall score must be present"
assert len(ai_report.get('predictions', [])) >= 4, "Predictions must have at least 4 items"

# Verify T+2.5 exists with days_future = 2
predictions = ai_report.get('predictions', [])
t25_found = any(p.get('days_future') == 2 for p in predictions)
assert t25_found, f"Expected prediction with days_future=2 (T+2.5), found: {predictions}"

# Báo cáo v3: kế hoạch giao dịch có cấu trúc & nhất quán (dù là AI hay bản định lượng dự phòng)
print("Engine:", ai_report.get('engine'), "| Data quality:", ai_report.get('data_quality'))
tp = ai_report.get('trade_plan') or {}
assert tp, "trade_plan must be present"
assert tp['stop_loss'] < tp['entry_low'] <= tp['entry_high'] < tp['target_1'] <= tp['target_2'], f"Inconsistent trade plan: {tp}"
scen = ai_report.get('scenarios') or []
assert scen and sum(s['probability'] for s in scen) == 100, f"Scenario probabilities must sum to 100: {scen}"
assert ai_report.get('quant_snapshot', {}).get('supports') is not None, "quant_snapshot.supports must be present"
assert "P/E: 10.5" not in ai_report.get('analysis', ''), "Hardcoded fake fundamentals must not appear"

print("\n--- Testing Watchlist APIs ---")
resp_wl_get = client.get("/api/watchlist")
assert resp_wl_get.status_code == 200, f"Watchlist GET failed: {resp_wl_get.status_code}"
resp_wl_add = client.post("/api/watchlist", json={"symbol": "HPG"})
assert resp_wl_add.status_code == 200, f"Watchlist POST failed: {resp_wl_add.status_code}"
resp_wl_del = client.delete("/api/watchlist/HPG")
assert resp_wl_del.status_code == 200, f"Watchlist DELETE failed: {resp_wl_del.status_code}"

print("\n--- Testing /api/chat ---")
resp_chat = client.post("/api/chat", json={"message": "Tin tức HPG gần đây?", "symbol": "HPG"})
assert resp_chat.status_code == 200, f"Chat API failed: {resp_chat.status_code}: {resp_chat.text}"
chat_data = resp_chat.json()
print("Chat reply length:", len(chat_data.get("reply", "")))
print("Chat sources count:", len(chat_data.get("sources", [])))
assert len(chat_data.get("reply", "")) > 0, "Chat reply should not be empty"

print("\n[+] ALL API TESTS PASSED SUCCESSFULLY!")
