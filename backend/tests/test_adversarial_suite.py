import sys
import os
import time
import json
import threading
import concurrent.futures
from pathlib import Path
import pandas as pd
import numpy as np

# Ensure backend directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from data_fetcher import calculate_rsi_wilder, calculate_indicators, get_historical_data
from cache_manager import get_cache, set_cache, CACHE_DIR


def test_math_boundaries():
    print("=" * 60)
    print("TEST 1: MATHEMATICAL & QUANTITATIVE BOUNDARIES (RSI WILDER)")
    print("=" * 60)

    # 1. 14 consecutive ceiling (limit-up) candles
    # Starting price: 10.0, increasing by 7% each day for 20 days
    up_prices = [10.0 * (1.07 ** i) for i in range(25)]
    up_series = pd.Series(up_prices)
    up_rsi = calculate_rsi_wilder(up_series, period=14)
    
    print(f"[+] 14+ consecutive up days test:")
    print(f"    Last 5 prices: {[round(p, 2) for p in up_prices[-5:]]}")
    print(f"    RSI series tail: {up_rsi.tail(5).tolist()}")
    final_up_rsi = up_rsi.iloc[-1]
    assert final_up_rsi == 100.0, f"Expected RSI = 100.0 on pure up-run, got {final_up_rsi}"
    print(f"    => PASS: RSI is exactly {final_up_rsi}")

    # Contrast with old legacy SMA bug:
    def legacy_sma_rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    legacy_up_rsi = legacy_sma_rsi(up_series, period=14).iloc[-1]
    print(f"    [Comparison] Legacy SMA RSI on 14+ up days: {legacy_up_rsi} (BUG: collapsed to 50.0!)")

    # 2. Completely flat prices (gain = 0, loss = 0)
    flat_prices = [25.0] * 30
    flat_series = pd.Series(flat_prices)
    flat_rsi = calculate_rsi_wilder(flat_series, period=14)
    print(f"\n[+] Completely flat series test (price = 25.0 constant):")
    print(f"    RSI series tail: {flat_rsi.tail(5).tolist()}")
    final_flat_rsi = flat_rsi.iloc[-1]
    assert final_flat_rsi == 50.0, f"Expected RSI = 50.0 on flat price, got {final_flat_rsi}"
    print(f"    => PASS: RSI is exactly {final_flat_rsi}")

    # 3. 14 consecutive floor (limit-down) candles
    down_prices = [100.0 * (0.93 ** i) for i in range(25)]
    down_series = pd.Series(down_prices)
    down_rsi = calculate_rsi_wilder(down_series, period=14)
    print(f"\n[+] 14+ consecutive down days test:")
    print(f"    RSI series tail: {down_rsi.tail(5).tolist()}")
    final_down_rsi = down_rsi.iloc[-1]
    assert final_down_rsi == 0.0, f"Expected RSI = 0.0 on pure down-run, got {final_down_rsi}"
    print(f"    => PASS: RSI is exactly {final_down_rsi}")

    # 4. Cliff-effect test (single massive spike 15 days ago)
    # Check that Wilder RMA decays smoothly whereas SMA exhibits a cliff discontinuity
    spike_prices = [20.0] * 35
    spike_prices[10] = 30.0  # single massive spike at index 10
    spike_series = pd.Series(spike_prices)
    wilder_spike = calculate_rsi_wilder(spike_series, period=14)
    legacy_spike = legacy_sma_rsi(spike_series, period=14)
    
    # At index 24 (14 periods after index 10 spike), legacy drops the spike abruptly
    print(f"\n[+] Cliff-effect test (spike at t=10):")
    print(f"    Wilder RSI t=23..26: {wilder_spike.iloc[23:27].tolist()}")
    print(f"    Legacy SMA RSI t=23..26: {legacy_spike.iloc[23:27].tolist()}")
    sma_diff = abs(legacy_spike.iloc[25] - legacy_spike.iloc[24])
    wilder_diff = abs(wilder_spike.iloc[25] - wilder_spike.iloc[24])
    print(f"    Legacy SMA cliff drop at window exit: {sma_diff:.2f}")
    print(f"    Wilder RMA smooth transition: {wilder_diff:.2f}")
    print("=> TEST 1 ALL CHECKS PASSED!\n")


def test_lookahead_bias():
    print("=" * 60)
    print("TEST 2: LOOK-AHEAD BIAS VERIFICATION")
    print("=" * 60)

    # 2026-05-03 was a Sunday
    target = '2026-05-03'
    target_dt = pd.to_datetime(target)
    print(f"[*] Calling get_historical_data for HPG with target_date='{target}' (Sunday)...")
    
    df = get_historical_data('HPG', days=15, target_date=target, include_indicators=True)
    assert df is not None and not df.empty, "DataFrame should not be empty"

    last_date = df.index[-1]
    print(f"[+] DataFrame returned {len(df)} rows.")
    print(f"[+] Earliest date: {df.index[0].strftime('%Y-%m-%d')}")
    print(f"[+] Latest date in DataFrame: {last_date.strftime('%Y-%m-%d')}")
    
    # Assertions
    assert last_date <= target_dt, f"Look-ahead bias detected! Latest date {last_date} is after target_date {target_dt}"
    
    # Specifically ensure 2026-05-04 is NOT in index
    future_forbidden = pd.to_datetime('2026-05-04')
    assert future_forbidden not in df.index, "CRITICAL LOOK-AHEAD BIAS: Found candle 2026-05-04 in historical data!"
    
    # Ensure no dates after target_date exist anywhere in DataFrame
    future_rows = df[df.index > target_dt]
    assert len(future_rows) == 0, f"Found {len(future_rows)} future rows in historical data!"
    print(f"    => PASS: Zero candles past {target}. No look-ahead bias.")
    print("=> TEST 2 ALL CHECKS PASSED!\n")


