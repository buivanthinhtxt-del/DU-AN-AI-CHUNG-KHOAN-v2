import yfinance as yf

for ticker in ["^VNINDEX.VN", "GC=F", "BZ=F", "USDVND=X"]:
    data = yf.Ticker(ticker).history(period="5d")
    print(f"--- {ticker} ---")
    print(data.tail(1) if not data.empty else "No Data")
