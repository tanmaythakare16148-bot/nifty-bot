import os, telebot, threading, yfinance as yf
import pandas as pd
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip() or os.environ.get("TELEGRAM_TOKEN","").strip()
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "FINNIFTY": "^CNXFINANCE"
}

def get_scalar(series_or_df):
    """Series error ka permanent fix"""
    val = series_or_df
    # Agar Series hai to uska pehla value le lo
    if isinstance(val, pd.Series):
        val = val.iloc[0]
    # Agar abhi bhi list/array jaisa hai
    try:
        return float(val)
    except:
        return float(str(val).replace(',', ''))

def get_data(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="1d", progress=False, auto_adjust=True)
        if df is None or len(df) == 0:
            return None
        # Naye yfinance me column MultiIndex hota hai - isko flat karo
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        print(f"Data error {symbol}: {e}")
        return None

def analyze_symbol(name, code):
    df = get_data(code)
    if df is None or len(df) < 2:
        return f"❌ {name} data nahi mila"
    try:
        close = get_scalar(df['Close'].iloc[-1])
        open_p = get_scalar(df['Open'].iloc[-1])
        high = get_scalar(df['High'].max())
        low = get_scalar(df['Low'].min())

        if close > open_p:
            return f"✅ {name} {close:.1f} - GREEN BOX ME HAI!\n CALL Setup | SL {low:.0f} | TGT {close+80:.0f}"
        else:
            return f"🔴 {name} {close:.1f} - RED BOX ME HAI!\n PUT Setup | SL {high:.0f} | TGT {close-80:.0f}"
    except Exception as e:
        return f"❌ {name} error: {e}"

@bot.message_handler(commands=['start'])
def start_cmd(m):
    bot.reply_to(m, "Bot Live Hai Tanmay! 🚀\n/zones bhej ke zones dekh\nSubah 9:15 baje auto alert ayega")

@bot.message_handler(commands=['zones'])
def zones_cmd(m):
    bot.reply_to(m, "⏳ Checking all 3 indices...")
    msg = ""
    for name, code in SYMBOLS.items():
        msg += analyze_symbol(name, code) + "\n\n"
    bot.send_message(m.chat.id, msg)

@app.route('/')
def home():
    return "Bot is Running - Tanmay Edition!"

def polling():
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"Polling restart: {e}")

threading.Thread(target=polling, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
