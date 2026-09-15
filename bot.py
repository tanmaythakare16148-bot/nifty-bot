import os, requests
from flask import Flask
import yfinance as yf
import talib
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
app_flask = Flask(__name__)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

def get_pcr_vix():
    try:
        session.get("https://www.nseindia.com", timeout=5)
        oc = session.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=10).json()
        exp = oc['records']['expiryDates'][0]
        ce_oi = 0
        pe_oi = 0
        for x in oc['records']['data']:
            if x.get('expiryDate') == exp:
                if 'CE' in x: ce_oi += x['CE']['openInterest']
                if 'PE' in x: pe_oi += x['PE']['openInterest']
        pcr = pe_oi / ce_oi if ce_oi > 0 else 1.0
        # VIX
        vix_df = yf.download("^INDIAVIX", period="1d", interval="5m", progress=False)
        vix = float(vix_df['Close'].iloc[-1]) if not vix_df.empty else 14.0
        nifty = oc['records']['underlyingValue']
        return pcr, vix, nifty
    except Exception as e:
        print(f"PCR error: {e}")
        return 1.0, 14.0, 0

def check_fii_auto():
    try:
        r = session.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=10).json()
        # data[0] = FII, data[1] = DII
        fii_buy = float(r['data'][0]['buyValue'])
        fii_sell = float(r['data'][0]['sellValue'])
        fii_net = fii_buy - fii_sell
        dii_net = float(r['data'][1]['buyValue']) - float(r['data'][1]['sellValue'])

        pcr, vix, nifty = get_pcr_vix()
        vix_msg = "✅ VIX Low - Trade Safe" if vix < 15 else "⚠️ VIX HIGH (>15) - Trade Avoid"

        msg = f"🚨 *FII/DII AUTO 3:45 PM*\n\nFII Net: {fii_net:.0f} Cr {'🟢 BUY' if fii_net>0 else '🔴 SELL'}\nDII Net: {dii_net:.0f} Cr\n\nNIFTY: {nifty}\nPCR: {pcr:.2f} | VIX: {vix:.2f}\n{vix_msg}"
        send(msg)
    except Exception as e:
        print(f"FII error: {e}")

def check_smc_auto():
    try:
        df = yf.download("^NSEI", period="5d", interval="15m", progress=False).dropna()
        if len(df) < 40: return
        last = df[-35:]
        curr = float(last['Close'].iloc[-1])
        pcr, vix, _ = get_pcr_vix()

        # VIX FILTER - High VIX pe signal mat de
        if vix > 16.5:
            return

        # KILLZONE
        now = datetime.now()
        hr = now.hour
        if 10 <= hr <= 11:
            kz = "🔥 NY KILLZONE ACTIVE (10-11:30) - Asli Bank Move"
        elif 13 <= hr <= 14:
            kz = "🪤 LUNCH TRAP (1:30-2:30) - 90% Fake Breakout"
        else:
            kz = "⏳ Non-Killzone - Wait & Watch"

        sig = ""
        # CANDLE PATTERN
        hammer = talib.CDLHAMMER(last['Open'], last['High'], last['Low'], last['Close'])
        engulf = talib.CDLENGULFING(last['Open'], last['High'], last['Low'], last['Close'])
        if hammer.iloc[-1] == 100: sig += "🔨 HAMMER (15m) - Bullish Reversal 🟢\n"
        if engulf.iloc[-1] == 100: sig += "🟢 Bullish Engulfing - Demand Zone\n"
        if engulf.iloc[-1] == -100: sig += "🔴 Bearish Engulfing - Supply Zone\n"

        # BOS / CHOCH
        prev_high = float(last['High'].iloc[-16:-2].max())
        prev_low = float(last['Low'].iloc[-16:-2].min())
        if curr > prev_high:
            sig += f"💥 BOS Break - {prev_high:.0f} toda - Uptrend Continue 🟢\n"
        if curr < prev_low:
            sig += f"⚠️ CHOCH Break - {prev_low:.0f} toda - Downtrend 🔴\n"

        # ORDER BLOCK
        ob = last.iloc[-4]
        vol_avg = last['Volume'].mean()
        if ob['Volume'] > vol_avg * 1.5 and ob['Close'] > ob['Open']:
            sig += f"🏦 ORDER BLOCK (Green Zone) {ob['Low']:.0f}-{ob['High']:.0f} - Bank Entry\n"

        # FVG
        if last['Low'].iloc[-1] > last['High'].iloc[-3]:
            sig += f"📦 FVG Gap {last['High'].iloc[-3]:.0f}-{last['Low'].iloc[-1]:.0f} - Fill hone ayega\n"

        # LIQUIDITY GRAB
        all_high = float(last['High'].max())
        if last['High'].iloc[-1] >= all_high*0.999 and last['Close'].iloc[-1] < all_high:
            sig += f"🪤 LIQUIDITY GRAB {all_high:.0f} pe - Fakeout tha!\n"

        if sig!= "":
            final_msg = f"🧠 *SMC + PRICE ACTION AUTO (15m)*\nNIFTY: {curr:.0f} | VIX: {vix:.2f} | PCR: {pcr:.2f}\n{kz}\n\n{sig}"
            send(final_msg)
    except Exception as e:
        print(f"SMC error: {e}")

def daily_summary():
    try:
        pcr, vix, nifty = get_pcr_vix()
        view = "Kal GAP UP possible" if pcr > 1.2 else "Kal GAP DOWN possible" if pcr < 0.8 else "Kal SIDEWAYS rahega"
        msg = f"📊 *DAILY SUMMARY 8 PM*\n\nNIFTY Close: {nifty:.0f}\nPCR: {pcr:.2f} | VIX: {vix:.2f}\n\n🧠 View: {view}\nOrder Block ko mark karke rakho, kal wahi se entry hogi."
        send(msg)
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pcr, vix, nifty = get_pcr_vix()
    await update.message.reply_text(f"NAVA BANK BOT LIVE ✅\n\nNIFTY: {nifty:.0f}\nPCR: {pcr:.2f} | VIX: {vix:.2f}\n\n100% AUTO:\n• FII 3:50pm\n• SMC/BOS har 15min\n• VIX Filter + Killzone\n• Daily Summary 8pm")

# SCHEDULER
sched = BackgroundScheduler()
sched.add_job(check_fii_auto, 'cron', hour=15, minute=50, day_of_week='mon-fri')
sched.add_job(check_smc_auto, 'cron', minute='*/15', hour='9-15', day_of_week='mon-fri')
sched.add_job(daily_summary, 'cron', hour=20, minute=0, day_of_week='mon-fri')
sched.start()

@app_flask.route('/')
def home():
    return "NAVA BANK BOT FINAL LIVE - SMC + VIX + Killzone"

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=10000)).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()
