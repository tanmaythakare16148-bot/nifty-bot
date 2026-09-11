import os
import telebot
import threading
from flask import Flask

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8539175413:AAG0yZ9_kftviW4AfcXHxlPvouuveOGsfu8")
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

@app.route('/')
def home():
    return "NAVA BOT LIVE"

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "Bot Live Hai Tanmay!")

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
