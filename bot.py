import os, requests, yfinance as yf
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime, pytz
import pandas as pd

app_flask = Flask(__name__)
@app_flask.route('/')
def home(): return "Master FII Pro Bot is Live!"
@app_flask.route('/send')
def trigger():
    check_market()
    return "Checked! Check Telegram."

def run_flask():
    app_flask.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
IST = pytz.timezone("Asia/Kolkata")

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print("Sent")
    except Exception as e: print(e)

# --- 1. FII/DII DATA ---
def get_fii_dii():
    try:
        # NSE API
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://www.nseindia.com/"}
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = s.get("https://www.nseindia.com/api/fiidiiTradeReact", headers=headers, timeout=10).json()
        fii = float(r[0]['buyValue']) - float(r[0]['sellValue'])
        dii = float(r[1]['buyValue']) - float(r[1]['sellValue'])
        return fii, dii, r
    except:
        return None, None, None

# --- 2. NIFTY DATA ---
def get_nifty_data():
    try:
        df_5m = yf.download("^NSEI", period="5d", interval="5m", auto_adjust=True, progress=False)
        df_1d = yf.download("^NSEI", period="20d", interval="1d", auto_adjust=True, progress=False)
        if df_5m.empty: return None, None
        return df_5m, df_1d
    except: return None, None

# --- 3. ANALYSIS ---
def analyze():
    df_5m, df_1d = get_nifty_data()
    if df_5m is None: return "⚠️ Nifty data nahi mila"

    close = float(df_5m['Close'].iloc[-1])
    high = float(df_5m['High'].iloc[-1])
    low = float(df_5m['Low'].iloc[-1])
    prev_high = float(df_1d['High'].iloc[-2])
    prev_low = float(df_1d['Low'].iloc[-2])

    # Support Resistance (Prev Day)
    pp = (prev_high + prev_low + float(df_1d['Close'].iloc[-2]))/3
    r1 = 2*pp - prev_low
    s1 = 2*pp - prev_high

    # Fake/Real Breakout Logic
    breakout_msg = ""
    if close > r1:
        # Check if wick is big = fake
        if (high - close) > (close - low)*1.5:
            breakout_msg = f"⚠️ *FAKE BREAKOUT* lag raha hai - Trap ho sakta hai | SL {r1+30:.0f} | TGT {pp:.0f}"
            status = "FAKE"
        else:
            breakout_msg = f"✅ *REAL BREAKOUT* - Trend tez hai | TGT {r1+80:.0f}"
            status = "REAL"
    elif close < s1:
        if (close - low) > (high - close)*1.5:
            breakout_msg = f"⚠️ *FAKE BREAKDOWN* lag raha hai - Trap ho sakta hai | SL {s1-30:.0f}"
            status = "FAKE"
        else:
            breakout_msg = f"🔻 *REAL BREAKDOWN* - Neeche jayega | TGT {s1-80:.0f}"
            status = "REAL"
    else:
        status = "RANGE"
        breakout_msg = "Sideways hai, No breakout"

    # Candlestick Pattern
    o = float(df_5m['Open'].iloc[-1])
    body = abs(close-o)
    candle_pattern = "Normal"
    if body < (high-low)*0.2: candle_pattern = "Doji - Confusion"
    elif close > o and (close-low) > body*2: candle_pattern = "Hammer - Bullish Reversal"
    elif close < o and (high-close) > body*2: candle_pattern = "Shooting Star - Bearish"
    elif close > o and close > float(df_5m['Close'].iloc[-2]): candle_pattern = "Bullish Engulfing"

    # Smart Money Concept
    smc = "Liquidity Sweep" if (high > prev_high and close < prev_high) else "Order Block Test" if abs(close-s1)<20 else "No SMC"

    return close, r1, s1, breakout_msg, status, candle_pattern, smc

def check_market():
    now = datetime.datetime.now(IST)
    # Market time 9:15 to 3:30 only
    if not (9 <= now.hour <= 15):
        return

    fii, dii, raw = get_fii_dii()
    result = analyze()
    if isinstance(result, str):
        send(result)
        return

    close, r1, s1, breakout_msg, status, candle_pat, smc = result

    fii_text = f"FII: {fii/100:.0f} Cr" if fii else "FII: Data wait"
    dii_text = f"DII: {dii/100:.0f} Cr" if dii else ""

    # Final Message like your screenshot
    msg = f"📊 *LIVE ZONES (5min + Pattern)*\n\n"
    msg += f"💰 {fii_text} | {dii_text}\n\n"

    if "FAKE" in status or "REAL" in breakout_msg:
        msg += f"🔹 *NIFTY {close:.1f} - {status}*\n{breakout_msg}\n"
    else:
        msg += f"🔹 NIFTY {close:.1f} - {status} | R:{r1:.0f} S:{s1:.0f}\n"

    msg += f"\n🕯️ Candle: {candle_pat}\n"
    msg += f"🧠 SMC: {smc}\n"
    msg += f"📍 Time: {now.strftime('%I:%M %p')}"

    # Only send if important
    if "FAKE" in breakout_msg or "REAL" in breakout_msg or "Hammer" in candle_pat or "Engulfing" in candle_pat:
        send(msg)
    else:
        # For testing /send route
        if now.minute % 30 == 0: # har 30 min ek update
            send(msg)

# --- Scheduler ---
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    # Market me har 5 min check karega
    scheduler.add_job(check_market, 'cron', minute='*/5', hour='9-15', day_of_week='mon-fri')
    # Morning 9:20 ko ek daily FII summary
    scheduler.add_job(check_market, 'cron', hour=9, minute=20, day_of_week='mon-fri')
    scheduler.start()
    print("Master Pro Started")
    check_market() # start hote hi ek baar
    import time
    while True: time.sleep(60)
