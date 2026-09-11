import telebot, requests, threading, time
from flask import Flask
import 
BOT_TOKEN = "8539175413:AAG0yZ9_kftviW4AfcXHxlPvouuveOGsfu8"
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
