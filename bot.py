import os, telebot, threading, yfinance as yf, requests
from flask import Flask
import time
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip() or os.environ.get("TELEGRAM_TOKEN","").strip()
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)
CHAT_ID = 809517300
SYMBOLS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}

@app.route('/')
def home():
    return "Bot Live - FULL AUTO"

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
        close = data['Close']; high = data['High']; low = data['Low']
        last = get_scalar(close.iloc[-1])
        day_high = get_scalar(high.tail(78).max())
        day_low = get_scalar(low.tail(78).min())
        green_low = get_scalar(low.min())
        green_high = green_low + 70

        signal = ""; sl=0; tgt=0; is_fake=False
        if last > green_low and last < green_high:
            signal = "✅ GREEN BOX ME HAI!"
            if last > day_high * 0.998:
                signal += "\n🔥 REAL BREAKOUT - CALL Setup"
                sl = last - 60; tgt = last + 120
            else:
                signal += "\n⏳ WAIT - Box ke andar"
                sl = green_low - 20; tgt = green_high + 50
        elif last > green_high:
            if last > day_high:
                signal = "🚀 REAL BREAKOUT UP - CALL"
                sl = green_high; tgt = last + 100
            else:
                signal = "⚠️ FAKE BREAKOUT - Trap!"
                sl = last + 50; tgt = last - 80
                is_fake = True
        else:
            signal = "🔴 BOX ke neeche - PUT Side"
            sl = last + 60; tgt = last - 100

        status = "🟢" if "CALL" in signal else "🔴" if "PUT" in signal else "✅"
        extra = "FAKE" if is_fake else "REAL" if "REAL" in signal else "GREEN"
        return f"{status} {name} {last:.1f} - {extra}\n{signal} | SL {sl:.0f} | TGT {tgt:.0f}\n\n"
    except Exception as e:
        return f"{name} Error {e}\n\n"

def get_zones():
    msg = "📊 AUTO SIGNAL (5min)\n\n"
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
        msg = f"💰 FII {fii_net:.0f} Cr {'🟢' if fii_net>0 else '🔴'} | DII {dii_net:.0f} Cr {'🟢' if dii_net>0 else '🔴'}\n"
        if fii_net > 500 and dii_net > 0: msg += "📈 STRONG BULLISH"
        elif fii_net < -500: msg += "📉 BEARISH"
        else: msg += "⚖️ SIDEWAYS"
        return msg
    except:
        return "FII Data sham ko update hota hai"

# Manual bhi rahega backup ke liye
@bot.message_handler(commands=['zones','start','signal','fii','dii'])
def handle_manual(message):
    if 'fii' in message.text or 'dii' in message.text:
        bot.send_message(message.chat.id, get_fii_dii())
    else:
        bot.send_message(message.chat.id, get_zones() + "\n" + get_fii_dii())

def auto_loop():
    sent_minutes = set()
    while True:
        try:
            # IST Time
            ist_now = datetime.utcnow() + timedelta(hours=5, minutes=30)
            # Market Time 9:15 to 15:30, Mon-Fri
            if ist_now.weekday() < 5 and 9 <= ist_now.hour <= 15:
                is_market = not (ist_now.hour == 15 and ist_now.minute > 30) and not (ist_now.hour == 9 and ist_now.minute < 15)
                # Har 15 min pe: 15, 30, 45, 00
                if is_market and ist_now.minute in [0,15,30,45]:
                    key = f"{ist_now.date()}-{ist_now.hour}-{ist_now.minute}"
                    if key not in sent_minutes:
                        full_msg = f"⏰ AUTO ALERT {ist_now.strftime('%I:%M %p')}\n\n" + get_zones() + "\n" + get_fii_dii()
                        bot.send_message(CHAT_ID, full_msg)
                        sent_minutes.add(key)
                        # memory clear
                        if len(sent_minutes) > 50:
                            sent_minutes.clear()
            time.sleep(30)
        except Exception as e:
            print(f"Auto loop error {e}")
            time.sleep(30)

def run_flask():
    app.run(host="0.0.0.0", port=10000)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=auto_loop, daemon=True).start()
    bot.infinity_polling()
