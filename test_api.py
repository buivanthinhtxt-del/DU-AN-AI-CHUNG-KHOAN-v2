import argparse
from fastapi.testclient import TestClient
import sys
import os
import json

# Add directory to sys.path so we can import api
sys.path.append(r'd:\2- LÀM VIỆC\2- github du an 1\DU-AN-AI-CHUNG-KHOAN')
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
if response_market.status_code == 200:
    data = response_market.json()
    print("Keys in response:", data.keys())
    print("History length:", len(data.get('history', [])))
    if data.get('history'):
        print("First history item:", data['history'][0])
else:
    print("Error:", response_market.text)

print("\n--- Testing /api/ai_report ---")
response_ai = client.post("/api/ai_report", json={"symbol": "HPG"})
print("Status Code:", response_ai.status_code)
if response_ai.status_code == 200:
    data_ai = response_ai.json()
    ai_report = data_ai.get('ai_report', {})
    
    # In toàn bộ JSON AI Report để dễ copy-paste
    pretty_print("AI Report JSON", ai_report)
    
    print("Overall Score:", ai_report.get('overall_score'))
    print("AI Analysis length:", len(ai_report.get('analysis', '')))
    print("AI Predictions length:", len(ai_report.get('predictions', [])))
else:
    print("Error:", response_ai.text)
