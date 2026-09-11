import os, telebot, threading, yfinance as yf, requests
import pandas as pd
from flask import Flask
import time
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip() or os.environ.get("TELEGRAM_TOKEN","").strip()
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CHAT_ID = 809517300
SYMBOLS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}

@app.route('/')
def home():
    return "Bot Live - Step 2 FII ON"

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
                msg += f"{name} ❌ Data kam\n"; continue
            last_price = get_scalar(data['Close'].iloc[-1])
            low = get_scalar(data['Low'].min())
            msg += f"{name} {last_price:.1f} ✅ GREEN BOX - {low:.1f} - {low+50:.1f}\n"
        except Exception as e:
            msg += f"{name} Error {e}\n"
    return msg

def get_fii_dii():
    try:
        # NSE FII DII API
        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/"
        }
        # NSE needs session
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=10)
        r = s.get(url, headers=headers, timeout=10)
        data = r.json()

        # Last data
        fii_buy = float(data[0]['buyValue']) if len(data)>0 else 0
        fii_sell = float(data[0]['sellValue']) if len(data)>0 else 0
        fii_net = float(data[0]['netValue']) if len(data)>0 else 0

        dii_buy = float(data[1]['buyValue']) if len(data)>1 else 0
        dii_sell = float(data[1]['sellValue']) if len(data)>1 else 0
        dii_net = float(data[1]['netValue']) if len(data)>1 else 0

        msg = f"💰 FII/DII LIVE ({data[0].get('category','')})\n\n"
        msg += f"FII Net: {fii_net:.2f} Cr {'🟢 BUYING' if fii_net>0 else '🔴 SELLING'}\n"
        msg += f" Buy: {fii_buy:.2f} | Sell: {fii_sell:.2f}\n\n"
        msg += f"DII Net: {dii_net:.2f} Cr {'🟢 BUYING' if dii_net>0 else '🔴 SELLING'}\n"
        msg += f" Buy: {dii_buy:.2f} | Sell: {dii_sell:.2f}\n\n"

        if fii_net > 500 and dii_net > 0:
            msg += "📈 Signal: STRONG BULLISH - Dono Buy kar rahe hai"
        elif fii_net < -500:
            msg += "📉 Signal: BEARISH - FII Heavy Selling"
        else:
            msg += "⚖️ Signal: SIDEWAYS / Mixed"
        return msg
    except Exception as e:
        return f"FII/DII Data abhi NSE se nahi aa raha\nError: {e}\n\nTry after 6PM - Daily data tab update hota hai"

@bot.message_handler(commands=['zones','start'])
def handle_zones(message):
    bot.reply_to(message, get_zones())

@bot.message_handler(commands=['fii','FII','dii','DII'])
def handle_fii(message):
    bot.reply_to(message, "⏳ FII/DII check kar raha hu...")
    bot.send_message(message.chat.id, get_fii_dii())

def daily_loop():
    while True:
        now_utc = datetime.utcnow()
        if now_utc.hour == 3 and now_utc.minute == 45: # 9:15 IST
            if now_utc.weekday() < 5:
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
