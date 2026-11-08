"""
Tải trước / cập nhật lịch sử giá vào kho CSV cục bộ (backend/data/ohlcv/) qua chuỗi nguồn của data_sources
(SSI FastConnect → API công khai các CTCK → vnstock), để hệ thống vẫn có dữ liệu phân tích kể cả khi mọi nguồn
trực tuyến tạm hỏng.

Cách dùng (từ thư mục gốc dự án):
    .venv/Scripts/python.exe backend/tools/backfill_local_store.py              # mọi mã trong SECTOR_MAP + chỉ số, 5 năm
    .venv/Scripts/python.exe backend/tools/backfill_local_store.py HPG FPT VNM  # chỉ các mã chỉ định
    .venv/Scripts/python.exe backend/tools/backfill_local_store.py --years 3
"""
import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import logging  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(message)s")

from data_fetcher import SECTOR_MAP  # noqa: E402
from data_sources import LOCAL, STORE_DIR, VNSTOCK, fetch_history, get_source_info  # noqa: E402

VNSTOCK.wait_on_limit = True  # công cụ chạy nền: chờ hồi hạn mức/phút thay vì bỏ qua mã

INDICES = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("symbols", nargs="*", help="Mã cần tải (mặc định: tất cả mã trong SECTOR_MAP + chỉ số)")
    ap.add_argument("--years", type=float, default=5)
    ap.add_argument("--pause", type=float, default=0.4, help="Nghỉ giữa các mã (giây) để tránh bị giới hạn")
    ap.add_argument("--skip-existing", action="store_true", help="Bỏ qua mã đã có đủ số năm dữ liệu trong kho")
    args = ap.parse_args()

    symbols = [s.upper() for s in args.symbols] or INDICES + sorted({s for lst in SECTOR_MAP.values() for s in lst})
    end = datetime.now()
    start = end - timedelta(days=int(args.years * 365))
    print(f"Kho cục bộ: {STORE_DIR}\nTải {len(symbols)} mã, {start:%d/%m/%Y} → {end:%d/%m/%Y}\n")

    ok, fail = 0, []
    t0 = time.time()
    for i, sym in enumerate(symbols, 1):
        if args.skip_existing and LOCAL.path(sym).exists():
            try:
                have = LOCAL.history(sym, start, end)
                if not have.empty and have.index[0] <= start + timedelta(days=30) and (end - have.index[-1]).days <= 4:
                    ok += 1
                    print(f"[{i:>3}/{len(symbols)}] {sym:<10} đã có trong kho ({len(have)} phiên) — bỏ qua", flush=True)
                    continue
            except Exception:  # noqa: BLE001
                pass
        df = fetch_history(sym, start, end)  # tự ghi vào kho khi lấy từ nguồn trực tuyến
        info = get_source_info(sym) or {}
        if df.empty or info.get("source") in (None, "local"):
            fail.append(sym)
            status = f"LỖI ({'chỉ có bản cũ trong kho' if info.get('source') == 'local' else '; '.join(info.get('errors', []))[:90]})"
        else:
            ok += 1
            status = f"{info['source']}: {len(df)} phiên, đến {info['last_date']}"
        print(f"[{i:>3}/{len(symbols)}] {sym:<10} {status}", flush=True)
        time.sleep(args.pause)

    print(f"\nHoàn tất sau {time.time() - t0:.0f}s: {ok} mã thành công, {len(fail)} mã lỗi.")
    if fail:
        print("Mã lỗi:", ", ".join(fail))
    print(f"Số file trong kho: {len(list(STORE_DIR.glob('*.csv')))} (ví dụ {LOCAL.path('HPG')})")


if __name__ == "__main__":
    main()
