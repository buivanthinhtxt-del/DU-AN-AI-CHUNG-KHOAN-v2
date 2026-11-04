import os
import json
import time
from pathlib import Path

CACHE_DIR = Path(".cache")

def _init_cache_dir():
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True)

def get_cache(key: str, ttl_seconds: int):
    """Retrieve data from cache if not expired."""
    _init_cache_dir()
    cache_file = CACHE_DIR / f"{key}.json"
    
    if not cache_file.exists():
        return None
        
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Check TTL
        if time.time() - data.get("timestamp", 0) > ttl_seconds:
            return None # Expired
            
        return data.get("payload")
    except Exception as e:
        print(f"[!] Lỗi đọc cache {key}: {e}")
        return None

def set_cache(key: str, payload: dict):
    """Save data to cache file."""
    _init_cache_dir()
    cache_file = CACHE_DIR / f"{key}.json"
    
    try:
        data = {
            "timestamp": time.time(),
            "payload": payload
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[!] Lỗi ghi cache {key}: {e}")
