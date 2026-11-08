from vnstock import Vnstock
import warnings
warnings.filterwarnings('ignore')

# Test KBS source
try:
    s = Vnstock().stock('FPT', 'KBS')
    df = s.quote.history(start='2026-03-01', end='2026-04-16', interval='1D')
    if df is not None:
        print("KBS OK, shape:", df.shape)
        print("Columns:", list(df.columns))
        print(df.tail(3).to_string())
    else:
        print("KBS: None result")
except Exception as e:
    print("KBS ERR:", str(e)[:300])

# Test FMP source  
try:
    s2 = Vnstock().stock('FPT', 'FMP')
    df2 = s2.quote.history(start='2026-03-01', end='2026-04-16', interval='1D')
    if df2 is not None:
        print("FMP OK, shape:", df2.shape)
        print("Columns:", list(df2.columns))
        print(df2.tail(3).to_string())
    else:
        print("FMP: None result")
except Exception as e:
    print("FMP ERR:", str(e)[:300])
