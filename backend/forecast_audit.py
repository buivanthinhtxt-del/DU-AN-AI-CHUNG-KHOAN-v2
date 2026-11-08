"""
Hệ thống Tự đúc rút / Đối chiếu Dự báo Cũ (Forecast Audit Engine)
Lưu trữ và đối chiếu dự báo lịch sử tại backend/cache/forecast_audit/{symbol}.json.
Chấm điểm 4 chiều: Hướng (Direction), Biên độ (Amplitude), Thời điểm (Timing), Điều kiện (Condition).
"""
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

AUDIT_CACHE_DIR = Path(__file__).resolve().parent / "cache" / "forecast_audit"


def get_audit_cache_path(symbol: str) -> Path:
    """Trả về đường dẫn tệp JSON lưu lịch sử dự báo của mã cổ phiếu."""
    sym = (symbol or "").upper().strip()
    AUDIT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIT_CACHE_DIR / f"{sym}.json"


def load_forecast_records(symbol: str) -> List[Dict[str, Any]]:
    """Đọc toàn bộ bản ghi dự báo lịch sử từ cache."""
    path = get_audit_cache_path(symbol)
    if not path.exists():
        return []
    for _ in range(3):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("records", []) if isinstance(data, dict) else []
        except (PermissionError, OSError):
            time.sleep(0.01)
        except Exception as e:
            logger.warning(f"[!] Không thể đọc cache forecast_audit cho {symbol}: {e}")
            return []
    return []


