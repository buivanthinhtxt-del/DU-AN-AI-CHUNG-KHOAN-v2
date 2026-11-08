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

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd

from data_fetcher import calculate_indicators

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
# HỒ SƠ ĐỊNH LƯỢNG TỔNG HỢP
# ----------------------------------------------------------------------------------------------
def build_quant_profile(df: pd.DataFrame, index_df: Optional[pd.DataFrame] = None,
                        risk_profile: str = "Trung bình", cost_basis: Optional[float] = None) -> dict:
    df = _ensure_indicators(df.dropna(subset=["Close"]))
    close = df["Close"]
    c = float(close.iloc[-1])
    partial = is_partial_session(df.index[-1])
    trend = _trend_regime(df)
    vr = _volatility_and_range(df)
    atr = vr.get("atr14") or c * 0.02
    levels = _key_levels(df, atr)

    ytd = None
    try:
        last_year = df.index[-1].year
        prev = df[df.index.year < last_year]
        if not prev.empty:
            ytd = (c / float(prev["Close"].iloc[-1]) - 1) * 100
    except Exception:
        pass

    return {
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
        "relative_strength": _relative_strength(df, index_df),
        "levels": levels,
        "base_rates": _base_rates(df),
        "stat_ranges": _prob_ranges(c, vr.get("daily_vol_pct")),
        "baseline_plan": _baseline_plan(c, atr, levels, trend.get("stage"), risk_profile, cost_basis),
        "price_unit": "nghìn đồng/cp" if c < 1000 else "đồng/cp",
    }


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
