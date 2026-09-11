import os, telebot, threading, yfinance as yf
import pandas as pd
from flask import Flask
import time
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip() or os.environ.get("TELEGRAM_TOKEN","").strip()
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

CHAT_ID = 809517300
SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK"
}

@app.route('/')
def home():
    return "Bot Live - Step 1 Auto ON"

def get_scalar(s):
    val = s
    if hasattr(val, 'iloc'):
        try: val = val.iloc[-1]
        except: val = float(val)
    return float(val)

def get_zones():
    msg = "📊 LIVE ZONES (5min)\n\n"
    for name, sym in SYMBOLS.items():
        try:
            data = yf.download(sym, period="2d", interval="5m", progress=False, auto_adjust=True)
            if len(data) < 10:
                msg += f"{name} ❌ Data kam\n"
                continue
            last_price = get_scalar(data['Close'].iloc[-1])
            low = get_scalar(data['Low'].min())
            msg += f"{name} {last_price:.1f} ✅ GREEN BOX - {low:.1f} - {low+50:.1f}\n"
        except Exception as e:
            msg += f"{name} Error {e}\n"
    return msg

@bot.message_handler(commands=['zones','start'])
def handle_zones(message):
    bot.reply_to(message, get_zones())

# 9:15 AM AUTO
def daily_loop():
    while True:
        now_utc = datetime.utcnow()
        # IST = UTC + 5:30, so 9:15 IST = 3:45 UTC
        if now_utc.hour == 3 and now_utc.minute == 45:
            if datetime.utcnow().weekday() < 5:
                try:
                    bot.send_message(CHAT_ID, "⏰ 9:15 AM AUTO ALERT\n\n" + get_zones())
                    time.sleep(70)
                except: pass
        time.sleep(30)

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=daily_loop, daemon=True).start()
    bot.infinity_polling()
