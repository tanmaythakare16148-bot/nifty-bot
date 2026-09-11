import os, telebot, threading, yfinance as yf, requests
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
    return "Bot Live - FINAL MASTER"

def get_scalar(s):
    if hasattr(s, 'iloc'):
        try: return float(s.iloc[-1])
        except: return float(s)
    return float(s)

def analyze_symbol(name, sym):
    try:
        data = yf.download(sym, period="5d", interval="5m", progress=False, auto_adjust=True)
        if len(data) < 50:
            return f"{name} ❌ Data kam\n"

        close = data['Close']
        high = data['High']
        low = data['Low']
        last = get_scalar(close.iloc[-1])

        # 5 Day High/Low for Fake/Real Check
        day_high = get_scalar(high.tail(78).max()) # 1 day ~ 78 candles of 5m
        day_low = get_scalar(low.tail(78).min())

        green_low = get_scalar(low.min())
        green_high = green_low + 70

        # Fake vs Real + CALL/PUT Logic
        signal = ""
        sl = 0
        tgt = 0
        is_fake = False

        if last > green_low and last < green_high:
            signal = "✅ GREEN BOX ME HAI!"
            if last > day_high * 0.998:
                signal += "\n🔥 REAL BREAKOUT - CALL Setup"
                sl = last - 60
                tgt = last + 120
            else:
                signal += "\n⏳ WAIT - Box ke andar"
                sl = green_low - 20
                tgt = green_high + 50
        elif last > green_high:
            # Upar nikal gaya - Fake check
            if last > day_high:
                signal = "🚀 REAL BREAKOUT UP - CALL"
                sl = green_high
                tgt = last + 100
            else:
                signal = "⚠️ FAKE BREAKOUT lag raha hai - Trap ho sakta hai"
                sl = last + 50
                tgt = last - 80
                is_fake = True
        else:
            signal = "🔴 GREEN BOX ke neeche - PUT Side"
            sl = last + 60
            tgt = last - 100

        status = "🟢" if "CALL" in signal else "🔴" if "PUT" in signal else "✅"
        extra = "FAKE" if is_fake else "REAL" if "REAL" in signal else "GREEN"

        return f"{status} {name} {last:.1f} - {extra}\n{signal} | SL {sl:.0f} | TGT {tgt:.0f}\n\n"
    except Exception as e:
        return f"{name} Error {e}\n\n"

def get_zones():
    msg = "📊 LIVE ZONES (5min + Pattern)\n\n"
    for name, sym in SYMBOLS.items():
        msg += analyze_symbol(name, sym)
    return msg

def get_fii_dii():
    try:
        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://www.nseindia.com/"}
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=headers, timeout=10)
        r = s.get(url, headers=headers, timeout=10)
        data = r.json()
        fii_net = float(data[0]['netValue']); dii_net = float(data[1]['netValue'])
        fii_buy = float(data[0]['buyValue']); fii_sell = float(data[0]['sellValue'])
        dii_buy = float(data[1]['buyValue']); dii_sell = float(data[1]['sellValue'])
        msg = f"💰 FII/DII LIVE\n\nFII Net: {fii_net:.2f} Cr {'🟢 BUYING' if fii_net>0 else '🔴 SELLING'}\n Buy: {fii_buy:.2f} | Sell: {fii_sell:.2f}\n\n"
        msg += f"DII Net: {dii_net:.2f} Cr {'🟢 BUYING' if dii_net>0 else '🔴 SELLING'}\n Buy: {dii_buy:.2f} | Sell: {dii_sell:.2f}\n\n"
        if fii_net > 500 and dii_net > 0: msg += "📈 STRONG BULLISH"
        elif fii_net < -500: msg += "📉 BEARISH - FII Selling"
        else: msg += "⚖️ SIDEWAYS / Mixed"
        return msg
    except Exception as e:
        return f"FII Data Error: {e}"

@bot.message_handler(commands=['zones','start','signal'])
def handle_zones(message):
    bot.reply_to(message, get_zones())

@bot.message_handler(commands=['fii','dii'])
def handle_fii(message):
    bot.reply_to(message, "⏳ FII/DII check...")
    bot.send_message(message.chat.id, get_fii_dii())

def daily_loop():
    while True:
        now_utc = datetime.utcnow()
        if now_utc.hour == 3 and now_utc.minute == 45 and now_utc.weekday() < 5:
            try:
                bot.send_message(CHAT_ID, "⏰ 9:15 AM AUTO MASTER ALERT\n\n" + get_zones() + "\n" + get_fii_dii())
                time.sleep(70)
            except: pass
        time.sleep(30)

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=daily_loop, daemon=True).start()
    bot.infinity_polling()
