import argparse
from fastapi.testclient import TestClient
import sys
import os

# Add directory to sys.path so we can import api
sys.path.append(r'd:\2- LÀM VIỆC\2- github du an 1\DU-AN-AI-CHUNG-KHOAN')
from api import app

client = TestClient(app)
response = client.post("/api/analyze", json={"symbol": "HPG"})
print("Status Code:", response.status_code)
if response.status_code == 200:
    data = response.json()
    print("Keys in response:", data.keys())
    print("History length:", len(data.get('history', [])))
    if data.get('history'):
        print("First history item:", data['history'][0])
    ai_report = data.get('ai_report', {})
    print("AI Analysis length:", len(ai_report.get('analysis', '')))
    print("AI Predictions length:", len(ai_report.get('predictions', [])))
else:
    print("Error:", response.text)
