import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import concurrent.futures
import warnings
warnings.filterwarnings('ignore')

SECTOR_MAP = {
    'BANK': ['VCB', 'BID', 'CTG', 'TCB', 'MBB', 'VPB', 'ACB', 'STB', 'HDB', 'SHB', 'TPB', 'VIB', 'LPB', 'OCB', 'MSB', 'EIB', 'SSB'],
    'REAL_ESTATE': ['VHM', 'VIC', 'VRE', 'NVL', 'KDH', 'NLG', 'PDR', 'DIG', 'DXG', 'CEO', 'HDC', 'TCH', 'HDG', 'NAM'],
    'INDUSTRIAL_RE': ['KBC', 'IDC', 'VGC', 'SZC', 'BCM', 'GVR', 'PHR', 'SIP', 'NTC', 'LHG', 'TIP'],
    'STEEL': ['HPG', 'HSG', 'NKG', 'VGS', 'SMC', 'TLH', 'TVN'],
    'TECH_TELECOM': ['FPT', 'CMG', 'VGI', 'CTR', 'ITD', 'ELC', 'FOX', 'FOC'],
    'RETAIL': ['MWG', 'PNJ', 'FRT', 'DGW', 'PET', 'MSN', 'VNM', 'SAB', 'MCH', 'QNS'],
    'SECURITIES': ['SSI', 'VND', 'VCI', 'HCM', 'SHS', 'MBS', 'VIX', 'FTS', 'CTS', 'BSI', 'ORS', 'AGR', 'VDS'],
    'OIL_GAS': ['GAS', 'PLX', 'PVD', 'PVS', 'BSR', 'OIL', 'PVT', 'PVC', 'PVB'],
    'CHEM_FERT': ['DGC', 'DPM', 'DCM', 'CSV', 'LAS', 'BFC', 'DDV'],
    'LOGISTICS_PORT': ['GMD', 'HAH', 'VOS', 'VSC', 'PVT', 'MVN', 'PHP', 'SGP', 'TMS'],
    'CONSTRUCTION': ['CTD', 'HHV', 'VCG', 'FCN', 'LCG', 'PC1', 'C4G', 'HT1', 'BCC', 'KSB', 'DPG'],
    'POWER_WATER': ['POW', 'REE', 'NT2', 'GEG', 'QTP', 'HDG', 'BWE', 'TDM'],
    'SEAFOOD_AGRI': ['VHC', 'ANV', 'IDI', 'FMC', 'CMX', 'DBC', 'HAG', 'BAF', 'PAN', 'LTG'],
    'TEXTILE': ['TNG', 'MSH', 'VGT', 'GIL', 'TCM', 'STK'],
    'AVIATION_TOURISM': ['VJC', 'HVN', 'ACV', 'AST', 'SCS', 'NCT']
}

SECTOR_NAMES_VI = {
    'BANK': 'Ngân hàng',
    'REAL_ESTATE': 'Bất động sản Dân dụng',
    'INDUSTRIAL_RE': 'BĐS Khu công nghiệp & Cao su',
    'STEEL': 'Thép & Vật liệu',
    'TECH_TELECOM': 'Công nghệ & Viễn thông',
    'RETAIL': 'Bán lẻ & Tiêu dùng (F&B)',
    'SECURITIES': 'Chứng khoán',
    'OIL_GAS': 'Dầu khí',
    'CHEM_FERT': 'Hóa chất & Phân bón',
    'LOGISTICS_PORT': 'Cảng biển & Vận tải biển',
    'CONSTRUCTION': 'Xây dựng & Đầu tư công',
    'POWER_WATER': 'Điện & Nước',
    'SEAFOOD_AGRI': 'Thủy sản & Nông nghiệp',
    'TEXTILE': 'Dệt may',
    'AVIATION_TOURISM': 'Hàng không & Dịch vụ sân bay'
}


