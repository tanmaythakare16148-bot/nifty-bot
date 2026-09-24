import os, requests, yfinance as yf
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "Bot LIVE with Liquidity Sweep"
@app.route('/send')
def send_route():
    check_market()
    return "Liquidity Check Done!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except Exception as e: print(e)

def check_market():
    try:
        # Nifty Data - 5min for sweep
        df_5m = yf.download("^NSEI", period="5d", interval="5m", auto_adjust=True, progress=False)
        df_1d = yf.download("^NSEI", period="20d", interval="1d", auto_adjust=True, progress=False)

        close = float(df_5m['Close'].iloc[-1])
        high = float(df_5m['High'].iloc[-1])
        low = float(df_5m['Low'].iloc[-1])

        prev_day_high = float(df_1d['High'].iloc[-2])
        prev_day_low = float(df_1d['Low'].iloc[-2])
        last_5_high = float(df_1d['High'].tail(5).max())
        last_5_low = float(df_1d['Low'].tail(5).min())

        # --- LIQUIDITY SWEEP LOGIC ---
        liquidity_msg = "No Sweep"
        signal = f"NIFTY {close:.0f} Range me"

        # 1. Buy Side Liquidity Sweep (BSL Sweep)
        if high > last_5_high and close < last_5_high:
            liquidity_msg = f"🔥 *BSL SWEEP* - Upar ka Liquidity le liya! Ab short ka mauka\nPrev High {last_5_high:.0f} ko sweep karke neeche aaya"
            signal = f"⚠️ *FAKE BREAKOUT = LIQUIDITY SWEEP* | SHORT kar sakte ho | SL {last_5_high+40:.0f} TGT {prev_day_low:.0f}"

        # 2. Sell Side Liquidity Sweep (SSL Sweep)
        elif low < last_5_low and close > last_5_low:
            liquidity_msg = f"🔥 *SSL SWEEP* - Neeche ka Liquidity le liya! Ab long ka mauka\nPrev Low {last_5_low:.0f} ko sweep karke upar aaya"
            signal = f"⚠️ *FAKE BREAKDOWN = LIQUIDITY SWEEP* | LONG kar sakte ho | SL {last_5_low-40:.0f} TGT {prev_day_high:.0f}"

        # 3. Normal Breakout
        elif close > prev_day_high:
            signal = f"✅ REAL BREAKOUT - {close:.0f} > {prev_day_high:.0f}"
        elif close < prev_day_low:
            signal = f"🔻 REAL BREAKDOWN - {close:.0f} < {prev_day_low:.0f}"

        # FII DATA
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            s = requests.Session()
            s.get("https://www.nseindia.com", headers=headers, timeout=5)
            r = s.get("https://www.nseindia.com/api/fiidiiTradeReact", headers=headers, timeout=10).json()
            fii = float(r[0]['buyValue']) - float(r[0]['sellValue'])
            dii = float(r[1]['buyValue']) - float(r[1]['sellValue'])
            fii_text = f"FII: {fii/100:.0f}Cr ({'BUY' if fii>0 else 'SELL'}) | DII: {dii/100:.0f}Cr"
        except:
            fii_text = "FII/DII data band"

        final_msg = f"📊 *MASTER BOT - SMC LIQUIDITY*\n\n💰 {fii_text}\n\n{signal}\n\n🧠 {liquidity_msg}\n\n📍 Levels: 5D High {last_5_high:.0f} | 5D Low {last_5_low:.0f}\nPrev Day H:{prev_day_high:.0f} L:{prev_day_low:.0f}\n⏰ {datetime.datetime.now().strftime('%d-%m %I:%M %p')}"

        send_telegram(final_msg)
    except Exception as e:
        send_telegram(f"Error in sweep: {e}")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(check_market, 'cron', minute='*/5', hour='9-15', day_of_week='mon-fri')
    scheduler.start()
    check_market()
    import time
    while True: time.sleep(60)
