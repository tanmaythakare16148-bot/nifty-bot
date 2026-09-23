import os, requests, yfinance as yf, threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
app_flask = Flask(__name__)

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

def send(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_data():
    try:
        session.get("https://www.nseindia.com", timeout=5)
        oc = session.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=10).json()
        exp = oc['records']['expiryDates'][0]
        ce=pe=0
        for x in oc['records']['data']:
            if x.get('expiryDate')==exp:
                if 'CE' in x: ce+=x['CE']['openInterest']
                if 'PE' in x: pe+=x['PE']['openInterest']
        pcr = pe/ce if ce>0 else 1.0
        vix_df = yf.download("^INDIAVIX", period="1d", interval="5m", progress=False)
        vix = float(vix_df['Close'].iloc[-1]) if not vix_df.empty else 14.0
        nifty = oc['records']['underlyingValue']
        return pcr, vix, nifty
    except:
        return 1.0, 14.0, 0

def check_fii():
    try:
        r = session.get("https://www.nseindia.com/api/fiidiiTradeReact", timeout=10).json()
        fii = float(r['data'][0]['buyValue']) - float(r['data'][0]['sellValue'])
        dii = float(r['data'][1]['buyValue']) - float(r['data'][1]['sellValue'])
        pcr, vix, nifty = get_data()
        send(f"🕞 *FII 3:30 PM*\nFII {fii:.0f} Cr {'🟢' if fii>0 else '🔴'} | DII {dii:.0f} Cr\nPCR {pcr:.2f} VIX {vix:.2f} NIFTY {nifty}")
    except: pass

def check_smc():
    try:
        df = yf.download("^NSEI", period="5d", interval="15m", progress=False).dropna()
        if len(df)<30: return
        last = df[-30:]
        curr = float(last['Close'].iloc[-1])
        ph = float(last['High'].max())
        pl = float(last['Low'].min())
        pcr, vix, _ = get_data()
        if vix>18.5: return
        sig=""
        if curr>ph: sig+=f"🚀 BOS {ph:.0f} toda\n"
        if curr<pl: sig+=f"⚠️ CHOCH {pl:.0f} toda\n"
        if sig!="": send(f"🔔 *SMC 15m* {curr:.0f}\n{sig}")
    except: pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pcr,vix,nifty=get_data()
    await update.message.reply_text(f"BOT LIVE ✅\nNIFTY {nifty:.0f} PCR {pcr:.2f} VIX {vix:.2f}")

@app_flask.route('/')
def home(): return "BOT LIVE"

sched = BackgroundScheduler()
sched.add_job(check_fii, 'cron', hour=15, minute=30, day_of_week='mon-fri')
sched.add_job(check_smc, 'cron', minute='*/15', hour='9-15', day_of_week='mon-fri')
sched.start()

if __name__ == "__main__":
    threading.Thread(target=lambda: app_flask.run(host='0.0.0.0', port=10000), daemon=True).start()
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()
