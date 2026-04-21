import urllib.request
import json

url = 'http://localhost:8000/api/analyze'
data = json.dumps({"symbol": "HPG"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        print("Success:", result.keys())
        hist = result.get('history', [])
        print("History len:", len(hist))
        print("AI Predictions:", result.get('ai_report', {}).get('predictions'))
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
