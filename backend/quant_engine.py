"""
Bộ máy định lượng (Quant Engine) — tính toán XÁC ĐỊNH toàn bộ dữ kiện kỹ thuật, dòng tiền và thống kê
từ dữ liệu giá thật, để AI chỉ phải LẬP LUẬN trên số liệu có sẵn thay vì tự "đoán" hoặc bịa số.

Đầu ra chính:
- build_quant_profile(): hồ sơ định lượng đầy đủ của một mã (xu hướng, sức mạnh tương đối, dòng tiền,
  vùng giá có cơ sở, xác suất lịch sử, dải giá thống kê, kế hoạch giao dịch cơ sở).
- market_regime(): "thời tiết" thị trường từ VN-Index / VN30.
- format_quant_dossier() / format_market_dossier(): chuyển thành văn bản đưa vào prompt.
"""
from __future__ import annotations

import calendar
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

from data_fetcher import calculate_indicators
from forecast_audit import (
    audit_historical_forecast,
    save_forecast_audit,
    evaluate_forecast_audit,
    record_new_forecast,
    get_audit_cache_path,
    load_forecast_records,
)

VN_TZ = timezone(timedelta(hours=7))

# Hồ sơ rủi ro mặc định: (rủi ro tối đa mỗi lệnh % NAV, tỷ trọng tối đa 1 mã %)
RISK_PROFILES = {
    "Thấp": (0.5, 10.0),
    "Trung bình": (1.0, 20.0),
    "Cao": (1.5, 25.0),
}


# ----------------------------------------------------------------------------------------------
# Tiện ích số học
# ----------------------------------------------------------------------------------------------
def _num(x, nd: int = 2) -> Optional[float]:
    try:
        if x is None:
            return None
        x = float(x)
        if math.isnan(x) or math.isinf(x):
            return None
        return round(x, nd)
    except (TypeError, ValueError):
        return None


def _ret(close: pd.Series, n: int) -> Optional[float]:
    """Lợi suất % trong n phiên gần nhất."""
    if close is None or len(close) <= n:
        return None
    base = float(close.iloc[-1 - n])
    if not base:
        return None
    return (float(close.iloc[-1]) / base - 1.0) * 100.0


def _slope_pct(series: pd.Series, n: int = 20) -> Optional[float]:
    """Độ dốc % của một đường (MA) trong n phiên."""
    s = series.dropna()
    if len(s) <= n:
        return None
    base = float(s.iloc[-1 - n])
    if not base:
        return None
    return (float(s.iloc[-1]) / base - 1.0) * 100.0


def _fmt_date(d) -> str:
    return d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)


def _fmt_short(d) -> str:
    return d.strftime("%d/%m") if hasattr(d, "strftime") else str(d)


def price_multiplier(close: float) -> float:
    """vnstock trả giá cổ phiếu theo nghìn đồng (VD 21.2 = 21.200đ)."""
    return 1000.0 if close < 1000 else 1.0


def is_partial_session(last_date) -> bool:
    """Phiên cuối là hôm nay và chưa qua 15h → số liệu khối lượng chưa chốt."""
    if not hasattr(last_date, "date"):
        return False
    now = datetime.now(VN_TZ)
    return last_date.date() == now.date() and now.weekday() < 5 and now.hour < 15


