import yfinance as yf
tickers = ['^GSPC','^IXIC','^DJI','^SOX','^VIX','NVDA','MU','AAPL','VOO','MSFT','AVGO','GOOGL','META','ORCL']
data = yf.download(tickers, start='2026-08-27', end='2026-09-09', progress=False)['Close']
print(data.round(2).to_string())