def audit_historical_forecast(
    symbol: str,
    current_price: float,
    current_date: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Đối chiếu các bản ghi dự báo trước đó của symbol so với giá thực tế hiện tại.
    Chấm điểm 4 chiều:
      1. Hướng (Direction): Đúng / Sai hướng kỳ vọng.
      2. Biên độ (Amplitude): Mức độ tiệm cận vùng mục tiêu hoặc dải giá dự báo (0.0 - 1.0).
      3. Thời điểm (Timing): Đạt trong khung thời gian T+ (T+2.5, T+5, T+10).
      4. Điều kiện (Condition): Điều kiện luận điểm có được bảo toàn hay vi phạm cắt lỗ.
    """
    records = load_forecast_records(symbol)
    if not records:
        return {
            "has_history": False,
            "audit_count": 0,
            "last_audit": None,
            "summary_for_prompt": "- Chưa có dữ liệu đối chiếu dự báo cũ cho mã này (lần đầu tạo hồ sơ hoặc chưa có bản ghi trước).",
            "lessons_learned": "Chưa có dữ liệu dự báo lịch sử để đối chiếu.",
        }

    last_rec = records[-1]
    as_of_price = float(last_rec.get("as_of_price") or current_price)
    target_1 = float(last_rec.get("target_1") or as_of_price * 1.05)
    stop_loss = float(last_rec.get("stop_loss") or as_of_price * 0.93)
    pred_dir = str(last_rec.get("predicted_direction") or "UP").upper()
    forecast_date = str(last_rec.get("date") or last_rec.get("created_at", "")[:10] or "N/A")

    # 1. Hướng (Direction)
    price_change_pct = ((current_price / as_of_price) - 1.0) * 100 if as_of_price > 0 else 0.0
    actual_dir = "UP" if price_change_pct > 0.5 else ("DOWN" if price_change_pct < -0.5 else "SIDEWAYS")

    is_dir_up = pred_dir in ("UP", "TĂNG", "MUA", "TÍCH CỰC")
    is_dir_down = pred_dir in ("DOWN", "GIẢM", "BÁN", "TIÊU CỰC")

    if is_dir_up:
        direction_score = 1.0 if price_change_pct >= 0 else 0.0
        dir_correct = price_change_pct >= 0
    elif is_dir_down:
        direction_score = 1.0 if price_change_pct <= 0 else 0.0
        dir_correct = price_change_pct <= 0
    else:  # SIDEWAYS
        direction_score = 1.0 if abs(price_change_pct) <= 2.5 else 0.5
        dir_correct = abs(price_change_pct) <= 2.5

    # 2. Biên độ (Amplitude)
    if is_dir_up and target_1 > as_of_price:
        expected_gain = target_1 - as_of_price
        actual_gain = current_price - as_of_price
        if actual_gain >= expected_gain:
            amplitude_score = 1.0
        elif actual_gain > 0:
            amplitude_score = round(max(0.0, min(1.0, actual_gain / expected_gain)), 2)
        else:
            amplitude_score = max(0.0, round(1.0 - abs(current_price - target_1) / target_1, 2)) if target_1 > 0 else 0.0
    elif is_dir_down and target_1 < as_of_price:
        expected_drop = as_of_price - target_1
        actual_drop = as_of_price - current_price
        if actual_drop >= expected_drop:
            amplitude_score = 1.0
        elif actual_drop > 0:
            amplitude_score = round(max(0.0, min(1.0, actual_drop / expected_drop)), 2)
        else:
            amplitude_score = max(0.0, round(1.0 - abs(current_price - target_1) / target_1, 2)) if target_1 > 0 else 0.0
    else:
        # Khoảng cách tương đối tới mục tiêu
        diff_pct = abs(current_price - target_1) / target_1 if target_1 > 0 else 0
        amplitude_score = max(0.0, round(1.0 - diff_pct, 2))

    # 3. Thời điểm (Timing)
    # Xác định số ngày đã trôi qua
    elapsed_days = 5
    if current_date and forecast_date != "N/A":
        try:
            d_curr = datetime.strptime(current_date[:10], "%Y-%m-%d" if "-" in current_date else "%d/%m/%Y")
            d_prev = datetime.strptime(forecast_date[:10], "%Y-%m-%d" if "-" in forecast_date else "%d/%m/%Y")
            elapsed_days = max(1, (d_curr - d_prev).days)
        except Exception:
            elapsed_days = 5

    # Nếu dự báo T+5 và thời gian diễn ra trong khoảng 1-10 ngày thì điểm timing tốt
    if elapsed_days <= 7:
        time_score = 1.0
    elif elapsed_days <= 14:
        time_score = 0.8
    elif elapsed_days <= 30:
        time_score = 0.6
    else:
        time_score = 0.4

    # 4. Điều kiện (Condition)
    # Nếu giá hiện tại giữ vững trên ngưỡng cắt lỗ (hoặc dưới nếu short/down) thì luận điểm bảo toàn
    if is_dir_up:
        condition_held = current_price >= stop_loss
    else:
        condition_held = current_price <= (as_of_price * 1.07)
    condition_score = 1.0 if condition_held else 0.0

    # Tổng điểm độ chính xác tổng thể (Overall Accuracy %)
    overall_accuracy_pct = round(
        (direction_score * 0.35 + amplitude_score * 0.25 + time_score * 0.20 + condition_score * 0.20) * 100.0,
        1,
    )

    if overall_accuracy_pct >= 75.0:
        verdict = "CHÍNH XÁC"
    elif overall_accuracy_pct >= 50.0:
        verdict = "ĐẠT MỘT PHẦN"
    else:
        verdict = "SAI LỆCH"

    # Đúc rút kinh nghiệm định lượng (Lessons learned)
    if dir_correct and amplitude_score >= 0.8:
        lessons = (
            f"Dự báo ngày {forecast_date} chuẩn xác cả về hướng và biên độ tăng ({price_change_pct:+.1f}%). "
            f"Giá đã tiệm cận sát vùng mục tiêu {target_1:.2f}. Cần nâng trailing stop bảo toàn lợi nhuận."
        )
    elif dir_correct and amplitude_score < 0.8:
        lessons = (
            f"Dự báo ngày {forecast_date} đúng hướng ({actual_dir}) nhưng biên độ thực tế ({price_change_pct:+.1f}%) "
            f"chưa đạt trọn vẹn mục tiêu {target_1:.2f} do áp lực chốt lời/rung lắc T+2,5."
        )
    elif not dir_correct and condition_held:
        lessons = (
            f"Dự báo ngày {forecast_date} chưa đúng nhịp bứt phá (biến động {price_change_pct:+.1f}%), "
            f"tuy nhiên giá vẫn nằm trên chốt chặn Stop-Loss {stop_loss:.2f}. Luận điểm chưa bị vi phạm hoàn toàn."
        )
    else:
        lessons = (
            f"Dự báo ngày {forecast_date} sai lệch: Cổ phiếu suy yếu {price_change_pct:+.1f}% và vi phạm ngưỡng cắt lỗ "
            f"{stop_loss:.2f}. Bài học: Cần tuân thủ kỷ luật Price-Stop dứt khoát và rà soát lại biến động dòng tiền Tạo lập."
        )

    last_audit_data = {
        "forecast_date": forecast_date,
        "as_of_price": round(as_of_price, 2),
        "predicted_direction": pred_dir,
        "actual_direction": actual_dir,
        "price_change_pct": round(price_change_pct, 2),
        "direction_score": direction_score,
        "predicted_target": round(target_1, 2),
        "actual_price": round(current_price, 2),
        "amplitude_score": amplitude_score,
        "time_score": time_score,
        "condition_score": condition_score,
        "overall_accuracy_pct": overall_accuracy_pct,
        "verdict": verdict,
        "lessons_learned": lessons,
    }

    summary_prompt = (
        f"- Lần dự báo trước: Ngày {forecast_date} tại giá {as_of_price:.2f} (Kỳ vọng: {pred_dir}, Mục tiêu: {target_1:.2f}, Cắt lỗ: {stop_loss:.2f})\n"
        f"- Kết quả đối chiếu với giá hiện tại {current_price:.2f} ({price_change_pct:+.1f}%): Đánh giá [{verdict}] (Độ chính xác {overall_accuracy_pct}%)\n"
        f"  • Hướng: {'Đúng' if dir_correct else 'Sai'} (điểm: {direction_score:.1f}) | Biên độ: {amplitude_score:.2f} | Thời điểm: {time_score:.2f} | Điều kiện: {condition_score:.1f}\n"
        f"- Bài học rút ra: {lessons}"
    )

    return {
        "has_history": True,
        "audit_count": len(records),
        "last_audit": last_audit_data,
        "summary_for_prompt": summary_prompt,
        "lessons_learned": lessons,
    }


def save_forecast_audit(
    symbol: str,
    forecast_record: Dict[str, Any],
    current_price: Optional[float] = None,
    current_date: Optional[str] = None,
) -> bool:
    """
    Lưu bản ghi dự báo mới vào file cache backend/cache/forecast_audit/{symbol}.json.
    Chấp nhận cả dict ai_report chuẩn lẫn dict tùy biến.
    """
    sym = (symbol or "").upper().strip()
    if not sym:
        return False

    path = get_audit_cache_path(sym)
    records = load_forecast_records(sym)

    now_dt = datetime.now()
    date_str = current_date or now_dt.strftime("%Y-%m-%d")

    # Trích xuất thông tin kế hoạch từ ai_report hoặc record
    trade_plan = forecast_record.get("trade_plan") or {}
    summary = forecast_record.get("summary") or {}
    predictions = forecast_record.get("predictions") or []
    quant_snapshot = forecast_record.get("quant_snapshot") or {}

    as_of = (
        current_price
        or quant_snapshot.get("close")
        or trade_plan.get("entry_low")
        or forecast_record.get("as_of_price")
        or 0.0
    )
    as_of = float(as_of)

    target_1 = float(trade_plan.get("target_1") or forecast_record.get("target_1") or (as_of * 1.06))
    target_2 = float(trade_plan.get("target_2") or forecast_record.get("target_2") or (as_of * 1.12))
    stop_loss = float(trade_plan.get("stop_loss") or forecast_record.get("stop_loss") or (as_of * 0.93))

    action = str(summary.get("action") or forecast_record.get("action") or "Theo dõi")
    stance = str(summary.get("stance") or forecast_record.get("stance") or "Trung lập")

    if action in ("Mua", "Tích lũy", "Gia tăng") or stance in ("Tích cực", "Rất tích cực"):
        pred_dir = "UP"
    elif action in ("Bán", "Hạ tỷ trọng", "Cắt lỗ") or stance in ("Tiêu cực", "Rủi ro"):
        pred_dir = "DOWN"
    else:
        pred_dir = "SIDEWAYS"

    record_entry = {
        "forecast_id": f"{sym}_{now_dt.strftime('%Y%m%d_%H%M%S')}",
        "created_at": now_dt.isoformat(),
        "date": date_str,
        "as_of_price": round(as_of, 2),
        "stance": stance,
        "action": action,
        "predicted_direction": pred_dir,
        "entry_zone": [
            round(float(trade_plan.get("entry_low") or as_of * 0.99), 2),
            round(float(trade_plan.get("entry_high") or as_of * 1.01), 2),
        ],
        "target_1": round(target_1, 2),
        "target_2": round(target_2, 2),
        "stop_loss": round(stop_loss, 2),
        "time_horizon": "T+5 (1 tuần)",
        "trigger_condition": trade_plan.get("entry_trigger") or forecast_record.get("trigger_condition") or "Theo dõi bứt phá kháng cự",
        "predictions": predictions if isinstance(predictions, list) else [],
        "engine": str(forecast_record.get("engine") or "gemini"),
    }

    records.append(record_entry)
    # Giữ tối đa 20 bản ghi gần nhất để tránh phình to tệp
    if len(records) > 20:
        records = records[-20:]

    temp_file = path.with_name(f"{path.stem}_{uuid.uuid4().hex[:8]}.tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump({"symbol": sym, "updated_at": now_dt.isoformat(), "records": records}, f, ensure_ascii=False, indent=2)
        
        last_err = None
        for _ in range(5):
            try:
                temp_file.replace(path)
                return True
            except (PermissionError, OSError) as pe:
                last_err = pe
                time.sleep(0.02)
        if last_err:
            raise last_err
        return False
    except Exception as e:
        logger.error(f"[!] Lỗi khi lưu forecast_audit cho {sym}: {e}", exc_info=True)
        return False
    finally:
        try:
            temp_file.unlink(missing_ok=True)
        except Exception:
            pass


# Aliases tương thích đa giao diện
evaluate_forecast_audit = audit_historical_forecast
record_new_forecast = save_forecast_audit
