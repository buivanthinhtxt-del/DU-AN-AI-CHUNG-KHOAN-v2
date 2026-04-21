import urllib.request
import json

url = 'http://localhost:8000/api/analyze'
data = json.dumps({"symbol": "HPG"}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        ai_report = result.get('ai_report', {})
        analysis = ai_report.get('analysis', '')
        with open('debug_output.txt', 'w', encoding='utf-8') as f:
            f.write(analysis)
        print("Predictions Length:", len(ai_report.get('predictions', [])))
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
