import os, telebot, threading, time, requests, yfinance as yf
from flask import Flask
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip()
if not BOT_TOKEN:
    BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN","").strip()

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CHAT_IDS = set()
LAST_OI = {}

SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS"
}
headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}

def get_data(symbol):
    try:
        # Market band hone par 1d data lo, warna 5m
        df = yf.download(symbol, period="1d", interval="5m", progress=False)
        if df is None or len(df) < 10:
            df = yf.download(symbol, period="5d", interval="15m", progress=False)
        if df is None or len(df) < 5:
            df = yf.download(symbol, period="1mo", interval="1d", progress=False)
        return df
    except Exception as e:
        print(f"{symbol} error: {e}")
        return None

def analyze_symbol(name, symbol_code):
    df = get_data(symbol_code)
    if df is None or len(df) == 0:
        return f"❌ {name} chart error - kal 9:15 pe try karo"
    
    try:
        close = float(df['Close'].iloc[-1])
        high = float(df['High'].max())
        low = float(df['Low'].min())
        
        # Simple Green/Red box logic
        if close > df['Open'].iloc[-1]:
            return f"✅ {name} {close:.1f} - GREEN BOX ME HAI! Yaha se CALL ka setup dekh. SL {low:.0f}"
        else:
            return f"🔴 {name} {close:.1f} - RED BOX ME HAI! Yaha se PUT ka setup dekh. SL {high:.0f}"
    except Exception as e:
        return f"❌ {name} data error: {e}"

@bot.message_handler(commands=['start'])
def start_cmd(m):
    CHAT_IDS.add(m.chat.id)
    bot.reply_to(m, "Bot Live Hai Tanmay! 🚀\n/zones bhej ke zones dekh")

@bot.message_handler(commands=['zones'])
def zones_cmd(m):
    CHAT_IDS.add(m.chat.id)
    bot.reply_to(m, "⏳ Checking all...")
    result = ""
    for name, code in SYMBOLS.items():
        result += analyze_symbol(name, code) + "\n\n"
    bot.send_message(m.chat.id, result)

@app.route('/')
def home():
    return "Bot is Running!"

def polling():
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(5)

threading.Thread(target=polling, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