# ----------------------------------------------------------------------------------------------
# Chỉ báo bổ sung
# ----------------------------------------------------------------------------------------------
def atr_wilder(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def _ensure_indicators(df: pd.DataFrame) -> pd.DataFrame:
    needed = {"EMA10", "SMA20", "MA50", "MA200", "RSI", "MACD", "Signal", "Histogram", "VolMA20"}
    if not needed.issubset(df.columns):
        df = calculate_indicators(df)
    df = df.copy()
    df["ATR14"] = atr_wilder(df)
    return df


# ----------------------------------------------------------------------------------------------
# 1. Xu hướng (phân giai đoạn kiểu Stan Weinstein)
# ----------------------------------------------------------------------------------------------
def _trend_regime(df: pd.DataFrame) -> dict:
    close = df["Close"]
    c = float(close.iloc[-1])
    m20 = _num(df["SMA20"].iloc[-1])
    m50 = _num(df["MA50"].iloc[-1])
    m200 = _num(df["MA200"].iloc[-1])
    s50 = _slope_pct(df["MA50"], 20)
    s200 = _slope_pct(df["MA200"], 20)

    out = {
        "stage": None,
        "label": "Chưa đủ dữ liệu xác định xu hướng",
        "ma20": m20, "ma50": m50, "ma200": m200,
        "ma50_slope_20d_pct": _num(s50), "ma200_slope_20d_pct": _num(s200),
        "vs_ma20_pct": _num((c / m20 - 1) * 100) if m20 else None,
        "vs_ma50_pct": _num((c / m50 - 1) * 100) if m50 else None,
        "vs_ma200_pct": _num((c / m200 - 1) * 100) if m200 else None,
    }

    if m50 and m200 and s200 is not None:
        aligned_up = m20 and c > m20 > m50 > m200
        aligned_down = m20 and c < m20 < m50 < m200
        out["ma_alignment"] = (
            "Xếp chồng tăng hoàn hảo (Giá > MA20 > MA50 > MA200)" if aligned_up
            else "Xếp chồng giảm (Giá < MA20 < MA50 < MA200)" if aligned_down
            else "Các đường MA đan xen (chưa đồng thuận)"
        )
        if c > m50 > m200 and s200 > 0:
            out.update(stage=2, label="Giai đoạn 2 – Xu hướng tăng (giá trên MA50 & MA200 đang dốc lên)")
        elif c < m50 < m200 and s200 < 0:
            out.update(stage=4, label="Giai đoạn 4 – Xu hướng giảm (giá dưới MA50 & MA200 đang dốc xuống)")
        elif abs(s200) <= 1.0 and abs(c / m200 - 1) <= 0.10:
            prior = float(close.iloc[-121]) if len(close) > 121 else c
            if prior > m200 * 1.08:
                out.update(stage=3, label="Giai đoạn 3 – Đi ngang sau nhịp tăng (rủi ro phân phối đỉnh)")
            else:
                out.update(stage=1, label="Giai đoạn 1 – Tích lũy nền (MA200 đi ngang)")
        elif c > m200 and s200 > 0 and c <= m50:
            out.update(stage=2, label="Giai đoạn 2 – Nhịp điều chỉnh trong xu hướng tăng (giá về dưới MA50, trên MA200)")
        elif c < m200 and s200 < 0 and c >= m50:
            out.update(stage=4, label="Giai đoạn 4 – Hồi phục kỹ thuật trong xu hướng giảm (giá trên MA50, dưới MA200 dốc xuống)")
        elif c > m200 and s200 <= 0:
            out.update(stage=1, label="Giai đoạn 1→2 – Nỗ lực đảo chiều (giá vượt MA200 khi MA200 chưa dốc lên)")
        elif c < m200 and s200 > 0:
            out.update(stage=3, label="Giai đoạn 3 – Suy yếu (giá thủng MA200 khi MA200 vẫn dốc lên)")
    elif m50 and s50 is not None:
        out["ma_alignment"] = "Chưa đủ 200 phiên để tính MA200"
        if c > m50 and s50 > 0:
            out.update(stage=2, label="Xu hướng tăng ngắn–trung hạn (chưa đủ dữ liệu MA200)")
        elif c < m50 and s50 < 0:
            out.update(stage=4, label="Xu hướng giảm ngắn–trung hạn (chưa đủ dữ liệu MA200)")
        else:
            out.update(stage=1, label="Đi ngang / chưa rõ xu hướng (chưa đủ dữ liệu MA200)")
    return out


# ----------------------------------------------------------------------------------------------
# 2. Động lượng & phân kỳ
# ----------------------------------------------------------------------------------------------
def _local_extrema(series: pd.Series, window: int = 3):
    span = 2 * window + 1
    roll_max = series.rolling(span, center=True).max()
    roll_min = series.rolling(span, center=True).min()
    highs = series[(series == roll_max)].dropna()
    lows = series[(series == roll_min)].dropna()
    return highs, lows


def _momentum(df: pd.DataFrame) -> dict:
    rsi = df["RSI"]
    macd, sig, hist = df["MACD"], df["Signal"], df["Histogram"]
    diff_sign = np.sign(macd - sig)
    cross_idx = diff_sign.ne(diff_sign.shift(1)) & diff_sign.shift(1).notna()
    crosses = list(np.where(cross_idx.values)[0])
    bars_since_cross = (len(df) - 1 - crosses[-1]) if crosses else None
    last_hist = hist.tail(4).values
    hist_trend = None
    if len(last_hist) == 4:
        d = np.diff(last_hist)
        hist_trend = "mở rộng" if (d > 0).all() else "thu hẹp" if (d < 0).all() else "dao động"

    out = {
        "rsi": _num(rsi.iloc[-1]),
        "rsi_5d_ago": _num(rsi.iloc[-6]) if len(rsi) > 6 else None,
        "macd": _num(macd.iloc[-1], 3),
        "signal": _num(sig.iloc[-1], 3),
        "histogram": _num(hist.iloc[-1], 3),
        "macd_vs_signal": "trên" if macd.iloc[-1] > sig.iloc[-1] else "dưới",
        "macd_vs_zero": "trên" if macd.iloc[-1] > 0 else "dưới",
        "bars_since_macd_cross": int(bars_since_cross) if bars_since_cross is not None else None,
        "histogram_trend_3d": hist_trend,
        "divergence": None,
    }

    # Phân kỳ RSI trên 60 phiên gần nhất (so 2 đỉnh / 2 đáy cục bộ gần nhất)
    tail = df.tail(60)
    highs, lows = _local_extrema(tail["Close"], window=3)
    try:
        if len(highs) >= 2:
            d1, d2 = highs.index[-2], highs.index[-1]
            if highs[d2] > highs[d1] and tail.loc[d2, "RSI"] < tail.loc[d1, "RSI"] - 2:
                out["divergence"] = (
                    f"Phân kỳ âm: đỉnh giá {_fmt_short(d2)} ({highs[d2]:.2f}) cao hơn đỉnh {_fmt_short(d1)} ({highs[d1]:.2f}) "
                    f"nhưng RSI thấp hơn ({tail.loc[d2, 'RSI']:.1f} < {tail.loc[d1, 'RSI']:.1f}) → động lượng tăng suy yếu"
                )
        if out["divergence"] is None and len(lows) >= 2:
            d1, d2 = lows.index[-2], lows.index[-1]
            if lows[d2] < lows[d1] and tail.loc[d2, "RSI"] > tail.loc[d1, "RSI"] + 2:
                out["divergence"] = (
                    f"Phân kỳ dương: đáy giá {_fmt_short(d2)} ({lows[d2]:.2f}) thấp hơn đáy {_fmt_short(d1)} ({lows[d1]:.2f}) "
                    f"nhưng RSI cao hơn ({tail.loc[d2, 'RSI']:.1f} > {tail.loc[d1, 'RSI']:.1f}) → lực bán suy yếu"
                )
    except Exception:
        pass
    return out


# ----------------------------------------------------------------------------------------------
# 3. Biến động, đỉnh/đáy 52 tuần, nền giá, gap
# ----------------------------------------------------------------------------------------------
def _volatility_and_range(df: pd.DataFrame) -> dict:
    close = df["Close"]
    c = float(close.iloc[-1])
    atr = _num(df["ATR14"].iloc[-1], 3)
    logret = np.log(close / close.shift(1)).dropna()
    dvol = float(logret.tail(60).std()) if len(logret) >= 20 else None

    y = df.tail(250)
    hi52 = float(y["High"].max())
    lo52 = float(y["Low"].min())
    hi52_date = y["High"].idxmax()
    lo52_date = y["Low"].idxmin()
    run_max = y["Close"].cummax()
    mdd = float(((y["Close"] / run_max) - 1).min() * 100)

    t15 = df.tail(15)
    t60 = df.tail(60)
    tight15 = (float(t15["High"].max()) - float(t15["Low"].min())) / c * 100
    range60 = (float(t60["High"].max()) - float(t60["Low"].min())) / c * 100
    contraction = tight15 / range60 if range60 else None

    # Khoảng trống giá (gap) chưa lấp trong 60 phiên
    gaps = []
    d = df.tail(61)
    highs, lows = d["High"].values, d["Low"].values
    dates = d.index
    for i in range(1, len(d)):
        if lows[i] > highs[i - 1] * 1.001:
            filled = (lows[i:].min() <= highs[i - 1]) if i < len(d) else False
            if not filled:
                gaps.append({"type": "Gap tăng", "date": _fmt_short(dates[i]), "zone": f"{highs[i-1]:.2f}–{lows[i]:.2f}", "role": "hỗ trợ"})
        elif highs[i] < lows[i - 1] * 0.999:
            filled = (highs[i:].max() >= lows[i - 1]) if i < len(d) else False
            if not filled:
                gaps.append({"type": "Gap giảm", "date": _fmt_short(dates[i]), "zone": f"{highs[i]:.2f}–{lows[i-1]:.2f}", "role": "kháng cự"})

    base = None
    near_high = (c / hi52 - 1) * 100 >= -10 if hi52 else False
    if contraction is not None and tight15 <= 12 and contraction <= 0.55:
        base = (
            f"Nền giá co hẹp: biên độ 15 phiên chỉ {tight15:.1f}% (bằng {contraction*100:.0f}% biên độ 60 phiên)"
            + (" — nằm gần đỉnh 52 tuần, dạng nền chặt trước bứt phá (VCP)" if near_high else "")
        )

    return {
        "atr14": atr,
        "atr_pct": _num(atr / c * 100) if atr else None,
        "daily_vol_pct": _num(dvol * 100) if dvol else None,
        "annual_vol_pct": _num(dvol * math.sqrt(250) * 100) if dvol else None,
        "high_52w": _num(hi52), "high_52w_date": _fmt_date(hi52_date),
        "low_52w": _num(lo52), "low_52w_date": _fmt_date(lo52_date),
        "from_52w_high_pct": _num((c / hi52 - 1) * 100) if hi52 else None,
        "from_52w_low_pct": _num((c / lo52 - 1) * 100) if lo52 else None,
        "max_drawdown_1y_pct": _num(mdd),
        "range_15d_pct": _num(tight15),
        "range_60d_pct": _num(range60),
        "base_pattern": base,
        "unfilled_gaps": gaps[-3:],
    }


# ----------------------------------------------------------------------------------------------
# 4. Dòng tiền & khối lượng
# ----------------------------------------------------------------------------------------------
def _flow(df: pd.DataFrame, partial: bool) -> dict:
    d = df.iloc[:-1] if (partial and len(df) > 30) else df
    close, vol = d["Close"], d["Volume"].astype(float)
    chg = close.pct_change()
    t20 = d.tail(20)
    c20 = chg.tail(20)
    up_vol = float(t20["Volume"][c20 > 0].sum())
    dn_vol = float(t20["Volume"][c20 < 0].sum())
    ud_ratio = up_vol / dn_vol if dn_vol > 0 else None

    dist = int(((chg < -0.002) & (vol > vol.shift(1))).tail(25).sum())
    accu = int(((chg > 0.002) & (vol > vol.shift(1))).tail(25).sum())

    obv = (np.sign(chg).fillna(0) * vol).cumsum()
    obv_score = None
    if len(obv) > 21 and vol.tail(20).sum() > 0:
        obv_score = float((obv.iloc[-1] - obv.iloc[-21]) / vol.tail(20).sum())

    spikes = []
    if "VolMA20" in d.columns:
        tail = d.tail(20)
        for idx, row in tail.iterrows():
            vma = row.get("VolMA20")
            if vma and not pd.isna(vma) and row["Volume"] > 1.8 * vma:
                pct = chg.loc[idx] * 100 if not pd.isna(chg.loc[idx]) else 0.0
                spikes.append(f"{_fmt_short(idx)}: KL {row['Volume']/vma:.1f}× TB20, giá {pct:+.2f}%")

    mult = price_multiplier(float(close.iloc[-1]))
    value_series = (close * vol) * mult / 1e9
    avg_val20 = float(value_series.tail(20).mean())
    vma_now = d["VolMA20"].iloc[-1] if "VolMA20" in d.columns else None
    vma_prev = d["VolMA20"].iloc[-21] if "VolMA20" in d.columns and len(d) > 21 else None
    liq_trend = _num((vma_now / vma_prev - 1) * 100) if vma_now and vma_prev else None

    last_vol_ratio = None
    if "VolMA20" in df.columns and df["VolMA20"].iloc[-1]:
        last_vol_ratio = _num(float(df["Volume"].iloc[-1]) / float(df["VolMA20"].iloc[-1]))

    if ud_ratio is None:
        verdict = "Không xác định"
    elif ud_ratio >= 1.4 and accu > dist:
        verdict = "Tích lũy (khối lượng phiên tăng áp đảo phiên giảm)"
    elif ud_ratio <= 0.75 and dist > accu:
        verdict = "Phân phối (khối lượng phiên giảm áp đảo phiên tăng)"
    else:
        verdict = "Cân bằng / giằng co"

    return {
        "up_down_volume_ratio_20d": _num(ud_ratio),
        "distribution_days_25": dist,
        "accumulation_days_25": accu,
        "obv_trend_score_20d": _num(obv_score),
        "flow_verdict": verdict,
        "volume_spikes_20d": spikes[-5:],
        "avg_value_20d_bn": _num(avg_val20, 1),
        "liquidity_tier": "Cao" if avg_val20 >= 100 else "Trung bình" if avg_val20 >= 20 else "Thấp (rủi ro thoát hàng)",
        "liquidity_trend_20d_pct": liq_trend,
        "last_session_vol_ratio": last_vol_ratio,
        "last_session_partial": partial,
    }


# ----------------------------------------------------------------------------------------------
# 5. Sức mạnh tương đối so với VN-Index
# ----------------------------------------------------------------------------------------------
def _relative_strength(df: pd.DataFrame, idx_df: Optional[pd.DataFrame]) -> Optional[dict]:
    if idx_df is None or idx_df.empty:
        return None
    j = pd.concat([df["Close"].rename("s"), idx_df["Close"].rename("i")], axis=1, join="inner").dropna()
    if len(j) < 30:
        return None
    out = {}
    for n in (5, 20, 60, 120, 250):
        if len(j) > n:
            rs_ = (j["s"].iloc[-1] / j["s"].iloc[-1 - n] - 1) * 100
            ri_ = (j["i"].iloc[-1] / j["i"].iloc[-1 - n] - 1) * 100
            out[f"stock_{n}d"] = _num(rs_)
            out[f"index_{n}d"] = _num(ri_)
            out[f"excess_{n}d"] = _num(rs_ - ri_)
    r = j.pct_change().dropna().tail(120)
    if len(r) >= 30 and r["i"].var() > 0:
        out["beta_120d"] = _num(r["s"].cov(r["i"]) / r["i"].var())
        out["corr_120d"] = _num(r["s"].corr(r["i"]))
    rs_line = j["s"] / j["i"]
    rs_ma50 = rs_line.rolling(50).mean()
    if not pd.isna(rs_ma50.iloc[-1]):
        out["rs_line_vs_ma50"] = "trên" if rs_line.iloc[-1] > rs_ma50.iloc[-1] else "dưới"
    out["rs_line_near_6m_high"] = bool(rs_line.iloc[-1] >= rs_line.tail(120).max() * 0.98)
    ex60 = out.get("excess_60d")
    ex20 = out.get("excess_20d")
    if ex60 is not None and ex20 is not None:
        if ex60 > 5 and ex20 > 0:
            out["verdict"] = "Dẫn dắt — mạnh hơn thị trường cả 1 và 3 tháng"
        elif ex60 < -5 and ex20 < 0:
            out["verdict"] = "Tụt hậu — yếu hơn thị trường cả 1 và 3 tháng"
        elif ex20 > 0 >= ex60:
            out["verdict"] = "Đang cải thiện — 1 tháng gần đây mạnh lên so với thị trường"
        elif ex20 < 0 <= ex60:
            out["verdict"] = "Đang suy yếu — 1 tháng gần đây kém thị trường"
        else:
            out["verdict"] = "Đồng pha với thị trường"
    return out


# ----------------------------------------------------------------------------------------------
# 6. Vùng giá quan trọng có cơ sở (pivot + MA + volume profile + đỉnh/đáy 52 tuần)
# ----------------------------------------------------------------------------------------------
def _volume_profile(df: pd.DataFrame, lookback: int = 120, bins: int = 30) -> Optional[dict]:
    d = df.tail(lookback)
    lo, hi = float(d["Low"].min()), float(d["High"].max())
    if hi <= lo or d["Volume"].sum() <= 0:
        return None
    edges = np.linspace(lo, hi, bins + 1)
    tp = ((d["High"] + d["Low"] + d["Close"]) / 3).values
    idx = np.clip(np.digitize(tp, edges) - 1, 0, bins - 1)
    vol = np.zeros(bins)
    np.add.at(vol, idx, d["Volume"].values.astype(float))
    poc_i = int(vol.argmax())
    total, acc, l, r = vol.sum(), vol[poc_i], poc_i, poc_i
    while acc < 0.7 * total and (l > 0 or r < bins - 1):
        left = vol[l - 1] if l > 0 else -1
        right = vol[r + 1] if r < bins - 1 else -1
        if right >= left:
            r += 1
            acc += vol[r]
        else:
            l -= 1
            acc += vol[l]
    return {
        "poc": float((edges[poc_i] + edges[poc_i + 1]) / 2),
        "va_low": float(edges[l]),
        "va_high": float(edges[r + 1]),
        "lookback": lookback,
    }


def _key_levels(df: pd.DataFrame, atr: float) -> dict:
    c = float(df["Close"].iloc[-1])
    look = df.tail(250)
    recent_cut = look.index[-60] if len(look) > 60 else look.index[0]
    cands = []

    span = 11  # pivot cửa sổ ±5 phiên
    rmax = look["High"].rolling(span, center=True).max()
    rmin = look["Low"].rolling(span, center=True).min()
    for d in look.index[(look["High"] == rmax)]:
        w = 1.5 if d >= recent_cut else 1.0
        cands.append({"price": float(look.loc[d, "High"]), "label": f"Đỉnh swing {_fmt_short(d)}", "weight": w, "pivot": True})
    for d in look.index[(look["Low"] == rmin)]:
        w = 1.5 if d >= recent_cut else 1.0
        cands.append({"price": float(look.loc[d, "Low"]), "label": f"Đáy swing {_fmt_short(d)}", "weight": w, "pivot": True})

    for col, label, w in (("SMA20", "MA20", 0.8), ("MA50", "MA50", 1.2), ("MA200", "MA200", 1.6)):
        v = df[col].iloc[-1] if col in df.columns else None
        if v is not None and not pd.isna(v):
            cands.append({"price": float(v), "label": label, "weight": w, "pivot": False})

    vp = _volume_profile(df)
    if vp:
        cands.append({"price": vp["poc"], "label": "Vùng khối lượng lớn nhất 6 tháng (POC)", "weight": 1.5, "pivot": False})
        cands.append({"price": vp["va_low"], "label": "Cận dưới vùng giá trị 70% KL (VAL)", "weight": 0.7, "pivot": False})
        cands.append({"price": vp["va_high"], "label": "Cận trên vùng giá trị 70% KL (VAH)", "weight": 0.7, "pivot": False})

    cands.append({"price": float(look["High"].max()), "label": "Đỉnh 52 tuần", "weight": 1.3, "pivot": False})
    cands.append({"price": float(look["Low"].min()), "label": "Đáy 52 tuần", "weight": 1.3, "pivot": False})
    cands.append({"price": float(df["Low"].tail(10).min()), "label": "Đáy ngắn hạn 10 phiên", "weight": 0.8, "pivot": False})
    cands.append({"price": float(df["High"].tail(10).max()), "label": "Đỉnh ngắn hạn 10 phiên", "weight": 0.8, "pivot": False})

    tol = max(0.6 * atr if atr else 0, c * 0.012)
    cands.sort(key=lambda x: x["price"])
    clusters = []
    for cd in cands:
        if clusters and abs(cd["price"] - clusters[-1]["ref"]) <= tol:
            cl = clusters[-1]
            cl["items"].append(cd)
            wsum = sum(i["weight"] for i in cl["items"])
            cl["ref"] = sum(i["price"] * i["weight"] for i in cl["items"]) / wsum
        else:
            clusters.append({"ref": cd["price"], "items": [cd]})

    levels = []
    for cl in clusters:
        strength = sum(i["weight"] for i in cl["items"])
        labels, seen = [], set()
        for it in sorted(cl["items"], key=lambda i: -i["weight"]):
            if it["label"] not in seen:
                seen.add(it["label"])
                labels.append(it["label"])
        levels.append({
            "price": round(cl["ref"], 2),
            "basis": "; ".join(labels[:3]) + (f" (+{len(labels)-3} cơ sở khác)" if len(labels) > 3 else ""),
            "touches": sum(1 for i in cl["items"] if i["pivot"]),
            "strength": "Mạnh" if strength >= 3 else "Trung bình" if strength >= 1.8 else "Yếu",
            "score": round(strength, 2),
        })

    supports = sorted([lv for lv in levels if lv["price"] < c * 0.995], key=lambda x: -x["price"])[:3]
    resistances = sorted([lv for lv in levels if lv["price"] > c * 1.005], key=lambda x: x["price"])[:3]
    for lv in supports + resistances:
        lv["distance_pct"] = round((lv["price"] / c - 1) * 100, 2)
    if not resistances and atr:
        resistances = [{
            "price": round(c + 2 * atr, 2), "basis": "Vùng giá mới – không có kháng cự lịch sử (ước lượng 2×ATR)",
            "touches": 0, "strength": "Yếu", "score": 0, "distance_pct": round(2 * atr / c * 100, 2),
        }]
    return {"supports": supports, "resistances": resistances, "volume_profile": vp}


# ----------------------------------------------------------------------------------------------
# 7. Xác suất lịch sử (base rates) của trạng thái hiện tại
# ----------------------------------------------------------------------------------------------
RSI_BINS = [-1, 30, 45, 55, 70, 101]
RSI_LABELS = ["<30 (quá bán)", "30–45 (yếu)", "45–55 (trung tính)", "55–70 (mạnh)", ">70 (quá mua)"]


def _base_rates(df: pd.DataFrame, horizons=(10, 20)) -> Optional[dict]:
    close, rsi, ma50 = df["Close"], df["RSI"], df["MA50"]
    valid = ma50.notna() & rsi.notna()
    if valid.sum() < 120:
        return None
    above = close > ma50
    bucket = pd.cut(rsi, RSI_BINS, labels=RSI_LABELS)
    cur_above, cur_bucket = bool(above.iloc[-1]), bucket.iloc[-1]
    mask = valid & (above == cur_above) & (bucket == cur_bucket)
    res = {}
    for h in horizons:
        fwd = (close.shift(-h) / close - 1) * 100
        sample = fwd[mask].dropna()
        allv = fwd[valid].dropna()
        if len(sample) >= 8:
            res[str(h)] = {
                "n": int(len(sample)),
                "win_rate": _num((sample > 0).mean() * 100, 1),
                "median": _num(sample.median()),
                "p10": _num(sample.quantile(0.10)),
                "p90": _num(sample.quantile(0.90)),
                "all_days_win_rate": _num((allv > 0).mean() * 100, 1),
                "all_days_median": _num(allv.median()),
            }
    if not res:
        return None
    return {
        "condition": f"Giá {'trên' if cur_above else 'dưới'} MA50 & RSI {cur_bucket}",
        "period": f"{_fmt_date(df.index[0])} → {_fmt_date(df.index[-1])}",
        "results": res,
        "note": "Mẫu chồng lấn theo ngày, cỡ mẫu nhỏ → chỉ dùng làm xác suất nền tham khảo, không phải dự báo.",
    }


# ----------------------------------------------------------------------------------------------
# 8. Dải giá thống kê (random-walk theo biến động thực tế)
# ----------------------------------------------------------------------------------------------
def _prob_ranges(close: float, daily_vol_pct: Optional[float], horizons=(1, 2, 5, 10)) -> list:
    if not daily_vol_pct:
        return []
    s = daily_vol_pct / 100.0
    out = []
    for h in horizons:
        sh = s * math.sqrt(h)
        out.append({
            "days": h,
            "low_68": round(close * math.exp(-sh), 2), "high_68": round(close * math.exp(sh), 2),
            "low_95": round(close * math.exp(-1.96 * sh), 2), "high_95": round(close * math.exp(1.96 * sh), 2),
        })
    return out


# ----------------------------------------------------------------------------------------------
# 9. Kế hoạch giao dịch cơ sở (deterministic) — AI được phép tinh chỉnh nhưng phải giải thích
# ----------------------------------------------------------------------------------------------
def _baseline_plan(close: float, atr: float, levels: dict, stage: Optional[int], risk_profile: str,
                   cost_basis: Optional[float] = None) -> dict:
    risk_nav, max_w = RISK_PROFILES.get(risk_profile, RISK_PROFILES["Trung bình"])
    atr = atr or close * 0.02
    sup = [s["price"] for s in levels.get("supports", [])]
    res = [r["price"] for r in levels.get("resistances", [])]
    s1 = sup[0] if sup else close - 2 * atr
    r1 = res[0] if res else close + 2.5 * atr

    near_support = (close - s1) <= max(1.2 * atr, close * 0.025)
    near_breakout = (r1 - close) <= max(0.8 * atr, close * 0.015)

    if near_breakout and stage in (1, 2):
        setup = "Mua khi bứt phá kháng cự"
        entry_low, entry_high = r1, r1 + 0.5 * atr
        trigger = f"Chỉ mua khi giá ĐÓNG CỬA trên {r1:.2f} với khối lượng ≥ 1,5× TB20 (bứt phá thật, không phải bẫy)"
        stop = entry_low - 1.5 * atr
        stop_basis = "Dưới điểm bứt phá 1,5×ATR — bứt phá thất bại khi giá quay lại sâu dưới kháng cự cũ"
    elif near_support:
        setup = "Mua tại vùng hỗ trợ"
        entry_low = s1
        entry_high = min(max(close, s1 + 0.3 * atr), s1 + 0.8 * atr)
        trigger = f"Giá giữ vững trên {s1:.2f} (không đóng cửa thủng), xuất hiện nến rút chân hoặc khối lượng bán cạn dần"
        stop = s1 - 0.75 * atr
        stop_basis = f"Dưới hỗ trợ {s1:.2f} một khoảng 0,75×ATR để tránh nhiễu"
    else:
        setup = "Chờ điều chỉnh về hỗ trợ (không mua đuổi)"
        entry_low, entry_high = s1, s1 + 0.6 * atr
        trigger = f"Giá đang cách hỗ trợ {s1:.2f} khoảng {(close/s1-1)*100:.1f}% → chờ lùi về vùng mua, hoặc chờ bứt phá {r1:.2f} kèm khối lượng"
        stop = s1 - 0.75 * atr
        stop_basis = f"Dưới hỗ trợ {s1:.2f} một khoảng 0,75×ATR"

    mid = (entry_low + entry_high) / 2
    # Hàng mua chưa về trong ~2,5 phiên (T+2) → biến động kỳ vọng ≈ ATR×√2,5 ≈ 1,6×ATR.
    # Cắt lỗ sát hơn 1,5×ATR thường bị "quét" trước khi kịp bán → nới tối thiểu 1,5×ATR (tối đa 12%).
    raw_dist = mid - stop
    stop_dist = min(max(raw_dist, 1.5 * atr), mid * 0.12)
    if stop_dist > raw_dist + 1e-9:
        stop_basis += " — đã nới tối thiểu 1,5×ATR vì hàng T+2 chưa về, không thể cắt lỗ sớm hơn"
    stop = mid - stop_dist
    targets = [r for r in res if r > entry_high + 0.5 * atr]
    t1 = targets[0] if targets else mid + 2 * stop_dist
    t2 = targets[1] if len(targets) > 1 else max(t1 + 1.5 * atr, mid + 3 * stop_dist)
    rr = (t1 - mid) / stop_dist if stop_dist > 0 else None
    stop_pct = stop_dist / mid * 100
    weight = min(max_w, risk_nav / stop_pct * 100) if stop_pct > 0 else max_w
    if stage == 4:
        setup = "Đứng ngoài – chỉ mua thăm dò khi có tín hiệu đảo chiều xác nhận"
        weight = min(weight, max_w * 0.3)
    quality = (
        "Đạt chuẩn (R:R ≥ 2)" if rr and rr >= 2
        else "Tạm chấp nhận (R:R 1,5–2)" if rr and rr >= 1.5
        else "Không đạt – lợi nhuận kỳ vọng không bù được rủi ro, chờ giá tốt hơn"
    )

    exit_stops = {
        "price_stop": {
            "price": round(stop, 2),
            "pct": -round(stop_pct, 1),
            "distance_pct": round(stop_pct, 1),
            "desc": stop_basis,
            "basis": stop_basis,
            "action": "Kích hoạt lệnh dừng tự động (Stop-Order) cắt lỗ 100% vị thế, không do dự",
        },
        "thesis_stop": {
            "price": round(entry_low - 0.5 * atr, 2),
            "condition": (
                f"Gãy hỗ trợ {s1:.2f} kèm vol > 1,5× TB20 hoặc giảm > 3% làm gãy cấu trúc tích lũy"
                if near_support
                else f"Bứt phá giả (Bull-trap), giá đảo chiều đóng cửa lùi sâu dưới {r1:.2f}"
                if near_breakout
                else "Gãy MA50 kèm vol lớn hoặc luận điểm đầu tư ban đầu bị bác bỏ"
            ),
            "trigger_signals": [
                "Gãy nền hỗ trợ then chốt kèm khối lượng đột biến",
                "Khối ngoại hoặc tự doanh xả ròng bất thường",
                "Luận điểm vĩ mô/ngành bị phủ định",
            ],
            "action": "Bán chủ động ngay trong phiên (kể cả hòa vốn hoặc lỗ nhẹ), không chờ chạm Price-Stop",
        },
        "time_stop": {
            "sessions": 10,
            "max_sessions": 10,
            "condition": "Sau T+10 không vượt được mục tiêu 1 và thanh khoản trôi dưới MA20",
            "action": "Sau T+10 không bứt phá khỏi vùng nền thì hạ 50% tỷ trọng, sau T+15 tất toán để thu hồi vốn",
        },
    }

    plan = {
        "setup_type": setup,
        "entry_low": round(entry_low, 2), "entry_high": round(entry_high, 2),
        "entry_trigger": trigger,
        "stop_loss": round(stop, 2), "stop_basis": stop_basis, "stop_pct": round(stop_pct, 2),
        "target_1": round(t1, 2), "target_2": round(t2, 2),
        "rr_ratio": round(rr, 2) if rr else None,
        "rr_quality": quality,
        "max_position_pct": round(weight, 1),
        "risk_per_trade_pct_nav": risk_nav,
        "sizing_rule": f"Tỷ trọng = {risk_nav}% NAV rủi ro / {stop_pct:.1f}% khoảng cắt lỗ → tối đa {weight:.1f}% NAV (trần {max_w:.0f}% theo khẩu vị)",
        "time_stop": "Nếu sau 15 phiên giá không vượt được mục tiêu 1 và hụt hơi dưới MA20 → hạ 1/2 vị thế",
        "exit_stops": exit_stops,
    }
    if cost_basis:
        pnl = (close / cost_basis - 1) * 100
        trail = max(stop, close - 2.5 * atr)
        plan["holder"] = {
            "cost_basis": round(cost_basis, 2),
            "pnl_pct": round(pnl, 2),
            "trailing_stop": round(trail, 2),
            "note": (
                f"Đang {'lãi' if pnl >= 0 else 'lỗ'} {pnl:+.1f}%. Ngưỡng bảo vệ/dừng lỗ động tham khảo {trail:.2f} "
                f"(= max(cắt lỗ kỹ thuật, giá − 2,5×ATR))."
            ),
        }
    return plan


# ----------------------------------------------------------------------------------------------
# 10. "Thời tiết" thị trường
# ----------------------------------------------------------------------------------------------
def market_regime(idx_df: Optional[pd.DataFrame], vn30_df: Optional[pd.DataFrame] = None) -> Optional[dict]:
    if idx_df is None or idx_df.empty or len(idx_df) < 30:
        return None
    d = _ensure_indicators(idx_df)
    close = d["Close"]
    trend = _trend_regime(d)
    vr = _volatility_and_range(d)
    partial = is_partial_session(d.index[-1])
    dd = d.iloc[:-1] if partial else d
    chg = dd["Close"].pct_change()
    vol = dd["Volume"].astype(float)
    dist = int(((chg < -0.002) & (vol > vol.shift(1))).tail(25).sum())
    ftd = int(((chg > 0.012) & (vol > vol.shift(1))).tail(10).sum())

    stage = trend.get("stage")
    if stage == 2 and dist <= 4:
        status, alloc = "🟢 Thuận lợi", "70–100%"
    elif stage == 4 or dist >= 6:
        status, alloc = "🔴 Rủi ro cao", "0–40%"
    else:
        status, alloc = "🟡 Trung tính", "40–70%"

    out = {
        "date": _fmt_date(d.index[-1]) + (" (phiên đang giao dịch, chưa chốt)" if partial else ""),
        "close": _num(close.iloc[-1]),
        "change_1d_pct": _num(_ret(close, 1)),
        "ret_5d": _num(_ret(close, 5)), "ret_20d": _num(_ret(close, 20)), "ret_60d": _num(_ret(close, 60)),
        "trend": trend,
        "rsi": _num(d["RSI"].iloc[-1]),
        "from_52w_high_pct": vr.get("from_52w_high_pct"),
        "distribution_days_25": dist,
        "strong_up_days_10": ftd,
        "volume_vs_ma20": _num(float(d["Volume"].iloc[-1]) / float(d["VolMA20"].iloc[-1])) if d["VolMA20"].iloc[-1] else None,
        "status": status,
        "equity_allocation": alloc,
        "recent": [
            f"{_fmt_short(i)}: {c_:.2f} ({p_:+.2f}%) | KL {v_:,.0f}"
            for i, c_, p_, v_ in zip(d.index[-5:], close.iloc[-5:], close.pct_change().iloc[-5:] * 100, d["Volume"].iloc[-5:])
        ],
    }
    if vn30_df is not None and not vn30_df.empty and len(vn30_df) > 21:
        v30 = vn30_df["Close"]
        out["vn30_close"] = _num(v30.iloc[-1])
        out["vn30_ret_20d"] = _num(_ret(v30, 20))
        if out.get("ret_20d") is not None and out["vn30_ret_20d"] is not None:
            gap = out["vn30_ret_20d"] - out["ret_20d"]
            out["vn30_vs_vnindex_20d"] = _num(gap)
            out["breadth_hint"] = (
                "VN30 mạnh hơn VN-Index → dòng tiền tập trung nhóm trụ, cẩn trọng 'xanh vỏ đỏ lòng'" if gap > 1.5
                else "VN30 yếu hơn VN-Index → nhóm vốn hóa lớn bị bán, dòng tiền dịch chuyển sang mid/small-cap" if gap < -1.5
                else "VN30 và VN-Index đồng pha"
            )
    return out


# ----------------------------------------------------------------------------------------------
# 11. Xếp hạng trong ngành
# ----------------------------------------------------------------------------------------------
def sector_ranking(symbol: str, stock_ret20: Optional[float], stock_ret60: Optional[float], peers: dict) -> Optional[dict]:
    rows = [{"symbol": symbol, "ret20": stock_ret20, "ret60": stock_ret60}]
    for p, info in (peers or {}).items():
        if isinstance(info, dict):
            rows.append({"symbol": p, "ret20": info.get("Ret20"), "ret60": info.get("Ret60")})
    rows = [r for r in rows if r["ret20"] is not None]
    if len(rows) < 3:
        return None
    rows.sort(key=lambda r: -(r["ret60"] if r["ret60"] is not None else r["ret20"]))
    rank = next(i for i, r in enumerate(rows) if r["symbol"] == symbol) + 1
    med20 = float(np.median([r["ret20"] for r in rows if r["symbol"] != symbol]))
    return {
        "rank": rank, "of": len(rows),
        "peer_median_ret20": _num(med20),
        "table": rows,
        "verdict": "Cổ phiếu dẫn đầu nhóm ngành" if rank == 1 else (
            "Nhóm mạnh trong ngành" if rank <= max(2, len(rows) // 3) else
            "Nhóm yếu trong ngành" if rank > len(rows) * 2 // 3 else "Trung bình ngành"),
    }


# ----------------------------------------------------------------------------------------------
# 12. Bộ Quy Tắc Thực Chiến 6 Bước (Định danh Tạo lập, Tape Reading, Chu kỳ T+2.5, Chốt lời 3 nhịp)
# ----------------------------------------------------------------------------------------------
ARCHETYPE_GROUPS = {
    "INDEX_PILLAR": {
        "symbols": {"VIC", "VHM", "VRE", "VNM", "SAB", "MSN", "BVH", "VJC", "BCM"},
        "code": "Nhóm 1: Trụ điều tiết chỉ số (Cô đặc)",
        "nature": (
            "Dùng lượng vốn nhỏ để kéo/đè điểm số VN-Index và VN30 phục vụ Phái sinh hoặc giữ nhịp thị trường. "
            "Cổ phiếu cô đặc trong tay tổ chức lớn."
        ),
        "core_rule": (
            "Phân biệt rõ 'Tiết cung' (cạn người bán, kéo nhẹ là bay) với 'Kéo xả'. "
            "Khi đã có vị thế tốt, tuyệt đối không bán hết 1 lệnh mà phải dùng chặn lãi trượt (Trailing Stop 1,5%–2%)."
        ),
        "tier1_gain_pct": 6.0,
    },
    "HIGH_BETA_ECOSYSTEM": {
        "symbols": {
            "VIX", "GEX", "VSC", "EIB", "NVL", "DIG", "PDR", "CEO", "DXG", "SHS",
            "VND", "ORS", "TCH", "HHS", "CII", "HAG", "DBC", "FTS", "BSI", "CTS", "VCI", "HCM",
        },
        "code": "Nhóm 2: Đầu cơ Hệ sinh thái (High-Beta)",
        "nature": (
            "Vận hành mạnh theo dòng tiền đầu cơ, sở hữu chéo, cầm cố tài sản đảm bảo hoặc kéo giá chốt quý "
            "để hạch toán lãi tự doanh FVTPL. Biên độ cực lớn (tăng trần/giảm sàn nhanh)."
        ),
        "core_rule": (
            "Ưu tiên tuyệt đối dòng tiền & hành vi khối lượng hơn BCTC tĩnh. Chỉ mua sau khi rũ xong hàng T+ "
            "và thoát dứt khoát ngay khi cả cụm hệ sinh thái bị lệnh lớn bán ròng."
        ),
        "tier1_gain_pct": 10.5,
    },
    "CORE_PRODUCTION": {
        "symbols": {
            "HPG", "CTD", "FPT", "DGC", "MWG", "PNJ", "GMD", "ACV", "REE", "BMP", "VHC", "ANV",
            "CTR", "HSG", "NKG", "KBC", "IDC", "SZC", "HHV", "VCG", "PC1", "FRT", "DGW", "QNS",
        },
        "code": "Nhóm 3: Sản xuất cơ bản & Nội tại thật",
        "nature": (
            "Có dòng tiền tổ chức và khối ngoại bảo kê tại vùng giá vốn. Đi lên theo bậc thang hoặc cô đặc "
            "theo đơn hàng/lợi nhuận thực tế nên giữ giá khỏe khi thị trường chung điều chỉnh."
        ),
        "core_rule": (
            "Mua gom tại nền cạn cung (No Supply). Không sợ các nhịp rũ bỏ thanh khoản thấp. "
            "Các nhịp đè giá ngay trước ngày công bố BCTC hợp nhất thường là cơ hội gom hàng của tổ chức."
        ),
        "tier1_gain_pct": 6.5,
    },
    "BANK_LIQUIDITY_KING": {
        "symbols": {
            "TCB", "MBB", "VCB", "BID", "CTG", "ACB", "VPB", "STB", "HDB", "VIB",
            "TPB", "LPB", "SHB", "MSB", "OCB", "SSB",
        },
        "code": "Nhóm 4: Ngân hàng (Vua thanh khoản)",
        "nature": (
            "Nhạy cảm với điểm số VN30, tỷ giá, biên lãi ròng (NIM) và đặc biệt là các sự kiện chia tách tăng vốn / GDKHQ."
        ),
        "core_rule": (
            "Soi kỹ dòng tiền mua/bán ròng tổ chức và tường lệnh đỡ ở bước giá dưới trước khi giải ngân. "
            "Tuyệt đối áp dụng 'Né trước chốt – Bắt sau chia' với lịch GDKHQ chia cổ tức cổ phiếu."
        ),
        "tier1_gain_pct": 6.0,
    },
    "GEOPOLITICAL_DEFENSIVE": {
        "symbols": {
            "OIL", "PVD", "PVS", "PVT", "GAS", "PLX", "BSR", "DPM", "DCM", "HAH", "VOS", "POW", "NT2", "QTP",
        },
        "code": "Nhóm 5: Phòng thủ Địa chính trị & Hàng hóa",
        "nature": (
            "Hút dòng tiền trú ẩn ngắn hạn khi thị trường chung đỏ lửa hoặc căng thẳng địa chính trị / giá dầu leo thang."
        ),
        "core_rule": (
            "Sóng ngắn, hay tạo nến cụt đầu (râu trên dài) khi kéo hưng phấn buổi sáng. "
            "Tuyệt đối không mua đuổi khi đã kéo xanh đầu phiên."
        ),
        "tier1_gain_pct": 6.5,
    },
}


def classify_stock_archetype(symbol: str = "", beta: Optional[float] = None) -> dict:
    sym = (symbol or "").upper().strip()
    for key, info in ARCHETYPE_GROUPS.items():
        if sym in info["symbols"]:
            return {
                "group_key": key,
                "name": info["code"],
                "nature": info["nature"],
                "core_rule": info["core_rule"],
                "tier1_gain_pct": info["tier1_gain_pct"],
            }
    if beta is not None and beta >= 1.3:
        info = ARCHETYPE_GROUPS["HIGH_BETA_ECOSYSTEM"]
        return {
            "group_key": "HIGH_BETA_ECOSYSTEM",
            "name": info["code"] + " (phân loại theo Beta cao)",
            "nature": info["nature"],
            "core_rule": info["core_rule"],
            "tier1_gain_pct": info["tier1_gain_pct"],
        }
    info = ARCHETYPE_GROUPS["CORE_PRODUCTION"]
    return {
        "group_key": "CORE_PRODUCTION",
        "name": info["code"] + " (mặc định theo chuẩn doanh nghiệp niêm yết)",
        "nature": info["nature"],
        "core_rule": info["core_rule"],
        "tier1_gain_pct": info["tier1_gain_pct"],
    }


# ----------------------------------------------------------------------------------------------
# 12b. Từ Điển Đặc Thù Ngành & Pháp Y BCTC (Sector Forensic Guide)
# ----------------------------------------------------------------------------------------------
SECTOR_FORENSIC_GUIDE = {
    "VIC": {
        "sector": "Bất động sản & Đa ngành (Hệ sinh thái Vin)",
        "key_metrics": ["Giao dịch cho vay/bảo lãnh nội bộ VinFast", "Cơ cấu nợ vay & Trái phiếu quốc tế", "Dòng tiền CFO"],
        "accounting_red_flags": [
            "Khoản phải thu và cho vay các bên liên quan chiếm tỷ trọng lớn trong tổng tài sản.",
            "Dòng tiền thuần từ hoạt động kinh doanh (CFO) âm kéo dài, phụ thuộc tài trợ vốn từ nợ vay mới.",
            "Doanh thu tài chính đột biến từ việc tái cấu trúc nội bộ hoặc bán buôn dự án.",
        ],
        "trading_caveats": "Là trụ điều tiết phái sinh và chỉ số VN30; không định giá bằng P/E thông thường; cần theo dõi sát biến động VFS trên sàn quốc tế.",
    },
    "VHM": {
        "sector": "Bất động sản Dân cư",
        "key_metrics": ["Doanh số bán hàng chưa ghi nhận (Unbilled Bookings)", "Tiến độ bàn giao đại đô thị", "Bán buôn lô lớn (Bulk sales)"],
        "accounting_red_flags": [
            "Dòng tiền bị chiếm dụng qua việc cho vay các công ty thành viên trong tập đoàn.",
            "Điểm rơi doanh thu phụ thuộc vào các thương vụ bán buôn lô lớn cho đối tác ngoại.",
        ],
        "trading_caveats": "Thanh khoản lớn nhưng chịu áp lực bán ròng khối ngoại kéo dài; nhạy cảm với pháp lý dự án và room tín dụng BĐS.",
    },
    "VRE": {
        "sector": "Bất động sản Bán lẻ & TTTM",
        "key_metrics": ["Tỷ lệ lấp đầy (Occupancy Rate)", "Giá thuê bình quân/m2", "Tiến độ mở mới Vincom Mega Mall"],
        "accounting_red_flags": [
            "Các khoản cho vay hoặc đặt cọc liên quan đến các dự án nội bộ hệ sinh thái.",
        ],
        "trading_caveats": "Dòng tiền kinh doanh từ cho thuê TTTM ổn định nhất họ Vin; theo dõi cơ cấu cổ đông mới sau khi Vingroup thoái vốn.",
    },
    "SSI": {
        "sector": "Chứng khoán & Dịch vụ Tài chính",
        "key_metrics": ["Danh mục tự doanh FVTPL/AFS", "Dư nợ cho vay margin", "Thị phần môi giới HOSE", "Tăng vốn điều lệ"],
        "accounting_red_flags": [
            "Biến động lãi/lỗ đánh giá lại danh mục FVTPL theo quý (nhạy cảm cao với điểm số VN-Index).",
            "Đòn bẩy tài chính cao từ các khoản vay ngắn hạn ngân hàng tài trợ cho mảng tự doanh và margin.",
        ],
        "trading_caveats": "Đầu ngành chứng khoán; vận động đồng pha với thanh khoản thị trường chung; game tăng vốn thường kéo giá trước ngày chốt quyền.",
    },
    "VIX": {
        "sector": "Chứng khoán Đầu cơ Hệ sinh thái",
        "key_metrics": ["Danh mục cổ phiếu niêm yết trong FVTPL (GEX, EIB, VSC...)", "Lãi chốt lời tự doanh", "Dư nợ margin"],
        "accounting_red_flags": [
            "Lợi nhuận phụ thuộc gần như 100% vào việc kéo giá cổ phiếu tự doanh để chốt NAV quý.",
            "Tập trung rủi ro cao vào một vài mã cổ phiếu trong cùng hệ sinh thái.",
        ],
        "trading_caveats": "Beta cực lớn (trần/sàn nhanh); bỏ qua P/E tĩnh; đánh hoàn toàn theo dòng tiền và các nhịp rũ bỏ T+2,5.",
    },
    "HPG": {
        "sector": "Sản xuất Thép & Công nghiệp nặng",
        "key_metrics": ["Spread giá HRC/Thép xây dựng vs Quặng sắt & Than mỡ", "Tiến độ Dung Quất 2", "Thị phần thép xây dựng (>38%)"],
        "accounting_red_flags": [
            "Trích lập dự phòng giảm giá hàng tồn kho lớn khi giá thép thế giới giảm mạnh.",
            "Chi phí xây dựng dở dang tại Dung Quất 2 và áp lực chi phí lãi vay khi đưa dự án vào vận hành.",
        ],
        "trading_caveats": "Cổ phiếu quốc dân, thanh khoản khổng lồ; mua khi ngành thép ở đáy chu kỳ hoặc P/B chạm vùng đáy lịch sử 1,0–1,2x.",
    },
    "OIL": {
        "sector": "Phân phối & Bán lẻ Xăng dầu",
        "key_metrics": ["Thị phần bán lẻ xăng dầu (~20-22%)", "Chiết khấu hoa hồng phân phối", "Quỹ bình ổn giá (BOG)"],
        "accounting_red_flags": [
            "Trích lập dự phòng giảm giá hàng tồn kho xăng dầu khi giá dầu thế giới rơi sốc trong chu kỳ điều hành.",
            "Biên lợi nhuận gộp rất mỏng (thường 2–4%), nhạy cảm với cơ chế điều hành giá của Nhà nước.",
        ],
        "trading_caveats": "Sàn UPCoM biên độ 15%; KHÔNG phải công ty khai thác dầu thô; hay có nến râu trên dài khi mở gap sáng theo tin tức giá dầu thế giới.",
    },
    "CTD": {
        "sector": "Xây dựng Dân dụng & Công nghiệp",
        "key_metrics": ["Giá trị Backlog ký mới", "Khoản phải thu khách hàng", "Biên lợi nhuận gộp (2–4%)"],
        "accounting_red_flags": [
            "Trích lập dự phòng nợ xấu phải thu khó đòi từ các chủ đầu tư BĐS dân dụng gặp khó khăn thanh khoản.",
            "Dòng tiền kinh doanh (CFO) âm do bị chủ đầu tư chiếm dụng vốn.",
        ],
        "trading_caveats": "Chiến lược chuyển dịch sang nhà xưởng công nghiệp (FDI: Lego, Foxconn...) tạo bước ngoặt; mua gom tại nền cạn cung khi có tin trúng thầu dự án lớn.",
    },
    "FPT": {
        "sector": "Công nghệ Thông tin & Xuất khẩu Phần mềm",
        "key_metrics": ["Doanh thu ký mới Global IT Services", "Tỷ giá JPY/VND & USD/VND", "Quy mô học sinh/sinh viên FPT Edu"],
        "accounting_red_flags": [
            "Tác động tỷ giá JPY suy yếu làm giảm biên lợi nhuận quy đổi mảng thị trường Nhật Bản (>35% doanh thu IT).",
            "Chi phí nhân sự chất lượng cao và R&D AI/Bán dẫn tăng nhanh.",
        ],
        "trading_caveats": "Tăng trưởng bền vững 15–20%/năm; cổ phiếu kênh trên; chỉnh sâu là cơ hội gom của khối ngoại và tổ chức lớn.",
    },
    "BANK": {
        "sector": "Ngân hàng Thương mại",
        "key_metrics": ["Biên lãi thuần (NIM)", "Tỷ lệ nợ xấu NPL (Nhóm 3-5) & Nợ nhóm 2", "Tỷ lệ bao phủ nợ xấu (LLR)", "Tỷ lệ CASA"],
        "accounting_red_flags": [
            "Nợ nhóm 2 tăng vọt báo hiệu rủi ro nợ xấu nhảy nhóm trong tương lai.",
            "Áp lực trích lập dự phòng rủi ro tín dụng bào mòn lợi nhuận trước thuế.",
            "Mức độ phơi nhiễm dư nợ tín dụng và trái phiếu đối với các chủ đầu tư BĐS rủi ro cao.",
        ],
        "trading_caveats": "Vua thanh khoản; chú ý lịch GDKHQ chia cổ tức cổ phiếu / tăng vốn theo quy tắc 'Né trước chốt – Bắt sau chia'.",
    },
}


def get_sector_forensic_guide(symbol: str) -> Optional[dict]:
    """Lấy từ điển pháp y tài chính & đặc thù kế toán/vận hành theo mã/ngành."""
    sym = (symbol or "").upper().strip()
    if sym in SECTOR_FORENSIC_GUIDE:
        return SECTOR_FORENSIC_GUIDE[sym]
    if sym in ARCHETYPE_GROUPS["BANK_LIQUIDITY_KING"]["symbols"] or sym.endswith("BANK"):
        g = dict(SECTOR_FORENSIC_GUIDE["BANK"])
        g["sector"] = f"Ngân hàng Thương mại ({sym})"
        return g
    return None


# ----------------------------------------------------------------------------------------------
# 12c. Bộ Lọc Phân Biệt Thực Thể (Entity Disambiguation)
# ----------------------------------------------------------------------------------------------
ENTITY_DISAMBIGUATION = {
    "OIL": {
        "stock_entity": "Tổng công ty Dầu Việt Nam - CTCP (PVOIL, UPCoM: OIL)",
        "business_nature": "Phân phối & Bán lẻ xăng dầu nội địa (chiếm ~20% thị phần sau Petrolimex).",
        "common_confusion": "Nhầm lẫn với Giá Dầu thô Thế giới (Brent Crude / WTI Crude Oil).",
        "disambiguation_rule": (
            "OIL KHÔNG PHẢI là giá dầu thô thế giới và KHÔNG trực tiếp khai thác mỏ dầu. "
            "Biến động lợi nhuận phụ thuộc vào chiết khấu bán lẻ xăng dầu, cơ chế điều hành giá 7 ngày của Liên Bộ và Quỹ BOG. "
            "Tránh mua đuổi theo đà tăng giá dầu thế giới vào buổi sáng vì hay bị xả cụt đầu."
        ),
    },
    "VIX": {
        "stock_entity": "CTCP Chứng khoán VIX (HOSE: VIX)",
        "business_nature": "Công ty Chứng khoán tại Việt Nam, thuộc hệ sinh thái Gelex/Tuấn Mượt, mảng cốt lõi là Tự doanh FVTPL và Cho vay Margin.",
        "common_confusion": "Nhầm lẫn với Chỉ số Biến động CBOE VIX (S&P 500 Volatility Index của Mỹ - Thước đo sợ hãi).",
        "disambiguation_rule": (
            "VIX KHÔNG PHẢI là chỉ số đo lường tâm lý phố Wall. "
            "VIX là cổ phiếu chứng khoán đầu cơ High-Beta tại Việt Nam. Giá biến động theo dòng tiền tự doanh, "
            "cổ phiếu trong danh mục FVTPL (GEX, EIB...) và thanh khoản sàn HOSE."
        ),
    },
    "GAS": {
        "stock_entity": "Tổng công ty Khí Việt Nam - CTCP (PV GAS, HOSE: GAS)",
        "business_nature": "Thu gom, vận chuyển, chế biến và phân phối khí tự nhiên khô, LPG và nhập khẩu LNG.",
        "common_confusion": "Nhầm lẫn với Giá Khí đốt Tự nhiên Thế giới (Henry Hub Natural Gas).",
        "disambiguation_rule": (
            "GAS bán khí theo hợp đồng dài hạn có cơ chế giá neo theo dầu FO/Brent, không biến động theo biểu đồ giá Henry Hub tương lai."
        ),
    },
    "HPG": {
        "stock_entity": "CTCP Tập đoàn Hòa Phát (HOSE: HPG)",
        "business_nature": "Nhà sản xuất thép tích hợp quy mô lớn nhất Đông Nam Á.",
        "common_confusion": "Nhầm lẫn với công ty thương mại thuần túy hoặc phụ thuộc 100% vào giá quặng sắt.",
        "disambiguation_rule": (
            "HPG sở hữu chuỗi giá trị từ quặng, than mỡ qua lò cao BOF đến thép xây dựng và HRC. "
            "Hưởng lợi từ biên chênh lệch giá thép trừ chi phí nguyên liệu và bảo hộ thương mại chống bán phá giá."
        ),
    },
    "PLX": {
        "stock_entity": "Tập đoàn Xăng dầu Việt Nam (Petrolimex, HOSE: PLX)",
        "business_nature": "Đầu mối phân phối bán lẻ xăng dầu chiếm ~50% thị phần Việt Nam.",
        "common_confusion": "Nhầm lẫn với công ty thăm dò và khai thác mỏ dầu thô.",
        "disambiguation_rule": (
            "PLX là hạ nguồn bán lẻ, ăn biên lợi nhuận định mức trên mỗi lít xăng dầu, không khai thác dầu."
        ),
    },
    "PVD": {
        "stock_entity": "Tổng công ty CP Khoan và Dịch vụ Khoan Dầu khí (PV Drilling, HOSE: PVD)",
        "business_nature": "Cung cấp giàn khoan biển tự nâng (Jack-up) và dịch vụ kỹ thuật giếng khoan.",
        "common_confusion": "Nhầm lẫn là công ty bán dầu thô theo thùng.",
        "disambiguation_rule": (
            "PVD kinh doanh dịch vụ giàn khoan, phụ thuộc vào giá thuê giàn (day rate) và hiệu suất sử dụng giàn (utilization rate), "
            "không khai thác và bán dầu trực tiếp."
        ),
    },
    "PVS": {
        "stock_entity": "Tổng công ty CP Dịch vụ Kỹ thuật Dầu khí Việt Nam (PTSC, HOSE: PVS)",
        "business_nature": "Tổng thầu EPCIC cơ khí dầu khí ngoài khơi, hạ tầng điện gió ngoài khơi (offshore wind) và kho nổi FSO/FPSO.",
        "common_confusion": "Nhầm lẫn là công ty bán dầu thô thùng.",
        "disambiguation_rule": (
            "PVS là tổng thầu cơ khí và xây lắp công trình biển, hưởng lợi từ các đại dự án Lô B Ô Môn và các hợp đồng chế tạo "
            "chân đế điện gió xuất khẩu quốc tế."
        ),
    },
    "BSR": {
        "stock_entity": "CTCP Lọc hóa dầu Bình Sơn (Nhà máy Lọc dầu Dung Quất, UPCoM/HOSE: BSR)",
        "business_nature": "Lọc hóa dầu, chế biến dầu thô thành xăng, diesel, Jet A1, hạt nhựa PP.",
        "common_confusion": "Nhầm lẫn là công ty khai thác dầu thô hoặc bán lẻ cây xăng.",
        "disambiguation_rule": (
            "BSR phụ thuộc vào Crack Spread (chênh lệch giá thành phẩm lọc như Diesel/Mogas95 trừ đi giá dầu thô nguyên liệu), "
            "không ăn theo giá dầu thô đơn thuần."
        ),
    },
}


def get_entity_disambiguation(symbol: str) -> Optional[dict]:
    """Lấy quy tắc phân biệt thực thể để triệt tiêu ảo giác nhầm lẫn mã Việt Nam với chỉ số/hàng hóa thế giới."""
    sym = (symbol or "").upper().strip()
    return ENTITY_DISAMBIGUATION.get(sym)


# ----------------------------------------------------------------------------------------------
# 12d. Phân Tích Phiên ATC & Vi Cấu Trúc Cuối Phiên
# ----------------------------------------------------------------------------------------------
def _analyze_atc(df: pd.DataFrame, quote_snapshot: Optional[dict] = None) -> dict:
    """
    Phân tích vi cấu trúc phiên ATC và nến cuối phiên:
    - Close Location Value (CLV = (Close - Low) / (High - Low))
    - Râu nến trên / dưới, nhận diện kéo trộm ATC hoặc đè đạp ATC
    - Cảnh báo tuần đáo hạn phái sinh VN30F (Thứ Năm tuần thứ 3 hàng tháng)
    """
    if df is None or df.empty:
        return {
            "clv": 0.5,
            "clv_pct": 50.0,
            "upper_wick": 0.0,
            "lower_wick": 0.0,
            "session_close_position": "Không có dữ liệu nến",
            "atc_pattern": "Giao dịch bình thường",
            "derivative_week_warning": False,
            "tactical_implication": "Chưa có dữ liệu phiên để đánh giá ATC.",
        }

    c = float(df["Close"].iloc[-1])
    h = float(df["High"].iloc[-1])
    l = float(df["Low"].iloc[-1])
    o = float(df["Open"].iloc[-1])
    span = h - l

    if span <= 1e-9:
        clv = 0.5
    else:
        clv = (c - l) / span
    clv = max(0.0, min(1.0, clv))

    upper_wick = max(0.0, h - max(o, c))
    lower_wick = max(0.0, min(o, c) - l)
    body = abs(c - o)

    # Vị trí đóng cửa
    if clv >= 0.80:
        close_pos = "Đóng cửa sát đỉnh ngày (Lực mua áp đảo cuối phiên / Kéo dứt khoát)"
    elif clv <= 0.20:
        close_pos = "Đóng cửa sát đáy ngày (Áp lực xả đè giá cuối phiên / Nến đóng thấp nhất)"
    elif clv >= 0.60:
        close_pos = "Đóng cửa nửa trên biên độ (Phe mua chiếm ưu thế nhẹ)"
    elif clv <= 0.40:
        close_pos = "Đóng cửa nửa dưới biên độ (Phe bán chiếm ưu thế nhẹ)"
    else:
        close_pos = "Cân bằng ở giữa biên độ ngày"

    # Hình thái ATC
    if upper_wick >= 1.5 * body and upper_wick >= 0.35 * span and clv <= 0.40:
        atc_pattern = "Bị đè bán ATC / Nến cụt đầu (Áp lực chốt lời vùng giá cao, cẩn trọng bẫy Bull-trap)"
        implication = "Áp lực cung đè giá cuối phiên lớn. Tránh mua đuổi sáng hôm sau vì dễ có bẫy mở gap giảm trả điểm."
    elif lower_wick >= 1.5 * body and lower_wick >= 0.35 * span and clv >= 0.60:
        atc_pattern = "Rút chân mạnh phiên ATC (Lực cầu hấp thụ vùng giá thấp cuối phiên)"
        implication = "Lực cầu gia tăng hấp thụ lệnh bán ở vùng thấp trước giờ đóng cửa. Tín hiệu hỗ trợ tích cực cho nhịp T+."
    elif clv >= 0.85 and span > 0 and body > 0.4 * span:
        atc_pattern = "Kéo dứt khoát ATC / Đóng nến Marubozu cao nhất phiên"
        implication = "Phe mua kiểm soát hoàn toàn phiên giao dịch tới phút chót. Khả năng cao mở gap xanh đầu phiên sau."
    elif clv <= 0.15 and span > 0 and body > 0.4 * span:
        atc_pattern = "Đè đạp ATC quyết liệt / Đóng nến thấp nhất phiên"
        implication = "Lực bán tháo ATC áp đảo hoàn toàn. Cần chuẩn bị kịch bản mở gap giảm đầu phiên kế tiếp."
    else:
        atc_pattern = "Giao dịch bình thường"
        implication = "Cung cầu cân bằng trong phiên khớp lệnh định kỳ đóng cửa."

    # Kiểm tra tuần đáo hạn phái sinh (Thứ Năm tuần thứ 3 của tháng)
    last_dt = df.index[-1]
    is_deriv_week = False
    try:
        cal = calendar.monthcalendar(last_dt.year, last_dt.month)
        thursdays = [w[calendar.THURSDAY] for w in cal if w[calendar.THURSDAY] != 0]
        if len(thursdays) >= 3:
            third_thurs_day = thursdays[2]
            third_thurs_date = pd.Timestamp(last_dt.year, last_dt.month, third_thurs_day).date()
            monday_date = third_thurs_date - timedelta(days=3)
            friday_date = third_thurs_date + timedelta(days=1)
            is_deriv_week = bool(monday_date <= last_dt.date() <= friday_date)
    except Exception:
        is_deriv_week = False

    if is_deriv_week:
        implication += " [LƯU Ý: Tuần đáo hạn phái sinh VN30F — hạn chế giao dịch theo nến ATC do dễ bị méo mó chỉ số]."

    return {
        "clv": round(clv, 2),
        "clv_pct": round(clv * 100, 1),
        "upper_wick": round(upper_wick, 2),
        "lower_wick": round(lower_wick, 2),
        "session_close_position": close_pos,
        "atc_pattern": atc_pattern,
        "derivative_week_warning": is_deriv_week,
        "tactical_implication": implication,
    }


# ----------------------------------------------------------------------------------------------
# 12e. Ma Trận 6 Giả Thuyết Biến Động Giá (Causal Hypotheses Matrix)
# ----------------------------------------------------------------------------------------------
def _evaluate_causal_hypotheses(profile: dict) -> list[dict]:
    """
    Ma trận 6 Giả thuyết Biến động Giá (Causal Hypotheses Matrix) theo chuẩn CFA:
    - H1: Gom hàng / Tích lũy (Tạo lập gom ngầm vùng hỗ trợ, cạn cung No Supply)
    - H2: Phân phối / Xả ngầm (Kéo trụ xả midcap, Upthrust, râu nến trên dài)
    - H3: Quỹ tái cơ cấu (Review định kỳ ETF, khớp lệnh đột biến ATC thứ 6)
    - H4: Luân chuyển ngành (Dòng tiền xoay vòng tự nhiên giữa các nhóm ngành)
    - H5: Tái định giá (KQKD quý vượt kỳ vọng, lợi nhuận ròng tăng trưởng > 20%)
    - H6: Bán tháo kỹ thuật / Margin (Call margin chéo, lực bán MP áp đảo)
    
    Đầu ra chuẩn hóa xác suất: tổng xác suất của 6 giả thuyết = 1.0 (100%).
    """
    trend = profile.get("trend") or {}
    stage = trend.get("stage")
    flow = profile.get("flow") or {}
    rs = profile.get("relative_strength") or {}
    atc = profile.get("atc_analysis") or {}
    tactical = profile.get("tactical_6step") or {}

    dist_days = flow.get("distribution_days_25") or 0
    accu_days = flow.get("accumulation_days_25") or 0
    vol_ratio = flow.get("up_down_volume_ratio_20d") or 1.0
    beta = rs.get("beta_120d") or 1.0
    clv = atc.get("clv") or 0.5
    is_spring = "Spring" in str(tactical.get("spring_analysis", ""))

    # Chấm điểm thô (raw scores)
    s1 = 15.0  # H1 Gom hàng
    if stage == 1:
        s1 += 30.0
    elif stage == 2:
        s1 += 10.0
    if accu_days > dist_days:
        s1 += 15.0
    if vol_ratio and vol_ratio > 1.2:
        s1 += 10.0
    if is_spring:
        s1 += 20.0

    s2 = 10.0  # H2 Phân phối
    if stage == 3:
        s2 += 35.0
    if dist_days >= 4:
        s2 += 20.0
    if dist_days >= 6:
        s2 += 15.0
    if clv < 0.35:
        s2 += 10.0

    s3 = 10.0  # H3 Quỹ tái cơ cấu
    if atc.get("derivative_week_warning"):
        s3 += 15.0
    if tactical.get("foreign_cycle_analysis") and "BÁN RÒNG" in str(tactical.get("foreign_cycle_analysis")):
        s3 += 15.0
    elif tactical.get("foreign_cycle_analysis") and "MUA RÒNG" in str(tactical.get("foreign_cycle_analysis")):
        s3 += 15.0

    s4 = 15.0  # H4 Luân chuyển ngành
    if stage == 2:
        s4 += 15.0
    if rs.get("excess_20d") and rs.get("excess_20d") > 0:
        s4 += 15.0

    s5 = 15.0  # H5 Tái định giá
    if stage in (1, 2):
        s5 += 15.0
    if rs.get("rs_line_vs_ma50") == "nằm trên":
        s5 += 15.0

    s6 = 5.0   # H6 Bán tháo kỹ thuật / Margin
    if stage == 4:
        s6 += 40.0
    if dist_days >= 6:
        s6 += 15.0
    if beta and beta > 1.3:
        s6 += 10.0
    if clv <= 0.15:
        s6 += 15.0

    raw_scores = [s1, s2, s3, s4, s5, s6]
    total = sum(raw_scores)
    raw_probs = [round(s / total, 2) for s in raw_scores]
    diff = round(1.0 - sum(raw_probs), 2)
    max_idx = int(np.argmax(raw_probs))
    raw_probs[max_idx] = round(raw_probs[max_idx] + diff, 2)

    hypotheses_defs = [
        ("H1", "Gom hàng/Tích lũy", "Tạo lập gom ngầm vùng hỗ trợ, cạn cung", "Vol cạn kiệt, spread hẹp, xuất hiện nến Test cung/Spring"),
        ("H2", "Phân phối/Xả ngầm", "Kéo trụ xả midcap, phân phối vùng kháng cự", "Upthrust, râu nến trên dài, phân kỳ âm RSI/MACD, nhiều ngày phân phối"),
        ("H3", "Quỹ tái cơ cấu", "Review định kỳ ETF hoặc cơ cấu danh mục khối ngoại", "Khớp lệnh đột biến phiên ATC thứ 6, tỷ trọng giao dịch ngoại > 20%"),
        ("H4", "Luân chuyển ngành", "Dòng tiền xoay vòng tự nhiên giữa các ngành dẫn dắt", "Toàn ngành cùng bứt phá, thanh khoản lan tỏa đồng thuận"),
        ("H5", "Tái định giá", "Định giá lại nội tại, điểm rơi KQKD quý vượt kỳ vọng", "Tăng trưởng doanh thu/lợi nhuận > 20%, P/E và P/B chiết khấu sâu"),
        ("H6", "Bán tháo kỹ thuật/Margin", "Call margin chéo, hoảng loạn cắt lỗ kỹ thuật", "Lực bán MP áp đảo, mở gap rơi, sàn hàng loạt mất thanh khoản"),
    ]

    result = []
    for (hid, name, driver, verifiable_by), prob in zip(hypotheses_defs, raw_probs):
        score_pct = int(round(prob * 100))
        verdict = (
            "Ủng hộ mạnh" if prob >= 0.35
            else "Khả năng cao" if prob >= 0.25
            else "Trung bình" if prob >= 0.15
            else "Ít khả năng"
        )
        result.append({
            "id": hid,
            "name": name,
            "prob": prob,
            "driver": driver,
            "verifiable_by": verifiable_by,
            "likelihood_score": score_pct,
            "verdict": verdict,
        })
    return result


# ----------------------------------------------------------------------------------------------
# 12f. Khung Phân Tích 4 Lớp Thị Trường Chung (Market Layers)
# ----------------------------------------------------------------------------------------------
def _build_market_layers(profile: dict, symbol: str = "") -> dict:
    """
    Khung phân tích Top-down 4 Tầng Thị Trường Chung (Market Layers):
    - Tầng 1: Vĩ mô & Lãi suất / Tỷ giá
    - Tầng 2: Thị trường chung VN-Index / VN30
    - Tầng 3: Ngành & Dòng tiền Luân chuyển
    - Tầng 4: Cổ phiếu & Vi cấu trúc Bảng điện
    """
    trend = profile.get("trend") or {}
    tactical = profile.get("tactical_6step") or {}
    flow = profile.get("flow") or {}
    rs = profile.get("relative_strength") or {}
    bp = profile.get("baseline_plan") or {}
    arch = tactical.get("archetype") or classify_stock_archetype(symbol)
    stops = bp.get("exit_stops") or {}
    price_stop_val = stops.get("price_stop", {}).get("price", bp.get("stop_loss", 0.0))

    layer_1 = {
        "name": "Lớp 1: Vĩ mô & Lãi suất / Tỷ giá",
        "environment": "Môi trường tiền tệ linh hoạt, duy trì lãi suất thấp hỗ trợ tăng trưởng",
        "key_metrics": [
            "Lãi suất tái cấp vốn SBV: 4.5% (Môi trường tiền tệ hỗ trợ dòng vốn đầu tư)",
            "Tỷ giá USD/VND: Biên độ điều hành ổn định, theo dõi áp lực DXY",
            "Dầu Brent & Vàng thế giới: Theo dõi rủi ro địa chính trị và lạm phát nhập khẩu",
        ],
        "implication": "Thanh khoản hệ thống ngân hàng dồi dào, thuận lợi cho kênh đầu tư chứng khoán.",
    }

    layer_2 = {
        "name": "Lớp 2: Thị trường chung VN-Index / VN30",
        "stage": f"Giai đoạn {trend.get('stage', 2)} ({trend.get('label', 'Tích lũy/Tăng')})",
        "distribution_pressure": f"{flow.get('distribution_days_25', 0)} ngày phân phối / 25 phiên gần nhất",
        "recommended_equity_allocation": bp.get("sizing_rule", "50%–70% NAV"),
        "breadth_verdict": "Thị trường phân hóa rõ nét, dòng tiền chọn lọc cổ phiếu có nền giá và câu chuyện riêng.",
    }

    s_guide = get_sector_forensic_guide(symbol)
    layer_3 = {
        "name": "Lớp 3: Ngành & Dòng tiền Luân chuyển",
        "sector_name": s_guide.get("sector", "Doanh nghiệp niêm yết") if s_guide else "Toàn thị trường",
        "flow_status": "Dòng tiền xoay vòng giữa các nhóm trụ và cổ phiếu midcap cơ bản",
        "relative_strength": rs.get("verdict", "Vận động đồng pha với chỉ số chung"),
    }

    layer_4 = {
        "name": "Lớp 4: Cổ phiếu & Vi cấu trúc Bảng điện",
        "symbol": (symbol or "MÃ").upper(),
        "archetype": arch.get("name", "Cổ phiếu niêm yết"),
        "tape_signal": tactical.get("spring_analysis", "Cung cầu cân bằng tại vùng hỗ trợ"),
        "exit_stops_triad": f"Price-Stop: {price_stop_val:.2f} | Thesis-Stop: Theo dõi gãy MA50 | Time-Stop: 10–15 phiên",
    }

    return {
        "layer_1_macro": layer_1,
        "layer_2_market": layer_2,
        "layer_3_sector": layer_3,
        "layer_4_stock": layer_4,
    }



def _tactical_playbook_6step(
    df: pd.DataFrame,
    levels: dict,
    baseline_plan: dict,
    atr: float,
    symbol: str = "",
    beta: Optional[float] = None,
    snapshot: Optional[dict] = None,
) -> dict:
    """
    Tính toán định lượng cho Bộ Quy Tắc Thực Chiến 6 Bước (T+2,5 & Tape Reading):
    1. Định danh bản chất cổ phiếu trên bàn cờ Tạo lập (5 nhóm).
    2. Tape Reading: Bẫy neo giá xả ngầm, Nến cụt đầu, Rũ giả (Spring) vs Gãy thật, Cạn cung (No Supply), Tường đỡ sổ lệnh.
    3. Đồng hồ sinh học T+2,5 & Theo dõi phiên hàng nổ thanh khoản về tài khoản.
    4. Bộ lọc sự kiện Quyền (GDKHQ) & Điểm rơi BCTC Quý.
    5. Quản trị vị thế linh hoạt & Công thức chốt lời 3 nhịp + Chặn lãi trượt (Trailing Stop 1,5%–2%).
    6. Bảng Checklist 5 phút trước khi bấm lệnh.
    """
    arch = classify_stock_archetype(symbol, beta)
    c = float(df["Close"].iloc[-1])
    h_last = float(df["High"].iloc[-1])
    l_last = float(df["Low"].iloc[-1])
    o_last = float(df["Open"].iloc[-1])
    v_last = float(df["Volume"].iloc[-1])
    vma20 = float(df["VolMA20"].iloc[-1]) if "VolMA20" in df.columns and df["VolMA20"].iloc[-1] else v_last

    # --- Bước 2: Đọc Bảng điện, Sổ lệnh & Dòng tiền ẩn (Tape Reading)
    tape_signals = []
    chg_pct = (c / float(df["Close"].iloc[-2]) - 1) * 100 if len(df) >= 2 else 0.0
    vol_ratio = v_last / vma20 if vma20 > 0 else 1.0

    # 2a. Bẫy "Neo giá xả ngầm" (Churning / Distribution at High Volume)
    body = abs(c - o_last)
    upper_wick = h_last - max(c, o_last)
    lower_wick = min(c, o_last) - l_last
    if vol_ratio >= 1.5 and abs(chg_pct) <= 0.85:
        tape_signals.append(
            f"⚠️ CẢNH BÁO PHÂN KỲ KHỐI LƯỢNG (Churning): Khối lượng phiên cuối nổ cao ({vol_ratio:.1f}× TB20) "
            f"nhưng giá chỉ biến động {chg_pct:+.2f}% → dấu hiệu phân kỳ khối lượng/biên độ giá (tín hiệu phân phối tiềm ẩn hoặc giao dịch trao tay)."
        )
    if upper_wick > max(1.2 * body, 0.55 * atr):
        tape_signals.append(
            f"⚠️ NẾN CỤT ĐẦU (Upper Wick Rejection): Râu nến trên dài ({upper_wick:.2f}), giá bị đè lùi từ đỉnh ngày {h_last:.2f} "
            f"về {c:.2f} → tuyệt đối không mua đuổi giá xanh đầu phiên."
        )

    # 2b. Tín hiệu "Tiết cung / Cạn cung" (No Supply Test)
    if vol_ratio <= 0.68 and abs(chg_pct) <= 1.2:
        tape_signals.append(
            f"✅ TÍN HIỆU TIẾT CUNG (No Supply): Thanh khoản co hẹp chỉ bằng {vol_ratio:.2f}× TB20 khi giá giữ nền ({chg_pct:+.2f}%) "
            f"→ áp lực bán cạn kiệt, thuận lợi để mua gom tại nền."
        )

    # 2c. Phân biệt "Rút ván rũ hàng (Spring / Wash-out)" vs "Gãy thật"
    sup_list = levels.get("supports", [])
    s1 = sup_list[0]["price"] if sup_list else (c - 1.5 * atr)
    spring_note = "Chưa xuất hiện nhịp quét thủng nền (Spring) trong 3 phiên gần nhất."
    if len(df) >= 6:
        recent3 = df.tail(3)
        prev10_low = float(df["Low"].iloc[-13:-3].min()) if len(df) >= 13 else s1
        min_low3 = float(recent3["Low"].min())
        dip_pct = (prev10_low - min_low3) / prev10_low * 100 if prev10_low > 0 else 0
        if 0.1 <= dip_pct <= 2.5 and c > prev10_low:
            spring_note = (
                f"✅ PHÁT HIỆN CÚ RŨ GIẢ (Spring / Wash-out): Giá từng nhúng thủng đáy nền {prev10_low:.2f} xuống {min_low3:.2f} "
                f"(lệch nền {dip_pct:.2f}% ≤ 2,5%) kiểm định dưới nền rồi phục hồi đóng cửa giữ vững nền tại {c:.2f}."
            )
            tape_signals.append(spring_note)
        elif dip_pct > 2.5 and c < prev10_low:
            spring_note = (
                f"🚨 CẢNH BÁO GÃY NỀN THẬT (Breakdown): Giá xuyên thủng đáy {prev10_low:.2f} quá 2,5% (xuống {min_low3:.2f}) "
                f"và chưa lấy lại được nền → không bắt đáy sớm."
            )
            tape_signals.append(spring_note)
        elif lower_wick > max(1.2 * body, 0.55 * atr) and l_last <= s1 * 1.015:
            spring_note = (
                f"✅ NẾN RÚT CHÂN HẤP THỤ TẠI HỖ TRỢ: Giá nhúng về {l_last:.2f} sát hỗ trợ {s1:.2f} rồi rút chân lên {c:.2f} "
                f"(râu dưới {lower_wick:.2f}) → có lực cầu đỡ giá."
            )
            tape_signals.append(spring_note)

    # 2d. Đọc Độ sâu Sổ lệnh (Order Book Wall) & Chu kỳ Khối ngoại Bất đối xứng
    order_book_note = "Chưa có dữ liệu sổ lệnh 3 bước giá trực tiếp."
    foreign_cycle_note = "Chưa có chuỗi khối ngoại nhiều phiên để tính chu kỳ bất đối xứng."
    event_flags = []
    if snapshot:
        ba = snapshot.get("bid_ask") or {}
        bids = [v for _, v in (ba.get("bid") or []) if v]
        asks = [v for _, v in (ba.get("ask") or []) if v]
        sum_bid, sum_ask = sum(bids), sum(asks)
        if sum_bid > 0 and sum_ask > 0:
            ba_ratio = sum_bid / sum_ask
            if ba_ratio >= 1.6:
                order_book_note = (
                    f"✅ ĐỘ SÂU SỔ LỆNH TỨC THỜI (ƯU THẾ BÊN MUA): Tổng khối lượng Kê Mua 3 bước giá ({sum_bid:,.0f} cp) gấp {ba_ratio:.1f} lần "
                    f"bên Bán ({sum_ask:,.0f} cp); áp lực cầu chờ mua chiếm ưu thế tại thời điểm ghi nhận."
                )
            elif ba_ratio <= 0.6:
                order_book_note = (
                    f"⚠️ ĐỘ SÂU SỔ LỆNH TỨC THỜI (ƯU THẾ BÊN BÁN): Tổng khối lượng Kê Bán ({sum_ask:,.0f} cp) gấp {1/ba_ratio:.1f} lần "
                    f"bên Mua ({sum_bid:,.0f} cp); áp lực cung chờ bán chiếm ưu thế tại các bước giá phía trên."
                )
            else:
                order_book_note = f"Độ sâu sổ lệnh tức thời cân bằng: Kê mua 3 bước {sum_bid:,.0f} cp / Kê bán {sum_ask:,.0f} cp (tỷ lệ {ba_ratio:.2f}×)."
        fh = snapshot.get("foreign_history")
        if fh and fh.get("recent"):
            net1 = fh.get("net_1d_bn") or 0
            net5 = fh.get("net_5d_bn") or 0
            net20 = fh.get("net_20d_bn") or 0
            if net20 > 0 and net1 > 0 >= (net5 - net1):
                foreign_cycle_note = (
                    f"✅ XÁC NHẬN ĐÁY CHU KỲ KHỐI NGOẠI: Sau giai đoạn gom ròng 20 phiên ({net20:+.1f} tỷ) và nhịp chững lại, "
                    f"khối ngoại đã đảo chiều mua ròng dương trở lại ({net1:+.1f} tỷ phiên gần nhất)."
                )
            elif net1 > 0 and net5 > 0:
                foreign_cycle_note = f"✅ KHỐI NGOẠI ĐỒNG THUẬN GOM RÒNG: 1 phiên {net1:+.1f} tỷ | 5 phiên {net5:+.1f} tỷ | 20 phiên {net20:+.1f} tỷ."
            elif net1 < 0 and abs(net1) < abs(net5) / 5 * 0.5:
                foreign_cycle_note = (
                    f"🟡 KHỐI NGOẠI THU HẸP ĐÀ BÁN (Cạn cung ngoại): Lượng bán phiên cuối ({net1:+.1f} tỷ) đã giảm mạnh so với trung bình 5 phiên "
                    f"({net5:+.1f} tỷ) → theo dõi phiên đảo chiều sang mua ròng dương để xác nhận đáy."
                )
            else:
                foreign_cycle_note = f"Chuỗi khối ngoại: 1 phiên {net1:+.1f} tỷ | 5 phiên {net5:+.1f} tỷ | 20 phiên {net20:+.1f} tỷ ({fh.get('streak', '')})."
        elif snapshot.get("foreign_net_bn") is not None:
            fn = snapshot["foreign_net_bn"]
            foreign_cycle_note = f"Khối ngoại phiên gần nhất: {'Mua ròng' if fn >= 0 else 'Bán ròng'} {fn:+.2f} tỷ đồng."
        event_flags = list(snapshot.get("flags") or [])

    # --- Bước 3: Đồng hồ sinh học T+2,5 & Theo dõi Hàng Nổ Thanh Khoản Về Tài Khoản
    t25_events = []
    tail6 = df.tail(6)
    n_tail = len(tail6)
    for idx_pos in range(n_tail):
        row = tail6.iloc[idx_pos]
        dt = tail6.index[idx_pos]
        v_row = float(row["Volume"])
        vma_row = float(row.get("VolMA20") or vma20)
        if vma_row > 0 and v_row >= 1.6 * vma_row:
            bars_ago = (n_tail - 1) - idx_pos
            spike_close = float(row["Close"])
            pnl_now = (c / spike_close - 1) * 100 if spike_close else 0.0
            if bars_ago == 0:
                status_t25 = "Vừa nổ vol hôm nay (T+0) → Hàng sẽ về tài khoản lúc 13h00 chiều phiên T+2 (2 phiên nữa)."
            elif bars_ago == 1:
                status_t25 = (
                    f"⚠️ CẢNH BÁO T+2,5: Hàng nổ vol ({v_row:,.0f} cp) sẽ về tài khoản vào 13h00 CHIỀU MAI! "
                    f"Giá hiện tại đang {'lãi' if pnl_now >= 0 else 'lỗ'} {pnl_now:+.2f}% so với giá đóng cửa phiên nổ ({spike_close:.2f}) "
                    f"→ Chờ qua 13h45 ngày mai kiểm tra lực hấp thụ rồi mới bấm lệnh."
                )
            elif bars_ago == 2:
                status_t25 = (
                    f"🔥 ĐÚNG CHIỀU NAY (13h00–13h45) HÀNG NỔ VOL T+2,5 VỀ TÀI KHOẢN ({v_row:,.0f} cp giá {spike_close:.2f}): "
                    f"Hiện tại đang {'lãi' if pnl_now >= 0 else 'lỗ'} {pnl_now:+.2f}% → "
                    + ("Đã hấp thụ tốt, giữ giá trên nền phiên nổ!" if pnl_now >= -1.5 else "Đang bị áp lực bán chốt/cắt lỗ T+, cẩn trọng!")
                )
            else:
                status_t25 = (
                    f"Đã qua cửa ải T+2,5 ({bars_ago} phiên trước, giá {spike_close:.2f}): "
                    + (f"Hấp thụ thành công, giá hiện cao hơn {pnl_now:+.2f}%." if pnl_now >= 0 else f"Lượng hàng lớn đang bị kẹp ({pnl_now:+.2f}%), tạo vùng cung treo tại {spike_close:.2f}.")
                )
            t25_events.append({
                "date": _fmt_short(dt),
                "bars_ago": bars_ago,
                "volume": int(v_row),
                "vol_ratio": round(v_row / vma_row, 2),
                "spike_close": round(spike_close, 2),
                "pnl_vs_now_pct": round(pnl_now, 2),
                "status": status_t25,
            })

    # --- Bước 4: Bộ lọc Sự kiện Quyền & Điểm rơi BCTC Quý
    cur_month = df.index[-1].month if hasattr(df.index[-1], "month") else datetime.now(VN_TZ).month
    cur_day = df.index[-1].day if hasattr(df.index[-1], "day") else datetime.now(VN_TZ).day
    in_bctc_window = cur_month in (1, 4, 7, 10) and cur_day <= 30
    bctc_season_note = (
        f"Đang trong mùa cao điểm công bố BCTC Quý (tháng {cur_month}, hạn chót ngày 20–30): "
        + ("Với nhóm Sản xuất nội tại thật như mã này, các nhịp đè giá trước ngày ra BCTC hợp nhất thường là cơ hội gom hàng của tổ chức."
           if arch["group_key"] == "CORE_PRODUCTION"
           else "Theo dõi sát rủi ro 'mua tin đồn, bán sự thật' khi ra số liệu chính thức.")
        if in_bctc_window
        else f"Tháng {cur_month}: Ngoài cao điểm BCTC quý; ưu tiên kiểm tra lịch GDKHQ chia cổ tức/phát hành thêm trong 3 ngày tới."
    )

    # --- Bước 5: Công thức Chốt lời 3 Nhịp & Chặn lãi trượt (Trailing Stop)
    entry_mid = (baseline_plan["entry_low"] + baseline_plan["entry_high"]) / 2
    tier1_pct = arch["tier1_gain_pct"]
    tier1_price = max(baseline_plan["target_1"], round(entry_mid * (1 + tier1_pct / 100), 2))
    trail_15 = round(h_last * (1 - 0.015), 2)
    trail_20 = round(h_last * (1 - 0.020), 2)
    near_high_close = (h_last - c) <= 0.25 * (h_last - l_last) if h_last > l_last else True

    profit_taking_3tier = {
        "tier1_sell_30pct": {
            "price": tier1_price,
            "rule": f"Nhịp 1 (Bán 30% – Khóa lợi nhuận cơ bản): Chủ động chốt 30% khi chạm kháng cự / đạt kỳ vọng +{tier1_pct:.1f}% tại ~{tier1_price:.2f}.",
        },
        "tier2_hold_50pct_trailing": {
            "trailing_1_5pct": trail_15,
            "trailing_2_0pct": trail_20,
            "rule": (
                f"Nhịp 2 (Giữ 50% – Cưỡi sóng bằng Trailing Stop): Cài lệnh điều kiện trượt lùi 1,5%–2,0% từ đỉnh cao nhất phiên "
                f"(tương ứng mốc chặn lãi động hiện tại {trail_20:.2f}–{trail_15:.2f} tính từ đỉnh {h_last:.2f})."
            ),
        },
        "tier3_hold_20pct_fomo": {
            "target_2": baseline_plan["target_2"],
            "strong_close": near_high_close and chg_pct > 0,
            "rule": (
                "Nhịp 3 (Giữ 20% cuối – Ăn trọn quán tính FOMO): Nếu kết phiên đóng nến xanh đặc gần đỉnh ngày hoặc dư mua trần, "
                "giữ 20% qua đêm để bán vào nhịp mở Gap hưng phấn lúc 09h15–09h30 sáng hôm sau."
            ),
        },
    }

    # --- Bước 6: Bảng Checklist 5 Phút Trước Khi Bấm Lệnh (Cho người bận rộn ngoài công trường)
    has_tomorrow_t25 = any(e["bars_ago"] == 1 for e in t25_events)
    dist_to_sup_pct = (c / s1 - 1) * 100 if s1 > 0 else 0
    checklist_5m = [
        {
            "step": "1. Kiểm tra Sự kiện Quyền (GDKHQ)",
            "status": "⚠️ CẦN XÁC MINH" if event_flags else "🟢 SẴN SÀNG (Kiểm tra ký hiệu • trên bảng điện)",
            "detail": (
                "Tuyệt đối KHÔNG mua trong 2 phiên (T-1, T-2) trước ngày GDKHQ chia cổ tức cổ phiếu / phát hành thêm "
                "để tránh bị giam vốn 2–3 tháng và chịu 5% thuế TNCN. Áp dụng 'Né trước chốt – Bắt sau chia'."
            ),
        },
        {
            "step": "2. Khung giờ Tác chiến & Vị trí Giá mua",
            "status": "🟢 VÙNG MUA HỢP LỆ" if dist_to_sup_pct <= 3.5 else "🟡 CÁCH XA NỀN (Cấm FOMO Gap Up sáng)",
            "detail": (
                f"Giá hiện tại {c:.2f} cách nền hỗ trợ {s1:.2f} khoảng {dist_to_sup_pct:+.1f}%. "
                "Chỉ bấm nút trong khung Phán quyết 13h45–14h25 chiều; tuyệt đối không mua đuổi giá xanh khung 09h00–10h30 sáng."
            ),
        },
        {
            "step": "3. Dòng tiền Tổ chức / Khối ngoại",
            "status": "🔴 CẢNH BÁO XẢ ẨN" if any("NEO GIÁ XẢ NGẦM" in s for s in tape_signals) else "🟢 THEO DÕI CHU KỲ",
            "detail": f"{foreign_cycle_note} | {order_book_note}",
        },
        {
            "step": "4. Kiểm tra Chu kỳ Hàng nổ Vol T+2,5 về tài khoản",
            "status": "🟡 CHỜ QUA 13H45 NGÀY MAI" if has_tomorrow_t25 else "🟢 KHÔNG VƯỚNG ÁP LỰC XẢ T+2,5 NGÀY MAI",
            "detail": t25_events[-1]["status"] if t25_events else "Không có phiên nổ thanh khoản đột biến (>1,6× TB20) nào sắp về tài khoản.",
        },
        {
            "step": "5. Thiết lập Chốt chặn Tự động (Stop Order & Price Alert)",
            "status": "🟢 BẮT BUỘC CÀI NGAY SAU KHỚP",
            "detail": (
                f"Cài sẵn Price Alert tại hỗ trợ {s1:.2f} và Lệnh điều kiện Stop Order cắt lỗ tại {baseline_plan['stop_loss']:.2f} "
                f"(hoặc Trailing Stop trượt 1,5%–2% tại {trail_20:.2f}–{trail_15:.2f}) để yên tâm làm việc."
            ),
        },
    ]

    return {
        "archetype": arch,
        "tape_signals": tape_signals,
        "spring_analysis": spring_note,
        "order_book_analysis": order_book_note,
        "foreign_cycle_analysis": foreign_cycle_note,
        "t25_events": t25_events,
        "bctc_season_note": bctc_season_note,
        "profit_taking_3tier": profit_taking_3tier,
        "checklist_5m": checklist_5m,
        "intraday_clock": {
            "09h00_10h30": "Khung giờ Bẫy hưng phấn — Đứng ngoài quan sát, tuyệt đối không mua đuổi Gap Up đầu phiên.",
            "13h00_13h45": "Khung giờ Thử lửa hàng T+2,5 về tài khoản — Đánh giá tốc độ hấp thụ nguồn cung chốt lời.",
            "13h45_14h25": "Khung giờ Phán quyết (Thời điểm bấm nút) — Chỉ mở mua/cắt lỗ sau 14h00 theo nến đóng cửa ngày.",
        },
    }


# ----------------------------------------------------------------------------------------------
# HỒ SƠ ĐỊNH LƯỢNG TỔNG HỢP
# ----------------------------------------------------------------------------------------------
def build_quant_profile(df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None,
                        risk_profile: str = "Trung bình", cost_basis: Optional[float] = None,
                        symbol: str = "", snapshot: Optional[dict] = None) -> dict:
    df = _ensure_indicators(df.dropna(subset=["Close"]))
    close = df["Close"]
    c = float(close.iloc[-1])
    partial = is_partial_session(df.index[-1])
    trend = _trend_regime(df)
    vr = _volatility_and_range(df)
    atr = vr.get("atr14") or c * 0.02
    levels = _key_levels(df, atr)
    rs = _relative_strength(df, index_df)
    bp = _baseline_plan(c, atr, levels, trend.get("stage"), risk_profile, cost_basis)
    beta_val = (rs or {}).get("beta_120d")
    tactical = _tactical_playbook_6step(df, levels, bp, atr, symbol=symbol, beta=beta_val, snapshot=snapshot)
    atc = _analyze_atc(df, quote_snapshot=snapshot)
    tactical["exit_stops"] = bp.get("exit_stops", {})

    ytd = None
    try:
        last_year = df.index[-1].year
        prev = df[df.index.year < last_year]
        if not prev.empty:
            ytd = (c / float(prev["Close"].iloc[-1]) - 1) * 100
    except Exception:
        pass

    profile_data = {
        "last_date": _fmt_date(df.index[-1]) + (" (phiên đang giao dịch, số liệu chưa chốt)" if partial else ""),
        "sessions": len(df),
        "close": _num(c),
        "change_1d_pct": _num(_ret(close, 1)),
        "returns": {
            "1w": _num(_ret(close, 5)), "1m": _num(_ret(close, 20)), "3m": _num(_ret(close, 60)),
            "6m": _num(_ret(close, 120)), "1y": _num(_ret(close, 250)), "ytd": _num(ytd),
        },
        "trend": trend,
        "momentum": _momentum(df),
        "volatility": vr,
        "flow": _flow(df, partial),
        "relative_strength": rs,
        "levels": levels,
        "base_rates": _base_rates(df),
        "stat_ranges": _prob_ranges(c, vr.get("daily_vol_pct")),
        "baseline_plan": bp,
        "tactical_6step": tactical,
        "atc_analysis": atc,
        "exit_stops": bp.get("exit_stops", {}),
        "price_unit": "nghìn đồng/cp" if c < 1000 else "đồng/cp",
    }

    causal_hypotheses = _evaluate_causal_hypotheses(profile_data)
    market_layers = _build_market_layers(profile_data, symbol=symbol)
    profile_data["causal_hypotheses"] = causal_hypotheses
    profile_data["market_layers"] = market_layers
    profile_data["sector_forensic"] = get_sector_forensic_guide(symbol)
    profile_data["entity_disambiguation"] = get_entity_disambiguation(symbol)

    return profile_data


# ----------------------------------------------------------------------------------------------
# Định dạng văn bản cho prompt
# ----------------------------------------------------------------------------------------------
def _v(x, suffix: str = "", sign: bool = False) -> str:
    if x is None:
        return "N/A"
    if isinstance(x, (int, float)):
        return (f"{x:+.2f}" if sign else f"{x:,.2f}") + suffix
    return f"{x}{suffix}"


def format_quant_dossier(p: dict) -> str:
    t, m, vr, fl = p["trend"], p["momentum"], p["volatility"], p["flow"]
    r = p["returns"]
    lines = [
        f"- Phiên cuối: {p['last_date']} | Số phiên dữ liệu: {p['sessions']} | Giá đóng cửa: {_v(p['close'])} ({_v(p['change_1d_pct'], '%', True)})",
        f"- Hiệu suất: 1 tuần {_v(r['1w'], '%', True)} | 1 tháng {_v(r['1m'], '%', True)} | 3 tháng {_v(r['3m'], '%', True)} | "
        f"6 tháng {_v(r['6m'], '%', True)} | 1 năm {_v(r['1y'], '%', True)} | Từ đầu năm {_v(r['ytd'], '%', True)}",
        "",
        "[XU HƯỚNG]",
        f"- Phân giai đoạn: {t['label']}",
        f"- {t.get('ma_alignment', '')}",
        f"- MA20 {_v(t['ma20'])} ({_v(t['vs_ma20_pct'], '%', True)}) | MA50 {_v(t['ma50'])} ({_v(t['vs_ma50_pct'], '%', True)}) | "
        f"MA200 {_v(t['ma200'])} ({_v(t['vs_ma200_pct'], '%', True)})  [số trong ngoặc = giá cách đường MA]",
        f"- Độ dốc 20 phiên: MA50 {_v(t['ma50_slope_20d_pct'], '%', True)} | MA200 {_v(t['ma200_slope_20d_pct'], '%', True)}",
        "",
        "[ĐỘNG LƯỢNG]",
        f"- RSI(14) Wilder: {_v(m['rsi'])} (5 phiên trước: {_v(m['rsi_5d_ago'])})",
        f"- MACD {_v(m['macd'])} {m['macd_vs_signal']} Signal {_v(m['signal'])}, {m['macd_vs_zero']} đường 0 | Histogram {_v(m['histogram'])} "
        f"({m['histogram_trend_3d'] or 'N/A'}) | Lần cắt MACD gần nhất: {m['bars_since_macd_cross'] if m['bars_since_macd_cross'] is not None else 'N/A'} phiên trước",
        f"- Phân kỳ: {m['divergence'] or 'Không phát hiện phân kỳ RSI rõ ràng trong 60 phiên'}",
        "",
        "[BIẾN ĐỘNG & VỊ TRÍ GIÁ]",
        f"- ATR(14): {_v(vr['atr14'])} ({_v(vr['atr_pct'], '%')} giá) | Biến động ngày (60 phiên): {_v(vr['daily_vol_pct'], '%')} | Năm hóa: {_v(vr['annual_vol_pct'], '%')}",
        f"- Đỉnh 52 tuần {_v(vr['high_52w'])} ({vr['high_52w_date']}) → giá cách {_v(vr['from_52w_high_pct'], '%', True)} | "
        f"Đáy 52 tuần {_v(vr['low_52w'])} ({vr['low_52w_date']}) → giá cách {_v(vr['from_52w_low_pct'], '%', True)}",
        f"- Sụt giảm tối đa 1 năm (max drawdown): {_v(vr['max_drawdown_1y_pct'], '%')}",
        f"- Biên độ 15 phiên: {_v(vr['range_15d_pct'], '%')} | 60 phiên: {_v(vr['range_60d_pct'], '%')}",
        f"- Mẫu hình nền: {vr['base_pattern'] or 'Chưa hình thành nền co hẹp rõ ràng'}",
        f"- Gap chưa lấp (60 phiên): " + ("; ".join(f"{g['type']} {g['date']} vùng {g['zone']} ({g['role']})" for g in vr["unfilled_gaps"]) or "Không có"),
        "",
        "[DÒNG TIỀN & THANH KHOẢN]",
        f"- Đánh giá: {fl['flow_verdict']}",
        f"- Tỷ lệ KL phiên tăng / phiên giảm (20 phiên): {_v(fl['up_down_volume_ratio_20d'])} | Ngày tích lũy: {fl['accumulation_days_25']} / Ngày phân phối: {fl['distribution_days_25']} (25 phiên)",
        f"- Điểm xu hướng OBV 20 phiên (−1…+1): {_v(fl['obv_trend_score_20d'])}",
        f"- Giá trị giao dịch TB 20 phiên: {_v(fl['avg_value_20d_bn'])} tỷ đồng/phiên → thanh khoản {fl['liquidity_tier']} | Xu hướng thanh khoản 20 phiên: {_v(fl['liquidity_trend_20d_pct'], '%', True)}",
        f"- KL phiên cuối / TB20: {_v(fl['last_session_vol_ratio'])}×" + (" (PHIÊN CHƯA CHỐT — không kết luận thanh khoản từ phiên này)" if fl["last_session_partial"] else ""),
        f"- Phiên đột biến khối lượng (>1,8× TB20): " + ("; ".join(fl["volume_spikes_20d"]) or "Không có"),
    ]

    rs = p.get("relative_strength")
    lines += ["", "[SỨC MẠNH TƯƠNG ĐỐI so với VN-Index]"]
    if rs:
        lines += [
            f"- Đánh giá: {rs.get('verdict', 'N/A')}",
            f"- Lợi suất vượt trội (cổ phiếu − VN-Index): 1 tuần {_v(rs.get('excess_5d'), '%', True)} | 1 tháng {_v(rs.get('excess_20d'), '%', True)} | "
            f"3 tháng {_v(rs.get('excess_60d'), '%', True)} | 6 tháng {_v(rs.get('excess_120d'), '%', True)} | 1 năm {_v(rs.get('excess_250d'), '%', True)}",
            f"- Beta 120 phiên: {_v(rs.get('beta_120d'))} | Tương quan: {_v(rs.get('corr_120d'))} | Đường RS {rs.get('rs_line_vs_ma50', 'N/A')} MA50"
            + (" | RS gần đỉnh 6 tháng" if rs.get("rs_line_near_6m_high") else ""),
        ]
    else:
        lines.append("- Chưa có dữ liệu VN-Index để so sánh")

    lv = p["levels"]
    lines += ["", "[VÙNG GIÁ QUAN TRỌNG — tính từ pivot, MA, volume profile, đỉnh/đáy 52 tuần]"]
    for x in reversed(lv["resistances"]):
        lines.append(f"- Kháng cự {_v(x['price'])} ({_v(x['distance_pct'], '%', True)}) — {x['strength']} — cơ sở: {x['basis']}")
    lines.append(f"- >>> Giá hiện tại {_v(p['close'])}")
    for x in lv["supports"]:
        lines.append(f"- Hỗ trợ {_v(x['price'])} ({_v(x['distance_pct'], '%', True)}) — {x['strength']} — cơ sở: {x['basis']}")
    vp = lv.get("volume_profile")
    if vp:
        lines.append(f"- Volume profile 6 tháng: POC {vp['poc']:.2f} | Vùng giá trị 70% KL: {vp['va_low']:.2f}–{vp['va_high']:.2f}")

    br = p.get("base_rates")
    lines += ["", "[XÁC SUẤT LỊCH SỬ CỦA TRẠNG THÁI HIỆN TẠI — chính cổ phiếu này]"]
    if br:
        lines.append(f"- Điều kiện: {br['condition']} | Giai đoạn mẫu: {br['period']}")
        for h, s in br["results"].items():
            lines.append(
                f"- Sau {h} phiên: n={s['n']} | tỷ lệ tăng {s['win_rate']}% (mọi ngày: {s['all_days_win_rate']}%) | "
                f"trung vị {_v(s['median'], '%', True)} (mọi ngày: {_v(s['all_days_median'], '%', True)}) | "
                f"10% xấu nhất ≤ {_v(s['p10'], '%', True)} | 10% tốt nhất ≥ {_v(s['p90'], '%', True)}"
            )
        lines.append(f"- Lưu ý: {br['note']}")
    else:
        lines.append("- Không đủ mẫu lịch sử (cần ≥ 120 phiên có MA50)")

    lines += ["", "[DẢI GIÁ THỐNG KÊ theo biến động thực tế — 68% / 95%]"]
    for s in p.get("stat_ranges", []):
        lines.append(f"- {s['days']} phiên: 68% trong {s['low_68']}–{s['high_68']} | 95% trong {s['low_95']}–{s['high_95']}")

    bp = p["baseline_plan"]
    lines += [
        "", "[KẾ HOẠCH GIAO DỊCH CƠ SỞ do hệ thống định lượng tính — được phép tinh chỉnh nhưng phải nêu lý do]",
        f"- Thiết lập: {bp['setup_type']}",
        f"- Vùng mua: {bp['entry_low']}–{bp['entry_high']} | Điều kiện kích hoạt: {bp['entry_trigger']}",
        f"- Cắt lỗ: {bp['stop_loss']} (−{bp['stop_pct']}%) — {bp['stop_basis']}",
        f"- Mục tiêu 1: {bp['target_1']} | Mục tiêu 2: {bp['target_2']} | R:R = 1:{bp['rr_ratio']} → {bp['rr_quality']}",
        f"- Quy mô vị thế: {bp['sizing_rule']}",
        f"- Dừng theo thời gian: {bp['time_stop']}",
    ]
    if bp.get("holder"):
        h = bp["holder"]
        lines.append(f"- Vị thế đang nắm giữ: giá vốn {h['cost_basis']} → {h['note']}")

    tac = p.get("tactical_6step")
    if tac:
        arch = tac["archetype"]
        pt3 = tac["profit_taking_3tier"]
        clk = tac["intraday_clock"]
        lines += [
            "",
            "[BỘ QUY TẮC THỰC CHIẾN 6 BƯỚC: ĐỊNH DANH TẠO LẬP, TAPE READING, CHU KỲ T+2,5 & CHỐT LỜI 3 NHỊP]",
            f"- Bước 1 – Định danh bản chất cổ phiếu: {arch['name']}",
            f"  • Bản chất vận động: {arch['nature']}",
            f"  • Nguyên tắc giao dịch cốt lõi: {arch['core_rule']}",
            f"- Bước 2 – Đọc bảng điện, sổ lệnh & dòng tiền ẩn (Tape Reading):",
            f"  • Phân tích Rũ giả (Spring) vs Gãy thật: {tac['spring_analysis']}",
            f"  • Độ sâu sổ lệnh (Order Book): {tac['order_book_analysis']}",
            f"  • Chu kỳ khối ngoại bất đối xứng: {tac['foreign_cycle_analysis']}",
        ]
        for sig in tac.get("tape_signals", []):
            if sig != tac["spring_analysis"]:
                lines.append(f"  • Tín hiệu hành vi giá/KL: {sig}")
        lines.append("- Bước 3 – Đồng hồ sinh học T+2,5 & Theo dõi hàng nổ vol về tài khoản:")
        if tac.get("t25_events"):
            for ev in tac["t25_events"]:
                lines.append(f"  • Phiên nổ vol {ev['date']} (KL {ev['vol_ratio']}× TB20, giá {ev['spike_close']}): {ev['status']}")
        else:
            lines.append("  • Không có phiên nổ thanh khoản đột biến (≥1,6× TB20) trong 6 phiên gần nhất → không vướng áp lực xả hàng lớn T+2,5.")
        lines += [
            f"  • Kỷ luật 3 khung giờ: (09h00–10h30) {clk['09h00_10h30']} | (13h00–13h45) {clk['13h00_13h45']} | (13h45–14h25) {clk['13h45_14h25']}",
            f"- Bước 4 – Bộ lọc sự kiện Quyền & Điểm rơi BCTC Quý: {tac['bctc_season_note']}",
            "- Bước 5 – Công thức Chốt lời 3 nhịp & Chặn lãi trượt (Trailing Stop):",
            f"  • {pt3['tier1_sell_30pct']['rule']}",
            f"  • {pt3['tier2_hold_50pct_trailing']['rule']}",
            f"  • {pt3['tier3_hold_20pct_fomo']['rule']}",
            "- Bước 6 – Checklist 5 phút trước khi bấm lệnh (cho người bận rộn):",
        ]
        for item in tac.get("checklist_5m", []):
            lines.append(f"  • [{item['status']}] {item['step']}: {item['detail']}")

    atc = p.get("atc_analysis")
    if atc:
        lines += [
            "",
            "[PHÂN TÍCH PHIÊN ATC & VI CẤU TRÚC CUỐI PHIÊN]",
            f"- Điểm vị trí đóng cửa (CLV): {atc['clv']:.2f} ({atc['clv_pct']}%) → {atc['session_close_position']}",
            f"- Râu nến: Râu trên {atc['upper_wick']:.2f} | Râu dưới {atc['lower_wick']:.2f} → Nhận diện: {atc['atc_pattern']}",
            f"- Đáo hạn phái sinh: {'Có cảnh báo tuần đáo hạn VN30F' if atc['derivative_week_warning'] else 'Không nằm trong tuần đáo hạn phái sinh'}",
            f"- Hàm ý tác chiến: {atc['tactical_implication']}",
        ]

    stops = p.get("exit_stops")
    if stops:
        lines += [
            "",
            "[3 CHỐT CHẶN THOÁT LỆNH: PRICE-STOP | THESIS-STOP | TIME-STOP]",
            f"- 1. Price-Stop (Chốt chặn Giá): {stops['price_stop']['price']:.2f} ({stops['price_stop']['pct']:+.1f}%) — {stops['price_stop']['basis']} → {stops['price_stop']['action']}",
            f"- 2. Thesis-Stop (Chốt chặn Luận điểm): {stops['thesis_stop']['price']:.2f} — Điều kiện: {stops['thesis_stop']['condition']} → {stops['thesis_stop']['action']}",
            f"- 3. Time-Stop (Chốt chặn Thời gian): {stops['time_stop']['sessions']} phiên — Điều kiện: {stops['time_stop']['condition']} → {stops['time_stop']['action']}",
        ]

    hyps = p.get("causal_hypotheses")
    if hyps:
        lines += [
            "",
            "[MA TRẬN 6 GIẢ THUYẾT NGUYÊN NHÂN BIẾN ĐỘNG GIÁ (CAUSAL HYPOTHESES)]",
        ]
        for h in hyps:
            lines.append(f"- [{h['id']}] {h['name']}: Xác suất {h['prob']*100:.0f}% ({h['verdict']}) | Động lực: {h['driver']} | Bằng chứng kiểm chứng: {h['verifiable_by']}")

    ml = p.get("market_layers")
    if ml:
        lines += [
            "",
            "[4 LỚP THỊ TRƯỜNG CHUNG (MARKET LAYERS)]",
            f"- {ml['layer_1_macro']['name']}: {ml['layer_1_macro']['environment']} → {ml['layer_1_macro']['implication']}",
            f"- {ml['layer_2_market']['name']}: {ml['layer_2_market']['stage']} | {ml['layer_2_market']['distribution_pressure']} → Phân bổ {ml['layer_2_market']['recommended_equity_allocation']}",
            f"- {ml['layer_3_sector']['name']}: {ml['layer_3_sector']['sector_name']} — {ml['layer_3_sector']['flow_status']} ({ml['layer_3_sector']['relative_strength']})",
            f"- {ml['layer_4_stock']['name']}: {ml['layer_4_stock']['symbol']} — {ml['layer_4_stock']['archetype']} | {ml['layer_4_stock']['tape_signal']} | {ml['layer_4_stock']['exit_stops_triad']}",
        ]

    sfg = p.get("sector_forensic")
    ed = p.get("entity_disambiguation")
    if sfg or ed:
        lines += ["", "[TỪ ĐIỂN ĐẶC THÙ NGÀNH & BẢNG ĐIỆN PHÂN BIỆT THỰC THỂ]"]
        if ed:
            lines.append(f"- Phân biệt thực thể ({ed['stock_entity']}): {ed['disambiguation_rule']} (Tránh nhầm với: {ed['common_confusion']})")
        if sfg:
            lines.append(f"- Đặc thù ngành ({sfg['sector']}): Chỉ số cốt lõi [{', '.join(sfg['key_metrics'])}]")
            lines.append(f"- Cảnh báo đỏ kế toán BCTC: {'; '.join(sfg['accounting_red_flags'])}")
            lines.append(f"- Lưu ý giao dịch thực chiến: {sfg['trading_caveats']}")

    return "\n".join(lines)


def format_market_dossier(mk: Optional[dict]) -> str:
    if not mk:
        return "- Chưa có dữ liệu VN-Index (không đánh giá được 'thời tiết' thị trường → hạ độ tin cậy)."
    t = mk["trend"]
    lines = [
        f"- Phiên: {mk['date']} | VN-Index {_v(mk['close'])} ({_v(mk['change_1d_pct'], '%', True)})",
        f"- Hiệu suất: 1 tuần {_v(mk['ret_5d'], '%', True)} | 1 tháng {_v(mk['ret_20d'], '%', True)} | 3 tháng {_v(mk['ret_60d'], '%', True)} | cách đỉnh 52 tuần {_v(mk['from_52w_high_pct'], '%', True)}",
        f"- Xu hướng: {t['label']}",
        f"- MA20 {_v(t['ma20'])} | MA50 {_v(t['ma50'])} | MA200 {_v(t['ma200'])} | RSI {_v(mk['rsi'])}",
        f"- Ngày phân phối (giảm >0,2% kèm KL tăng) trong 25 phiên: {mk['distribution_days_25']} (≥5–6 ngày = áp lực phân phối đáng kể)",
        f"- Phiên tăng mạnh (>1,2% kèm KL tăng) trong 10 phiên: {mk['strong_up_days_10']}",
        f"- KL phiên cuối / TB20: {_v(mk['volume_vs_ma20'])}×",
        f"- Trạng thái hệ thống chấm: {mk['status']} → tỷ trọng cổ phiếu tổng thể tham khảo {mk['equity_allocation']}",
    ]
    if mk.get("vn30_close") is not None:
        lines.append(f"- VN30: {_v(mk['vn30_close'])} | 1 tháng {_v(mk.get('vn30_ret_20d'), '%', True)} | {mk.get('breadth_hint', '')}")
    lines.append("- 5 phiên gần nhất:\n" + "\n".join(f"  {x}" for x in mk["recent"]))
    return "\n".join(lines)


def format_sector_dossier(sector_name: str, ranking: Optional[dict], peers: dict) -> str:
    lines = [f"- Nhóm ngành: {sector_name}"]
    if ranking:
        lines.append(f"- Xếp hạng hiệu suất 3 tháng trong nhóm: {ranking['rank']}/{ranking['of']} → {ranking['verdict']} | Trung vị 1 tháng của các mã cùng ngành: {_v(ranking['peer_median_ret20'], '%', True)}")
        for row in ranking["table"]:
            lines.append(f"  • {row['symbol']}: 1 tháng {_v(row['ret20'], '%', True)} | 3 tháng {_v(row['ret60'], '%', True)}")
    elif peers:
        for p_, info in peers.items():
            lines.append(f"  • {p_}: {info.get('Price')} ({info.get('Change', 0):+.2f}%)")
    else:
        lines.append("- Chưa có dữ liệu cổ phiếu cùng ngành")
    return "\n".join(lines)
