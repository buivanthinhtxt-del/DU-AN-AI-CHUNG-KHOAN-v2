import os
import json
import time
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / ".cache"

def _init_cache_dir():
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cache(key: str, ttl_seconds: int):
    """Retrieve data from cache if not expired. Gracefully handles corrupted files and JSONDecodeError."""
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
    except (json.decoder.JSONDecodeError, ValueError) as e:
        print(f"[!] File cache {key} bị hỏng ({type(e).__name__}): {e}. Tự động dọn dẹp file lỗi.")
        try:
            if cache_file.exists():
                cache_file.unlink(missing_ok=True)
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"[!] Lỗi đọc cache {key}: {e}")
        return None

def set_cache(key: str, payload: dict):
    """Save data to cache file atomically using tempfile and os.replace to prevent race conditions and 0-byte corruption."""
    _init_cache_dir()
    cache_file = CACHE_DIR / f"{key}.json"
    
    temp_path = None
    try:
        data = {
            "timestamp": time.time(),
            "payload": payload
        }
        # Tạo tệp tạm trong CÙNG thư mục CACHE_DIR để đảm bảo cùng phân vùng ổ đĩa cho os.replace nguyên tử
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(CACHE_DIR),
            prefix=f"tmp_{key}_",
            suffix=".json",
            delete=False,
            encoding="utf-8"
        ) as tmp_f:
            json.dump(data, tmp_f, ensure_ascii=False, indent=2)
            tmp_f.flush()
            os.fsync(tmp_f.fileno())
            temp_path = tmp_f.name
            
        # Atomic rename/replace với cơ chế retry ngắn cho Windows file locks
        for attempt in range(5):
            try:
                os.replace(temp_path, str(cache_file))
                break
            except (PermissionError, OSError) as pe:
                if attempt == 4:
                    raise pe
                time.sleep(0.01 * (attempt + 1))
    except Exception as e:
        print(f"[!] Lỗi ghi cache nguyên tử {key}: {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
