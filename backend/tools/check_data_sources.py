"""
Kiểm tra sức khỏe từng nguồn dữ liệu giá (SSI FastConnect / từng API công khai / vnstock / kho cục bộ).

    .venv/Scripts/python.exe backend/tools/check_data_sources.py          # mặc định HPG
    .venv/Scripts/python.exe backend/tools/check_data_sources.py FPT

Hoặc khi backend đang chạy: GET http://127.0.0.1:8000/api/data_sources/health?symbol=HPG
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging  # noqa: E402

logging.basicConfig(level=logging.ERROR)

from data_sources import check_sources, provider_chain  # noqa: E402


def main():
    sym = (sys.argv[1] if len(sys.argv) > 1 else "HPG").upper()
    print(f"Chuỗi nguồn hiện tại: {' → '.join(p.name for p in provider_chain())}   (đổi bằng DATA_SOURCES trong .env)\n")
    for r in check_sources(sym):
        mark = "✅" if r.get("ok") else ("⏸️" if not r.get("enabled") else "❌")
        detail = (
            f"{r.get('rows')} phiên, đến {r.get('last_date')}, giá cuối {r.get('last_close')}"
            if r.get("ok") else (r.get("error") or r.get("detail") or "")
        )
        lat = f" ({r['latency_s']}s)" if "latency_s" in r else ""
        print(f"{mark} {r['source']:<18} {detail}{lat}")


if __name__ == "__main__":
    main()
