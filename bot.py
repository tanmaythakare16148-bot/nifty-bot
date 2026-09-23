import os, requests, yfinance as yf
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

# --- Render ke liye Flask Server ---
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Nifty Bot is Live!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# --- Telegram Config ---
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
        print(f"Sent: {msg[:50]}")
    except Exception as e:
        print(f"Send Error: {e}")

def get_nifty_levels():
    try:
        data = yf.download("^NSEI", period="5d", interval="1d")
        if data.empty:
            return None
        close = float(data['Close'].iloc[-1])
        high = float(data['High'].iloc[-1])
        low = float(data['Low'].iloc[-1])
        
        # Simple Pivot Levels
        pp = (high + low + close) / 3
        r1 = (2 * pp) - low
        s1 = (2 * pp) - high
        
        msg = f"📈 *NIFTY Update* - {datetime.date.today()}\n\n"
        msg += f"Close: `{close:.2f}`\n"
        msg += f"High: `{high:.2f}` | Low: `{low:.2f}`\n\n"
        msg += f"🔴 Resistance 1: `{r1:.2f}`\n"
        msg += f"🟢 Support 1: `{s1:.2f}`\n"
        msg += f"Pivot: `{pp:.2f}`"
        return msg
    except Exception as e:
        print(f"Nifty Error: {e}")
        return None

def daily_job():
    print("Running daily job...")
    levels = get_nifty_levels()
    if levels:
        send(levels)
    else:
        send("⚠️ Nifty data nahi mila aaj.")

# --- Start Everything ---
if __name__ == "__main__":
    # 1. Flask ko alag thread me start karo (Render ke liye zaruri hai)
    Thread(target=run_flask, daemon=True).start()
    
    # 2. Scheduler start karo
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    # Roz subah 9:15 AM ko message bhejega
    scheduler.add_job(daily_job, 'cron', hour=9, minute=15)
    # Test ke liye abhi ek baar bhej dega start hote hi
    scheduler.add_job(daily_job, 'date', run_date=datetime.datetime.now() + datetime.timedelta(seconds=10))
    
    scheduler.start()
    print("Bot & Scheduler Started...")
    
    # Bot ko zinda rakho
    try:
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
