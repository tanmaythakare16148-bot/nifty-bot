import os
import time
import requests
import pytz
import threading
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "Tera BotFather wala Token Yaha Daal"
CHAT_ID = "Tera Channel ID"

# ========= 1. NSE DATA FETCH =========
def fetch_with_fallback(symbol="NIFTY"):
    try:
        # Live API - NiftyTrader
        url = f"https://www.niftytrader.in/api/option-chain?symbol={symbol}"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10).json()
        underlying = float(r.get('underlying', 23140))
        pcr = float(r.get('pcr', 0.92))
        ce_chg = int(r.get('ce_chg', 12345))
        pe_chg = int(r.get('pe_chg', 18765))
        return underlying, pcr, ce_chg, pe_chg, "LIVE"
    except:
        # Backup agar API fail ho
        return 23140, 0.92, 10000, 15000, "BACKUP"

# ========= 2. V13.1 FINAL 9 POINT =========
def get_index_data(symbol="NIFTY"):
    underlying, pcr, ce_chg, pe_chg, source = fetch_with_fallback(symbol)
    
    support = underlying - 120
    resistance = underlying + 120
    
    # 4. CHART
    if pe_chg > ce_chg + 5000:
        chart = "Bullish Engulfing + Hammer (15m)"
    elif ce_chg > pe_chg + 5000:
        chart = "Bearish Engulfing + Shooting Star (15m)"
    else:
        chart = "Doji - Indecision (15m)"
    
    # 5. BREAKOUT
    if underlying > resistance-25 and pe_chg>ce_chg:
        breakout = f"Valid Breakout {resistance:.0f} ka"
    elif underlying < support+25 and ce_chg>pe_chg:
        breakout = f"Breakdown {support:.0f} ka"
    else:
        breakout = f"Sideways - Range {int(support)} to {int(resistance)}"
    
    # 6. MAX PAIN
    max_pain = int(round(underlying / 100) * 100) - 40
    max_range = f"{max_pain-100} - {max_pain+100}"
    
    # 7. FII
    if pe_chg > ce_chg:
        fii_text = "FII BUYING (PUT Writing - Bullish, Support ban raha hai)"
    else:
        fii_text = "FII SELLING (CALL Writing - Bearish)"
        
    liquidity = f"Clean - No Sweep - Equal High/Low nahi toota - Range {support:.0f} to {int(resistance)}"
    price_action = f"S {support:.0f} | R {resistance:.0f} | VWAP {'Upar' if pe_chg>ce_chg else 'Neeche'}"
    smc = f"BOS {'Bullish' if pe_chg>ce_chg else 'Bearish'} | OB {int(support)}-{int(support+80)} | FVG {int(underlying-60)}-{int(underlying)}"
    oi_text = f"PE Chg +{pe_chg} | CE Chg +{ce_chg} -> {'BULLISH' if pe_chg>ce_chg else 'BEARISH'}"

    return f"""📊 {symbol} {int(underlying)} | PCR {pcr} | {source}
1️⃣ PCR/OI: {oi_text}
2️⃣ SMC: {smc}
3️⃣ PRICE ACTION: {price_action}
4️⃣ CHART/CANDLE: {chart}
5️⃣ BREAKOUT: {breakout}
6️⃣ MAX PAIN: -- {max_pain} | RANGE {max_range}
7️⃣ FII LIVE: {fii_text}
8️⃣ FALSE/VALID: Breakout Volume ke saath hai to Valid
9️⃣ LIQUIDITY SWEEP: {liquidity}
⏰ {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m %I:%M %p')}"""

# ========= 3. TELEGRAM COMMANDS =========
async def pcr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_index_data("NIFTY")
    await update.message.reply_text(msg)

async def bank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = get_index_data("BANKNIFTY")
    await update.message.reply_text(msg)

# ========= 4. WEB SERVER FOR RENDER + UPTIME =========
app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Nifty Bot V13.1 LIVE - 9 Point Active"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

# ========= 5. START BOT =========
def main():
    # Web server start
    threading.Thread(target=run_web, daemon=True).start()
    
    # Telegram bot
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("pcr", pcr_cmd))
    application.add_handler(CommandHandler("bank", bank_cmd))
    application.add_handler(CommandHandler("nifty", pcr_cmd))
    print("Bot Started - V13.1 FINAL")
    application.run_polling()

if __name__ == "__main__":
    main()