def calculate_rsi_wilder(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Tính RSI chuẩn theo J. Welles Wilder Jr. (1978) sử dụng Wilder's RMA (alpha = 1/period).
    Xử lý an toàn các trường hợp biên:
    - Khi loss == 0 và gain > 0: RSI = 100.0 (chuỗi nến toàn tăng)
    - Khi gain == 0 và loss == 0: RSI = 50.0 (giá đi ngang hoàn toàn)
    - Khi gain == 0 và loss > 0: RSI = 0.0 (chuỗi nến toàn giảm)
    """
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)

    # Wilder's smoothing RMA (alpha = 1/period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rsi = pd.Series(50.0, index=series.index)

    # Trường hợp bình thường: avg_loss > 0
    normal_mask = avg_loss > 0
    rs = avg_gain[normal_mask] / avg_loss[normal_mask]
    rsi[normal_mask] = 100.0 - (100.0 / (1.0 + rs))

    # Trường hợp toàn tăng: loss == 0 và gain > 0 -> RSI = 100.0
    zero_loss_mask = (avg_loss == 0) & (avg_gain > 0)
    rsi[zero_loss_mask] = 100.0

    # Trường hợp đi ngang: cả gain và loss = 0 -> RSI = 50.0
    zero_both_mask = (avg_loss == 0) & (avg_gain == 0)
    rsi[zero_both_mask] = 50.0

    return rsi.fillna(50.0).round(2)


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tính toán các chỉ số kỹ thuật chuyên sâu (EMA10, SMA20, MA50, MA200, RSI14 Wilder, MACD, Volatility, VolMA20)."""
    if df is None or df.empty or 'Close' not in df.columns:
        return df
    try:
        df = df.copy()
        # 1. Đường trung bình động (MA/EMA)
        df['EMA10'] = df['Close'].ewm(span=10, adjust=False).mean()
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['MA50'] = df['Close'].rolling(window=50).mean()
        df['MA200'] = df['Close'].rolling(window=200).mean()

        # 2. RSI (14) chuẩn Wilder RMA
        df['RSI'] = calculate_rsi_wilder(df['Close'], period=14)

        # 3. MACD (12, 26, 9)
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']

        # 4. Biến động 20 phiên (%)
        df['Volatility'] = df['Close'].pct_change().rolling(window=20).std() * 100

        # 5. Khối lượng trung bình 20 phiên
        if 'Volume' in df.columns:
            df['VolMA20'] = df['Volume'].rolling(window=20).mean()

        return df
    except Exception as e:
        print(f"[!] Lỗi tính toán chỉ số kỹ thuật: {e}")
        return df


def get_historical_data(symbol: str, days: int = 365, target_date: str = None, include_indicators: bool = True) -> pd.DataFrame:
    """
    Lấy dữ liệu lịch sử giá OHLCV tính từ `target_date` ngược về quá khứ.
    Loại bỏ triệt để Look-ahead Bias: Ngày cuối cùng của dữ liệu không bao giờ vượt quá `target_date`.
    Hỗ trợ cả mã cổ phiếu (HPG, FPT...) lẫn chỉ số thị trường (VNINDEX, VN30).
    """
    if target_date:
        end_date = datetime.strptime(target_date, '%Y-%m-%d')
    else:
        end_date = datetime.now()

    start_date = end_date - timedelta(days=days)
    clean_symbol = symbol.upper().strip().replace('.VN', '')

    # Chuỗi nguồn dự phòng: SSI FastConnect (chính thức) → vnstock → kho CSV cục bộ (xem data_sources.py)
    from data_sources import fetch_history
    df = fetch_history(clean_symbol, start_date, end_date)
    if df is None or df.empty:
        print(f"[-] Không tải được dữ liệu cho {clean_symbol} từ mọi nguồn")
        return pd.DataFrame()

    # [P0-DATA-01] Bộ lọc chặn Look-ahead Bias: Ngày tối đa không vượt quá target_date
    if target_date:
        df = df[df.index <= pd.to_datetime(target_date)]
    else:
        df = df[df.index <= pd.to_datetime(datetime.now().strftime('%Y-%m-%d'))]
    df = df[df.index >= pd.to_datetime(start_date.strftime('%Y-%m-%d'))]
    if df.empty:
        return pd.DataFrame()

    if include_indicators:
        df = calculate_indicators(df)
    return df


def get_stock_sector(symbol: str) -> str:
    """Trả về tên nhóm ngành tiếng Việt của mã cổ phiếu."""
    clean_symbol = symbol.upper().strip().replace('.VN', '')
    for sector_code, stock_list in SECTOR_MAP.items():
        if clean_symbol in stock_list:
            return SECTOR_NAMES_VI.get(sector_code, sector_code)
    return "Chưa phân loại ngành"


def _fetch_single_peer(peer: str, target_date: str = None):
    """Hàm phụ trợ tải nhanh 1 mã cùng ngành."""
    try:
        # ~100 ngày lịch ≈ 65 phiên → đủ tính hiệu suất 1 tháng (20 phiên) và 3 tháng (60 phiên) để xếp hạng trong ngành
        df = get_historical_data(peer, days=100, target_date=target_date, include_indicators=False)
        if df is not None and not df.empty and len(df) >= 2:
            close = df['Close'].astype(float)
            last_close = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])
            pct_change = ((last_close - prev_close) / prev_close) * 100

            def _ret(n):
                return round((last_close / float(close.iloc[-1 - n]) - 1) * 100, 2) if len(close) > n else None

            vol = float(df['Volume'].iloc[-1]) if 'Volume' in df.columns else 0
            mult = 1000.0 if last_close < 1000 else 1.0
            avg_val = float((close * df['Volume']).tail(20).mean() * mult / 1e9) if 'Volume' in df.columns else None
            return peer, {
                'Price': round(last_close, 2),
                'Change': round(pct_change, 2),
                'Volume': int(vol),
                'Ret5': _ret(5),
                'Ret20': _ret(20),
                'Ret60': _ret(60),
                'AvgValue20Bn': round(avg_val, 1) if avg_val is not None else None,
            }
    except Exception:
        pass
    return peer, None


def get_peers_performance(symbol: str, target_date: str = None) -> dict:
    """Tìm các mã cùng nhóm ngành và lấy hiệu suất giá song song bằng ThreadPoolExecutor."""
    clean_symbol = symbol.upper().strip().replace('.VN', '')
    peers = []

    for sector, stock_list in SECTOR_MAP.items():
        if clean_symbol in stock_list:
            peers = [s for s in stock_list if s != clean_symbol][:6]
            break

    if not peers:
        # Nếu mã ngoài danh mục ngành cố định, so sánh với 3 cổ phiếu trụ đại diện thị trường
        default_leaders = ['FPT', 'VCB', 'HPG', 'MWG']
        peers = [s for s in default_leaders if s != clean_symbol][:3]

    print(f"[*] Đang tải song song dữ liệu cùng ngành: {', '.join(peers)}...")

    peer_data = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(_fetch_single_peer, p, target_date) for p in peers]
        for future in concurrent.futures.as_completed(futures, timeout=25):
            try:
                peer, res = future.result()
                if res:
                    peer_data[peer] = res
            except Exception:
                continue

    return peer_data


if __name__ == "__main__":
    df = get_historical_data("FPT", 60)
    print(df.tail(5))
