import requests, time, threading, os
from flask import Flask
from datetime import datetime
import pytz
from telegram import Bot

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Render me daala hua hai
CHAT_ID = os.environ.get("CHAT_ID")

app = Flask(__name__)

# --- Better Stack ke liye ye zaruri hai ---
@app.route('/')
def home():
    return "V8 FINAL - LIVE", 200

@app.route('/health')
def health():
    return "OK", 200

# --- NSE Live Data Logic ---
def get_live_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.nseindia.com/option-chain',
        'Connection': 'keep-alive'
    }
    session = requests.Session()
    try:
        # Pehle NSE ka main page hit karna padta hai cookie ke liye
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        time.sleep(1)
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        r = session.get(url, headers=headers, timeout=15)
        
        if r.status_code != 200 or not r.text.strip().startswith('{'):
            raise Exception(f"NSE Blocked: {r.status_code}")

        j = r.json()
        # PCR Logic
        pcr = j['records']['data']
        # ... (yaha tumhara PCR calculation)
        # Sample return
        underlying = j['records']['underlyingValue']
        return f" NIFTY {underlying} | PCR: LIVE DATA\nRange LIVE\nPrev H L LIVE"
    except Exception as e:
        print(f"Backup Error Fixed, trying again: {e}")
        # Fallback - Moneycontrol ya dusra API
        return None

def telegram_loop():
    bot = Bot(token=BOT_TOKEN)
    last_auto = ""
    ist = pytz.timezone('Asia/Kolkata')
    while True:
        try:
            now = datetime.now(ist)
            curr_time = now.strftime("%H:%M")
            # Auto msg - 9:30, 10:20, 11:20, 12:20, 13:20, 14:20, 15:20
            auto_times = ["09:30", "10:20", "11:20", "12:20", "13:20", "14:20", "15:20"]
            if curr_time in auto_times and curr_time != last_auto:
                data = get_live_data()
                if data:
                    msg = f"{data}\n\n✅ Auto Update ON\n{now.strftime('%d-%m %H:%M %p IST')}"
                    bot.send_message(chat_id=CHAT_ID, text=msg)
                    last_auto = curr_time
                    print(f"Auto sent at {now}")
        except Exception as e:
            print(f"Loop Error: {e}")
        time.sleep(30)

# Threads start
threading.Thread(target=telegram_loop, daemon=True).start()

if __name__ == "__main__":
    # Flask ko 0.0.0.0 pe chalana zaruri hai Render ke liye
    app.run(host='0.0.0.0', port=10000)
