import os, requests, yfinance as yf
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

# --- Flask Server for Render ---
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Nifty Bot is Live! Add /send to URL to test."

@app_flask.route('/send')
def trigger_send():
    daily_job()
    return "Message sent! Check Telegram."

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# --- Telegram Config ---
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(msg):
    try:
        print(f"Trying to send to CHAT_ID: {CHAT_ID}")
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=15)
        print(f"Telegram Response: {r.text}")
    except Exception as e:
        print(f"Send Error: {e}")

def get_nifty_levels():
    try:
        data = yf.download("^NSEI", period="5d", interval="1d", auto_adjust=True)
        if data.empty:
            return None
        close = float(data['Close'].iloc[-1])
        high = float(data['High'].iloc[-1])
        low = float(data['Low'].iloc[-1])
        
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
        return f"⚠️ Error fetching Nifty: {e}"

def daily_job():
    print("Running daily_job...")
    levels = get_nifty_levels()
    if levels:
        send(levels)
    else:
        send("Test message: Bot is Live!")

# --- Start Everything ---
if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(daily_job, 'cron', hour=9, minute=15)
    scheduler.start()
    print("Bot & Scheduler Started...")

    # Start hote hi turant bhej dega
    daily_job()

    try:
        import time
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