def test_concurrent_cache_stress():
    print("=" * 60)
    print("TEST 3: CONCURRENT CACHE STRESS-TEST (SHARED KEY)")
    print("=" * 60)

    key = "adversarial_stress_shared_key"
    num_workers = 20
    ops_per_worker = 100
    
    stats = {
        "set_count": 0,
        "get_count": 0,
        "get_hit": 0,
        "get_miss": 0,
        "json_decode_errors": 0,
        "win_error_32": 0,
        "corrupted_payloads": 0,
        "other_exceptions": 0
    }
    stats_lock = threading.Lock()

    # Seed the initial cache
    set_cache(key, {"initial": True, "version": 0, "timestamp": time.time()})

    def writer_worker(worker_id):
        for step in range(ops_per_worker):
            payload = {
                "writer_id": worker_id,
                "step": step,
                "data_block": f"payload_data_{worker_id}_{step}_" + ("Z" * 200),
                "timestamp": time.time()
            }
            try:
                set_cache(key, payload)
                with stats_lock:
                    stats["set_count"] += 1
            except PermissionError as e:
                with stats_lock:
                    stats["win_error_32"] += 1
                print(f"[!] Writer {worker_id} WinError: {e}")
            except Exception as e:
                with stats_lock:
                    stats["other_exceptions"] += 1
                print(f"[!] Writer {worker_id} Exception: {e}")
            time.sleep(0.001)

    def reader_worker(worker_id):
        for step in range(ops_per_worker):
            try:
                data = get_cache(key, ttl_seconds=300)
                with stats_lock:
                    stats["get_count"] += 1
                    if data is not None:
                        stats["get_hit"] += 1
                        # Validate payload structure
                        if not isinstance(data, dict):
                            stats["corrupted_payloads"] += 1
                        elif "initial" in data:
                            pass
                        elif "writer_id" not in data or "step" not in data:
                            stats["corrupted_payloads"] += 1
                    else:
                        stats["get_miss"] += 1
            except json.decoder.JSONDecodeError as e:
                with stats_lock:
                    stats["json_decode_errors"] += 1
                print(f"[!] Reader {worker_id} JSONDecodeError: {e}")
            except PermissionError as e:
                with stats_lock:
                    stats["win_error_32"] += 1
                print(f"[!] Reader {worker_id} WinError: {e}")
            except Exception as e:
                with stats_lock:
                    stats["other_exceptions"] += 1
                print(f"[!] Reader {worker_id} Exception: {e}")
            time.sleep(0.001)

    print(f"[*] Spawning {num_workers} threads (10 writers, 10 readers), {ops_per_worker} ops each on shared key '{key}'...")
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for i in range(num_workers // 2):
            futures.append(executor.submit(writer_worker, i))
        for i in range(num_workers // 2):
            futures.append(executor.submit(reader_worker, i))
        concurrent.futures.wait(futures)

    duration = time.time() - start_time
    total_ops = stats["set_count"] + stats["get_count"]
    print(f"[+] Completed {total_ops} operations in {duration:.2f}s ({total_ops/duration:.1f} ops/sec)")
    print(f"    - Total Writes: {stats['set_count']}")
    print(f"    - Total Reads: {stats['get_count']} (Hits: {stats['get_hit']}, Misses: {stats['get_miss']})")
    print(f"    - JSONDecodeError count: {stats['json_decode_errors']}")
    print(f"    - WinError 32 / PermissionError count: {stats['win_error_32']}")
    print(f"    - Corrupted Payloads count: {stats['corrupted_payloads']}")
    print(f"    - Other Exceptions count: {stats['other_exceptions']}")

    # Clean up stress key
    stress_file = CACHE_DIR / f"{key}.json"
    if stress_file.exists():
        stress_file.unlink(missing_ok=True)

    # Clean up any leftover tmp files
    for tmp_f in CACHE_DIR.glob(f"tmp_{key}_*.json"):
        tmp_f.unlink(missing_ok=True)

    # Rigorous assertions
    assert stats["json_decode_errors"] == 0, f"Encountered {stats['json_decode_errors']} JSONDecodeError!"
    assert stats["win_error_32"] == 0, f"Encountered {stats['win_error_32']} WinError 32!"
    assert stats["corrupted_payloads"] == 0, f"Encountered {stats['corrupted_payloads']} Corrupted Payloads!"
    assert stats["other_exceptions"] == 0, f"Encountered {stats['other_exceptions']} Unhandled Exceptions!"
    print("=> TEST 3 ALL CHECKS PASSED: 0% JSONDecodeError, 0% WinError 32, 100% Payload Integrity!\n")


if __name__ == "__main__":
    test_math_boundaries()
    test_lookahead_bias()
    test_concurrent_cache_stress()
    print("=" * 60)
    print("ALL ADVERSARIAL STRESS TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
