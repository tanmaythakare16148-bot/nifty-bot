import os, requests, yfinance as yf
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "Bot LIVE - Sweep Fixed"
@app.route('/send')
def send_route():
    check_market()
    return "Done!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
    except: pass

def check_market():
    try:
        df_1d = yf.download("^NSEI", period="20d", interval="1d", auto_adjust=True, progress=False)
        if df_1d.empty or len(df_1d) < 6:
            send_telegram("⚠️ Nifty 1D data nahi mila, yfinance slow hai. 2 min me fir try karo.")
            return

        df_5m = yf.download("^NSEI", period="5d", interval="5m", auto_adjust=True, progress=False)
        # Agar 5m khali hai to 1d se kaam chalao
        if df_5m.empty or len(df_5m) < 2:
            close = float(df_1d['Close'].iloc[-1])
            high = close
            low = close
        else:
            close = float(df_5m['Close'].iloc[-1])
            high = float(df_5m['High'].iloc[-1])
            low = float(df_5m['Low'].iloc[-1])

        prev_day_high = float(df_1d['High'].iloc[-2])
        prev_day_low = float(df_1d['Low'].iloc[-2])
        last_5_high = float(df_1d['High'].tail(5).max())
        last_5_low = float(df_1d['Low'].tail(5).min())

        # Liquidity Sweep
        liquidity_msg = "No Sweep - Market Range"
        if high > last_5_high and close < last_5_high:
            liquidity_msg = f"🔥 *BSL SWEEP* - Upar SL kha gaye! SHORT zone\nSweep Level {last_5_high:.0f}"
            signal = f"⚠️ *FAKE BREAKOUT = LIQUIDITY SWEEP* | NIFTY {close:.0f} | SHORT SL {last_5_high+40:.0f}"
        elif low < last_5_low and close > last_5_low:
            liquidity_msg = f"🔥 *SSL SWEEP* - Neeche SL kha gaye! LONG zone\nSweep Level {last_5_low:.0f}"
            signal = f"⚠️ *FAKE BREAKDOWN = LIQUIDITY SWEEP* | NIFTY {close:.0f} | LONG SL {last_5_low-40:.0f}"
        elif close > prev_day_high:
            signal = f"✅ REAL BREAKOUT {close:.0f} > {prev_day_high:.0f}"
        elif close < prev_day_low:
            signal = f"🔻 REAL BREAKDOWN {close:.0f} < {prev_day_low:.0f}"
        else:
            signal = f"➡️ NIFTY {close:.0f} Range me | H:{prev_day_high:.0f} L:{prev_day_low:.0f}"

        # FII
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            s = requests.Session()
            s.get("https://www.nseindia.com", headers=headers, timeout=5)
            r = s.get("https://www.nseindia.com/api/fiidiiTradeReact", headers=headers, timeout=10).json()
            fii = float(r[0]['buyValue']) - float(r[0]['sellValue'])
            fii_text = f"FII: {fii/100:.0f}Cr"
        except:
            fii_text = "FII: Data closed"

        msg = f"📊 *MASTER BOT - LIQUIDITY FIXED*\n\n💰 {fii_text}\n\n{signal}\n\n🧠 {liquidity_msg}\n\n5D High: {last_5_high:.0f} | Low: {last_5_low:.0f}\n⏰ {datetime.datetime.now().strftime('%d-%m %I:%M %p')}"
        send_telegram(msg)

    except Exception as e:
        send_telegram(f"Error fixed: {e}")

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(check_market, 'cron', minute='*/5', hour='9-15', day_of_week='mon-fri')
    scheduler.start()
    check_market()
    import time
    while True: time.sleep(60)
