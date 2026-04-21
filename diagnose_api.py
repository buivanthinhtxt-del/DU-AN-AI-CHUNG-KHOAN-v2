import urllib.request
import json
import time

url = 'http://localhost:8000/api/analyze'
data = json.dumps({"symbol": "HPG"}).encode('utf-8')
headers = {'Content-Type': 'application/json'}
req = urllib.request.Request(url, data=data, headers=headers)

print("[*] Sending request to local API...")
start_time = time.time()
try:
    with urllib.request.urlopen(req, timeout=60) as response:
        duration = time.time() - start_time
        print(f"[*] Received response in {duration:.2f}s")
        result = json.loads(response.read().decode('utf-8'))
        print("[*] Keys in response:", result.keys())
        print("[*] AI Report Keys:", result.get('ai_report', {}).keys())
        print("[*] AI Report Analysis Preview:", result.get('ai_report', {}).get('analysis', '')[:100])
        print("[*] Predictions Count:", len(result.get('ai_report', {}).get('predictions', [])))
        if not result.get('ai_report', {}).get('predictions'):
             print("[!] WARNING: Predictions list is EMPTY.")
except Exception as e:
    print(f"[!] Error: {e}")
    if hasattr(e, 'read'):
        print("[!] Response Body:", e.read().decode('utf-8'))
