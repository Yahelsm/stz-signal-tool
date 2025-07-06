# data_loader.py

import os, json, requests, pandas as pd
from datetime import datetime
from yfinance import Ticker as YFTicker
from config import FROM_DATE

CACHE_DIR     = os.path.join(os.path.dirname(__file__), 'cache')
TICKERS_CACHE = os.path.join(CACHE_DIR, 'tickers_cache.json')
os.makedirs(CACHE_DIR, exist_ok=True)

SCREENER_IDS = {
    'sp500':       'sp500',
    'nasdaq100':   'nasdaq_100',
    'dow30':       'dow_jones',
    'russell2000': 'russell_2000'
}

def fetch_all_tickers() -> list:
    """Fetch & cache index constituents once per UTC day."""
    today = datetime.utcnow().date().isoformat()
    if os.path.exists(TICKERS_CACHE):
        try:
            c = json.load(open(TICKERS_CACHE))
            if isinstance(c, dict) and c.get('date') == today:
                return c.get('tickers', [])
        except: pass

    tickers = set()
    for scr in SCREENER_IDS.values():
        url = (
            "https://query2.finance.yahoo.com/v1/finance/screener/predefined/saved"
            f"?formatted=true&scrIds={scr}&count=2000"
        )
        try:
            r = requests.get(url, timeout=5).json()
            for q in r['finance']['result'][0]['quotes']:
                tickers.add(q['symbol'])
        except: pass

    result = sorted(tickers)
    if result:
        try:
            json.dump({'date': today, 'tickers': result}, open(TICKERS_CACHE, 'w'))
        except: pass
    return result

def batch_fetch(tickers: list, period: str, interval: str) -> dict:
    """
    Batch-fetch OHLCV for many symbols at once.
    Returns a dict { symbol: DataFrame }.
    """
    out = {}
    # split into chunks of 200 symbols
    for i in range(0, len(tickers), 200):
        chunk = tickers[i:i+200]
        raw = YFTicker(chunk).history(
            period=period,
            interval=interval,
            group_by='ticker',
            actions=False
        )
        # raw can be a multi-index DataFrame or dict
        for sym in chunk:
            try:
                df = raw[sym] if sym in raw else raw.loc[sym]
                df = df.rename(columns={
                    'Open':'open','High':'high',
                    'Low':'low','Close':'close','Volume':'volume'
                })[['open','high','low','close','volume']].dropna()
                out[sym] = df
            except:
                out[sym] = pd.DataFrame()
    return out

def fetch_news(count: int = 5) -> list:
    """
    Grab top `count` headlines from SPY news via yfinance.
    """
    news = []
    try:
        items = YFTicker("SPY").news
        for item in items[:count]:
            news.append(item.get('title'))
    except:
        pass
    return news

