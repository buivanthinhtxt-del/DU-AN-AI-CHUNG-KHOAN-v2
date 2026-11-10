"""
Dữ liệu thật cho Huyết Vũ Lâu (không cần vnstock):
  1. Chất lượng lợi nhuận theo quý: CFO (LCTT thuần từ HĐKD) so với LNST, phải thu, tồn kho.
  2. Lịch sự kiện quyền (GDKHQ cổ tức tiền/cổ phiếu, thưởng, phát hành, ĐHCĐ) → quy tắc "Né trước chốt – Bắt sau chia".

Nguồn: API công khai VNDirect Finfo (api-finfo.vndirect.com.vn/v4). Mã chỉ tiêu được dò THEO TÊN trong
danh mục financial_models của từng mã, vì doanh nghiệp thường / ngân hàng / chứng khoán dùng mẫu BCTC khác nhau.
Mọi hàm trả về None hoặc dict có "available": False khi nguồn lỗi — tuyệt đối không bịa số.
"""

from __future__ import annotations

import logging
import time
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from cache_manager import get_cache, set_cache

logger = logging.getLogger("financial_quality")

FINFO_BASE = "https://api-finfo.vndirect.com.vn/v4"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}
_TIMEOUT = 15
SOURCE_LABEL = "VNDirect Finfo (BCTC công bố)"

# Chỉ tiêu cần lấy: khóa nội bộ -> (loại báo cáo, các cụm tên chấp nhận theo thứ tự ưu tiên)
ITEM_SPECS = {
    "cfo": ("CASHFLOW", ["luu chuyen tien thuan tu hoat dong kinh doanh"]),
    "npat_parent": ("INCOME", ["loi nhuan sau thue cua cong ty me", "loi nhuan sau thue cua co dong cua ngan hang me",
                               "loi nhuan sau thue cua chu so huu", "loi nhuan sau thue phan bo cho chu so huu"]),
    "npat": ("INCOME", ["loi nhuan sau thue thu nhap doanh nghiep", "loi nhuan sau thue"]),
    "revenue": ("INCOME", ["doanh thu thuan", "thu nhap lai thuan", "cong doanh thu hoat dong"]),
    "receivables": ("BALANCESHEET", ["cac khoan phai thu ngan han"]),
    "inventory": ("BALANCESHEET", ["hang ton kho"]),
    "total_assets": ("BALANCESHEET", ["tong cong tai san", "tong tai san"]),
    "equity": ("BALANCESHEET", ["von chu so huu"]),
}

EVENT_TYPE_LABELS = {
    "DIVIDEND": "Cổ tức tiền mặt",
    "STOCKDIV": "Cổ tức bằng cổ phiếu",
    "KINDDIV": "Cổ phiếu thưởng",
    "RIGHT": "Quyền mua cổ phiếu phát hành thêm",
    "ISSUE": "Phát hành thêm",
    "LISTED": "Niêm yết/giao dịch bổ sung",
    "MEETING": "Họp ĐHCĐ",
    "meetingRight": "Chốt quyền dự ĐHCĐ",
}
# Sự kiện làm giá tham chiếu bị điều chỉnh giảm tại ngày GDKHQ (pha loãng / chia tách)
DILUTIVE_TYPES = {"STOCKDIV", "KINDDIV", "RIGHT", "ISSUE"}


def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    return " ".join("".join(c for c in s if unicodedata.category(c) != "Mn").split())


