# main.py

import argparse, json, time
from datetime import datetime, time as dtime
import pytz, openai
from data_loader import fetch_all_tickers, batch_fetch, fetch_news
from strategy import ShakedTzafoni
from emailer import send_alert
from config import SMTP_USER, SMTP_PASS, SMTP_SERVER, SMTP_PORT, OPENAI_MODEL

ET    = pytz.timezone('America/New_York')
LOCAL = pytz.timezone('Asia/Jerusalem')

def is_market_open() -> bool:
    now = datetime.now(pytz.utc).astimezone(ET)
    return now.weekday()<5 and dtime(9,30)<=now.time()<=dtime(16,0)

SYSTEM_PROMPT = """
You are an algorithmic-trading assistant implementing the Shaked Tzafoni method:
- Identify uptrends by consecutive higher highs & higher lows; downtrends by lower highs & lower lows.
- Reference candle = highest high (or lowest low) in the sequence; breakout when price closes beyond its body.
- Use EMA8 and SMA20 for confirmation. Entry on breakout in trend direction, above EMA8/SMA20, volume high.
- Exit when sequence breaks opposite direction or price closes below/above EMA8, or EMA3 crosses EMA8.
- Include only valid candlestick patterns: hammer, inverted hammer, engulfing, doji at S/R.
Classify each ticker into one of three lists: "enter", "breakout", "exit". 
Return JSON: { "enter":[...], "breakout":[...], "exit":[...] }, max 20 symbols each.
"""

def ask_ai(payload: list, retries=3):
    for i in range(retries):
        try:
            resp = openai.ChatCompletion.create(
                model=OPENAI_MODEL,
                messages=payload,
                temperature=0
            )
            return resp.choices[0].message.content
        except Exception as e:
            wait = 2**i
            print(f"AI error ({e}), retry in {wait}s")
            time.sleep(wait)
    return None

def run_once(recipients):
    tickers = fetch_all_tickers()
    if not tickers:
        send_alert(recipients, "Stock Alert – ERROR", "Universe fetch failed.")
        return

    # fetch data & news
    intraday = batch_fetch(tickers, period='7d', interval='5m') if is_market_open() else {}
    daily    = batch_fetch(tickers, period='30d', interval='1d')
    news     = fetch_news(5)

    # build JSON payload
    data = {'prices':{}, 'news': news}
    for sym, df in (intraday.items() if is_market_open() else daily.items()):
        if df.empty: continue
        last = df.iloc[-1].to_dict()
        data['prices'][sym] = {
            'o': last['open'], 'h':last['high'],
            'l': last['low'],  'c':last['close'],
            'v': last['volume']
        }

    # AI classification
    prompt = [
        {'role':'system','content':SYSTEM_PROMPT},
        {'role':'user','content': json.dumps(data)}
    ]
    out = ask_ai(prompt)
    if not out:
        print("AI unavailable, skipping alert")
        return

    result = json.loads(out)
    # email
    now = datetime.now(pytz.utc).astimezone(LOCAL).strftime("%d/%m/%Y")
    freshness = "live" if is_market_open() else "end-of-day"
    subject = f"Stock Alert – {now}"
    lines = [f"Stock Alert – {now}", f"Mode: {freshness}", ""]
    for section in ['enter','breakout','exit']:
        lst = result.get(section,[])
        lines.append(section.title()+":")
        lines += lst[:20]
        lines.append("")

    body = "\n".join(lines)
    send_alert(recipients, subject, body)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-r','--recipients', nargs='+', required=True)
    args = parser.parse_args()
    openai.api_key = ''  # ensure your OPENAI_API_KEY env var is set
    run_once(args.recipients)

