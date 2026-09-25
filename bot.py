import os
import time
import requests
import yfinance as yf
from datetime import datetime

# Render ke Environment se lega
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_msg(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN ya CHAT_ID nahi mila Environment me")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        print(e)

def check_nifty():
    try:
        data = yf.download("^NSEI", period="2d", interval="5m")
        # Yaha tera purana sweep logic tha
        # Abhi test ke liye simple price bhej raha hu
        price = round(data['Close'].iloc[-1], 2)
        print(f"Nifty: {price}")
        return price
    except Exception as e:
        print(f"Error: {e}")
        return None

# Bot Start
send_msg("✅ *Purana Nifty Bot START ho gaya* \nAb sweep alert ayega")

while True:
    price = check_nifty()
    # if sweep_mila: send_msg(f"🚨 SWEEP ALERT Nifty {price}")
    time.sleep(60)
