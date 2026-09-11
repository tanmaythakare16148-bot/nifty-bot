import telebot, requests, threading, time
from flask import Flask
import os

BOT_TOKEN ="8539175413:AAHujbpYwHbWtW03akA0J99fJ7kVKugc2S4"
bot = telebot.TeleBot(BOT_TOKEN)

GREEN_TOP, GREEN_BOTTOM = 23590, 23540
RED_TOP, RED_BOTTOM = 23850, 23800
last_price = 0

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot LIVE hai Tanmay!"

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "✅ NAVA BOT LIVE - Render pe!\n\n/zones - Demand/Supply\n/fii - FII DII\n/ltp 23560 - Fake/Real BO\n/oc - Option Chain")

@bot.message_handler(commands=['zones'])
def zones(m):
    bot.reply_to(m, f"📦 ZONES:\n\n🟢 DEMAND: {GREEN_BOTTOM}-{GREEN_TOP}\n🔴 SUPPLY: {RED_BOTTOM}-{RED_TOP}")

@bot.message_handler(commands=['fii'])
def fii_cmd(m):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get("https://www.nseindia.com/api/fiidiiTradeReact", headers=headers, timeout=15).json()
        fii_net = float(r['data'][0]['buyValue']) - float(r['data'][0]['sellValue'])
        dii_net = float(r['data'][1]['buyValue']) - float(r['data'][1]['sellValue'])
        bot.reply_to(m, f"FII Net: {fii_net:.0f} Cr\nDII Net: {dii_net:.0f} Cr")
    except:
        bot.reply_to(m, "FII data 6pm ke baad aayega")

@bot.message_handler(commands=['ltp'])
def ltp(m):
    global last_price
    try:
        p = float(m.text.replace('/ltp','').strip())
        last_price = p
        bot.reply_to(m, f"Nifty {p} - Zone check kar raha hu")
    except:
        bot.reply_to(m, "/ltp 23560 aise likh")

@bot.message_handler(commands=['oc'])
def oc(m):
    bot.reply_to(m, "OC market hours me check kar - /oc")

def run_bot():
    while True:
        try:
            bot.infinity_polling()
        except:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