def _get(path: str, params: Dict[str, Any]) -> list:
    resp = requests.get(f"{FINFO_BASE}/{path}", params=params, headers=_HEADERS, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json().get("data") or []


# ----------------------------------------------------------------------------------------------
# 1. Chất lượng lợi nhuận (CFO vs LNST)
# ----------------------------------------------------------------------------------------------
def _resolve_items(symbol: str) -> Dict[str, Any]:
    """Dò modelType (mẫu BCTC theo quý gốc) và itemCode của từng chỉ tiêu theo tên. Cache 7 ngày."""
    key = f"finfo_models_v1_{symbol}"
    cached = get_cache(key, 7 * 86400)
    if cached:
        return cached
    models = _get("financial_models", {"sort": "displayOrder:asc", "q": f"codeList:{symbol}", "size": 3000})
    by_type: Dict[str, Dict[float, list]] = defaultdict(lambda: defaultdict(list))
    company_form = None
    for m in models:
        name = m.get("modelTypeName")
        if name in ("CASHFLOW", "INCOME", "BALANCESHEET"):
            by_type[name][m["modelType"]].append(m)
            company_form = company_form or m.get("companyForm")
    resolved: Dict[str, Any] = {"company_form": company_form, "items": {}}
    for key_name, (stmt, phrases) in ITEM_SPECS.items():
        if not by_type.get(stmt):
            continue
        model_type = min(by_type[stmt])  # mẫu gốc (số nhỏ nhất: 1/2/3, 101/102/103, 89/90/91)
        rows = by_type[stmt][model_type]
        for phrase in phrases:
            hit = next((r for r in rows if _strip_accents(r.get("itemVnName", "")) == phrase), None) or next(
                (r for r in rows if _strip_accents(r.get("itemVnName", "")).startswith(phrase)), None)
            if hit:
                resolved["items"][key_name] = {"model_type": int(model_type), "item_code": int(hit["itemCode"])}
                break
    set_cache(key, resolved)
    return resolved


def _fetch_quarters(symbol: str, resolved: Dict[str, Any], quarters: int) -> Dict[str, Dict[str, float]]:
    per_model: Dict[int, List[int]] = defaultdict(list)
    for spec in resolved["items"].values():
        per_model[spec["model_type"]].append(spec["item_code"])
    code_to_key = {(s["model_type"], s["item_code"]): k for k, s in resolved["items"].items()}
    data: Dict[str, Dict[str, float]] = defaultdict(dict)
    for model_type, codes in per_model.items():
        rows = _get("financial_statements", {
            "q": f"code:{symbol}~reportType:QUARTER~modelType:{model_type}~itemCode:{','.join(map(str, sorted(set(codes))))}",
            "sort": "fiscalDate:desc", "size": quarters * len(codes) + 20,
        })
        for r in rows:
            k = code_to_key.get((model_type, int(r["itemCode"])))
            if k and r.get("numericValue") is not None:
                data[r["fiscalDate"]][k] = float(r["numericValue"])
    return data


def _q_label(fiscal_date: str) -> str:
    d = datetime.strptime(fiscal_date[:10], "%Y-%m-%d")
    return f"Q{(d.month - 1) // 3 + 1}/{d.year}"


def _ratio(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 2)


def _growth(cur: Optional[float], prev: Optional[float]) -> Optional[float]:
    if cur is None or prev is None or prev <= 0:
        return None
    return round((cur / prev - 1) * 100, 1)


def analyze_cashflow_quality(quarters_desc: List[Dict[str, Any]], company_form: Optional[str] = None) -> Dict[str, Any]:
    """Tính chỉ số chất lượng lợi nhuận từ danh sách quý (mới nhất trước). Hàm thuần, dễ kiểm thử."""
    q = quarters_desc
    ni_key = lambda r: r.get("npat_parent") if r.get("npat_parent") is not None else r.get("npat")  # noqa: E731
    last4 = q[:4]
    cfo_ttm = sum(r["cfo"] for r in last4 if r.get("cfo") is not None) if len(last4) == 4 and all(r.get("cfo") is not None for r in last4) else None
    ni_ttm = sum(ni_key(r) for r in last4) if len(last4) == 4 and all(ni_key(r) is not None for r in last4) else None
    cfo_ni_ttm = _ratio(cfo_ttm, ni_ttm) if (ni_ttm or 0) > 0 else None

    yoy = q[4] if len(q) > 4 else None
    rev_g = _growth(q[0].get("revenue"), yoy.get("revenue")) if yoy else None
    rec_g = _growth(q[0].get("receivables"), yoy.get("receivables")) if yoy else None
    inv_g = _growth(q[0].get("inventory"), yoy.get("inventory")) if yoy else None
    negative_cfo_quarters = sum(1 for r in last4 if (r.get("cfo") or 0) < 0)

    is_financial = (company_form or "").upper() in ("BANK", "SECURITIES", "INSURANCE")
    flags: List[str] = []
    if is_financial:
        flags.append("Doanh nghiệp tài chính: CFO biến động theo tiền gửi/cho vay, tỷ lệ CFO/LNST ít ý nghĩa — ưu tiên chất lượng tài sản.")
    else:
        if cfo_ni_ttm is not None and cfo_ni_ttm < 0.5:
            flags.append(f"CFO 4 quý chỉ bằng {cfo_ni_ttm:.2f}x LNST — nguy cơ 'lãi trên giấy'.")
        if ni_ttm is not None and ni_ttm > 0 and cfo_ttm is not None and cfo_ttm < 0:
            flags.append("LNST 4 quý dương nhưng CFO 4 quý âm — lợi nhuận chưa chuyển thành tiền.")
        if negative_cfo_quarters >= 2:
            flags.append(f"{negative_cfo_quarters}/4 quý gần nhất có CFO âm.")
        if rec_g is not None and rev_g is not None and rec_g - rev_g > 20:
            flags.append(f"Phải thu ngắn hạn tăng {rec_g:+.1f}% so với cùng kỳ, nhanh hơn doanh thu ({rev_g:+.1f}%).")
        if inv_g is not None and rev_g is not None and inv_g - rev_g > 25:
            flags.append(f"Tồn kho tăng {inv_g:+.1f}% so với cùng kỳ, nhanh hơn doanh thu ({rev_g:+.1f}%).")

    if is_financial or cfo_ni_ttm is None:
        verdict = "KHONG_DU_DU_LIEU" if not is_financial else "KHONG_AP_DUNG"
    elif cfo_ni_ttm >= 0.85 and not flags:
        verdict = "TOT"
    elif cfo_ni_ttm >= 0.5:
        verdict = "TRUNG_BINH"
    else:
        verdict = "YEU"

    return {
        "cfo_ttm_bn": round(cfo_ttm / 1e9, 1) if cfo_ttm is not None else None,
        "npat_ttm_bn": round(ni_ttm / 1e9, 1) if ni_ttm is not None else None,
        "cfo_to_npat_ttm": cfo_ni_ttm,
        "negative_cfo_quarters_4q": negative_cfo_quarters,
        "revenue_yoy_pct": rev_g,
        "receivables_yoy_pct": rec_g,
        "inventory_yoy_pct": inv_g,
        "is_financial_company": is_financial,
        "verdict": verdict,
        "flags": flags,
    }


def get_cashflow_quality(symbol: str, quarters: int = 8) -> Dict[str, Any]:
    """BCTC quý thật + chỉ số chất lượng lợi nhuận. Cache 12 giờ (lỗi: cache âm 1 giờ)."""
    sym = (symbol or "").upper().strip()
    key = f"cashflow_quality_v1_{sym}"
    cached = get_cache(key, 12 * 3600)
    if cached and (cached.get("available") or time.time() - cached.get("ts", 0) < 3600):
        return cached
    try:
        resolved = _resolve_items(sym)
        if not resolved.get("items"):
            raise ValueError("không tìm thấy mẫu BCTC cho mã này")
        raw = _fetch_quarters(sym, resolved, quarters)
        if not raw:
            raise ValueError("nguồn không trả dữ liệu quý")
        rows = []
        for fd in sorted(raw, reverse=True)[:quarters]:
            r = {"period": _q_label(fd), "fiscal_date": fd, **raw[fd]}
            rows.append(r)
        metrics = analyze_cashflow_quality(rows, resolved.get("company_form"))
        result = {
            "available": True,
            "symbol": sym,
            "source": SOURCE_LABEL,
            "company_form": resolved.get("company_form"),
            "latest_period": rows[0]["period"],
            "quarters": [
                {"period": r["period"], **{k: (round(v / 1e9, 1) if isinstance(v, float) else v)
                                           for k, v in r.items() if k not in ("period", "fiscal_date")}}
                for r in rows
            ],
            "unit": "tỷ đồng",
            **metrics,
            "ts": time.time(),
        }
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[financial_quality] Không lấy được BCTC quý {sym}: {e}")
        result = {"available": False, "symbol": sym, "source": SOURCE_LABEL, "error": str(e)[:200], "ts": time.time()}
    set_cache(key, result)
    return result


# ----------------------------------------------------------------------------------------------
# 2. Lịch sự kiện quyền (GDKHQ)
# ----------------------------------------------------------------------------------------------
def _parse_d(s: Optional[str]) -> Optional[date]:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date() if s else None
    except ValueError:
        return None


def evaluate_rights_events(events: List[Dict[str, Any]], today: Optional[date] = None,
                           window_days: int = 30) -> Dict[str, Any]:
    """Áp quy tắc 'Né trước chốt – Bắt sau chia' lên danh sách sự kiện đã chuẩn hóa. Hàm thuần."""
    today = today or date.today()
    upcoming = [e for e in events if e["ex_date"] and today <= _parse_d(e["ex_date"]) <= today + timedelta(days=window_days)]
    recent = [e for e in events if e["ex_date"] and today - timedelta(days=window_days) <= _parse_d(e["ex_date"]) < today]
    upcoming.sort(key=lambda e: e["ex_date"])
    recent.sort(key=lambda e: e["ex_date"], reverse=True)

    up_dilutive = [e for e in upcoming if e["type"] in DILUTIVE_TYPES]
    up_cash = [e for e in upcoming if e["type"] == "DIVIDEND"]
    rec_dilutive = [e for e in recent if e["type"] in DILUTIVE_TYPES]

    if up_dilutive:
        e = up_dilutive[0]
        stance = "NE_TRUOC_CHOT"
        advice = (f"Né trước chốt: {e['label']} GDKHQ ngày {e['ex_date']} ({e['days_to_ex']} ngày nữa)"
                  f"{' — ' + e['note'] if e.get('note') else ''}. Giá tham chiếu sẽ bị điều chỉnh giảm, tránh mua đuổi trước ngày chốt.")
    elif rec_dilutive:
        e = rec_dilutive[0]
        stance = "BAT_SAU_CHIA"
        advice = (f"Bắt sau chia: {e['label']} đã GDKHQ ngày {e['ex_date']}. Theo dõi nhịp chỉnh sau chia "
                  f"và áp lực hàng về tài khoản trước khi giải ngân.")
    elif up_cash:
        e = up_cash[0]
        stance = "CO_TUC_TIEN"
        advice = (f"Cổ tức tiền mặt GDKHQ ngày {e['ex_date']} ({e['days_to_ex']} ngày nữa)"
                  f"{' — ' + e['note'] if e.get('note') else ''}. Giá tham chiếu giảm tương ứng mức cổ tức.")
    else:
        stance = "KHONG_CO_SU_KIEN"
        advice = f"Không có sự kiện quyền nào có ngày GDKHQ trong ±{window_days} ngày theo dữ liệu công bố."

    return {"stance": stance, "advice": advice, "upcoming": upcoming, "recent": recent, "window_days": window_days}


def get_corporate_events(symbol: str, window_days: int = 30, today: Optional[date] = None) -> Dict[str, Any]:
    """Lịch sự kiện quyền thật từ VNDirect + đánh giá Né trước chốt – Bắt sau chia. Cache 3 giờ."""
    sym = (symbol or "").upper().strip()
    today = today or date.today()
    key = f"corporate_events_v1_{sym}_{today.isoformat()}"
    cached = get_cache(key, 3 * 3600)
    if cached:
        return cached
    try:
        raw = _get("events", {"q": f"code:{sym}~locale:VN", "sort": "effectiveDate:desc", "size": 60})
        events = []
        for r in raw:
            if r.get("group") != "investorRight":
                continue
            ex = _parse_d(r.get("effectiveDate"))
            events.append({
                "type": r.get("type"),
                "label": EVENT_TYPE_LABELS.get(r.get("type"), r.get("typeDesc") or r.get("type")),
                "note": r.get("note"),
                "ex_date": ex.isoformat() if ex else None,
                "record_or_end_date": r.get("expiredDate"),
                "payment_date": r.get("actualDate"),
                "disclosure_date": r.get("disclosureDate"),
                "cash_per_share": r.get("dividend"),
                "ratio_pct": r.get("ratio"),
                "days_to_ex": (ex - today).days if ex else None,
            })
        result = {"available": True, "symbol": sym, "source": "VNDirect Finfo (lịch sự kiện công bố)",
                  "as_of": today.isoformat(), **evaluate_rights_events(events, today, window_days),
                  "history": events[:15]}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[financial_quality] Không lấy được lịch sự kiện {sym}: {e}")
        result = {"available": False, "symbol": sym, "error": str(e)[:200],
                  "stance": "KHONG_RO", "advice": "Không tải được lịch sự kiện quyền — cần tự kiểm tra GDKHQ trước khi giao dịch."}
    set_cache(key, result)
    return result
