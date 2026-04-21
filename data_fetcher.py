import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_historical_data(symbol: str, days: int = 365, target_date: str = None) -> pd.DataFrame:
    """
    Lấy dữ liệu lịch sử giá OHLCV tính từ `target_date` ngược về quá khứ.
    Dùng vnstock (KBS data source) cho cổ phiếu Việt Nam.
    """
    if target_date:
        end_date = datetime.strptime(target_date, '%Y-%m-%d') + timedelta(days=1)
    else:
        end_date = datetime.now() + timedelta(days=1)
        
    start_date = end_date - timedelta(days=days)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    # Bỏ suffix .VN nếu user nhập vào
    clean_symbol = symbol.upper().replace('.VN', '')
    
    print(f"[*] Dang tai du lieu {clean_symbol} tu {start_str} den {end_str}...")
    
    try:
        from vnstock import Vnstock
        stock = Vnstock().stock(symbol=clean_symbol, source='KBS')
        df = stock.quote.history(start=start_str, end=end_str, interval='1D')
        
        if df is not None and not df.empty:
            # Chuẩn hoá tên cột (KBS trả về: time, open, high, low, close, volume)
            df = df.rename(columns={
                'time': 'Date',
                'open': 'Open', 
                'high': 'High', 
                'low': 'Low', 
                'close': 'Close', 
                'volume': 'Volume'
            })
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df = df.set_index('Date')
            cols_to_keep = [c for c in ['Open', 'High', 'Low', 'Close', 'Volume'] if c in df.columns]
            print(f"[+] vnstock KBS: Tai thanh cong {len(df)} phien giao dich cho {clean_symbol}")
            return df[cols_to_keep]
        else:
            print(f"[-] vnstock KBS: Khong co du lieu cho {clean_symbol}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"[!] vnstock KBS loi: {e}")
        return pd.DataFrame()


SECTOR_MAP = {
    'BANK': ['VCB', 'BID', 'CTG', 'TCB', 'MBB', 'VPB', 'ACB', 'STB', 'SHB', 'EIB', 'MSB'],
    'REAL_ESTATE': ['VHM', 'VIC', 'VRE', 'NVL', 'KDH', 'NLG', 'PDR', 'DIG', 'DXG', 'CEO'],
    'STEEL': ['HPG', 'HSG', 'NKG', 'SMC', 'TLH'],
    'TECH': ['FPT', 'CMG', 'VGI', 'ITD', 'ELC'],
    'RETAIL': ['MWG', 'PNJ', 'FRT', 'DGW', 'PET'],
    'SECURITIES': ['SSI', 'VND', 'VCI', 'HCM', 'SHS', 'MBS', 'VIX', 'FTS', 'CTS', 'BSI'],
    'OIL_GAS': ['GAS', 'PLX', 'PVD', 'PVS', 'OIL'],
    'CHEM_FERT': ['DPM', 'DCM', 'DGC', 'CSV'],
    'LOGISTICS': ['GMD', 'HAH', 'VOS', 'VSC', 'MVN']
}

def get_peers_performance(symbol: str, target_date: str = None) -> dict:
    """Tìm các mã cùng nhóm ngành và lấy hiệu suất giá trong phiên gần nhất."""
    clean_symbol = symbol.upper().replace('.VN', '')
    peers = []
    
    for sector, stock_list in SECTOR_MAP.items():
        if clean_symbol in stock_list:
            peers = [s for s in stock_list if s != clean_symbol][:3]
            break
            
    if not peers:
        return {}
        
    print(f"[*] Dang tai du lieu cung nganh: {', '.join(peers)}...")
    
    peer_data = {}
    for peer in peers:
        try:
            df = get_historical_data(peer, days=10, target_date=target_date)
            if df is not None and not df.empty and len(df) >= 2:
                last_close = float(df['Close'].iloc[-1])
                prev_close = float(df['Close'].iloc[-2])
                pct_change = ((last_close - prev_close) / prev_close) * 100
                peer_data[peer] = {'Price': last_close, 'Change': pct_change}
        except Exception:
            continue
            
    return peer_data


if __name__ == "__main__":
    df = get_historical_data("FPT", 30)
    print(df.tail(5))
