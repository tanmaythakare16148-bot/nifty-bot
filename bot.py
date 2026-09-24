import os, requests, time, yfinance as yf
from flask import Flask
from threading import Thread
from apscheduler.schedulers.background import BackgroundScheduler
import datetime

app = Flask(__name__)
@app.route('/')
def home(): return "V7.2 YAHOO FALLBACK LIVE"
@app.route('/send')
def send_route():
    check_market()
    return "V7.2 Sent!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=20)
    except Exception as e:
        print(e)

def get_nifty_yahoo():
    try:
        df = yf.download("^NSEI", period="1mo", interval="1d", progress=False)
        last = df.iloc[-1]
        prev = df.iloc[-2]
        close = float(last['Close'])
        high = float(last['High'])
        low = float(last['Low'])
        l5h = float(df['High'].tail(5).max())
        l5l = float(df['Low'].tail(5).min())
        return close, high, low, float(prev['High']), float(prev['Low']), l5h, l5l
    except Exception as e:
        print(f"Yahoo Error {e}")
        return None

def get_option_pcr():
    for attempt in range(2):
        try:
            s = requests.Session()
            s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"})
            s.get("https://www.nseindia.com", timeout=10)
            r = s.get("https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY", timeout=15).json()
            ce_oi=0; pe_oi=0; top_ce=[]; top_pe=[]
            for item in r['records']['data']:
                if 'CE' in item:
                    ce_oi+=item['CE']['openInterest']
                    top_ce.append((item['strikePrice'], item['CE']['changeinOpenInterest']))
                if 'PE' in item:
                    pe_oi+=item['PE']['openInterest']
                    top_pe.append((item['strikePrice'], item['PE']['changeinOpenInterest']))
            pcr = pe_oi/ce_oi if ce_oi>0 else 0
            top_ce = sorted(top_ce, key=lambda x: x[1], reverse=True)[:1]
            top_pe = sorted(top_pe, key=lambda x: x[1], reverse=True)[:1]
            return pcr, top_ce, top_pe
        except:
            time.sleep(3)
    return None, None, None

def check_market():
    yahoo_data = get_nifty_yahoo()
    if not yahoo_data:
        send_telegram("⚠️ Yahoo busy hai, 1 min baad /send dabao")
        return

    close, high, low, prev_h, prev_l, l5h, l5l = yahoo_data
    pcr, top_ce, top_pe = get_option_pcr()

    if pcr:
        if top_pe and top_ce and top_pe[0][1] > top_ce[0][1]*1.3:
            fii_msg = f"🟢 FII PUT ENTRY {top_pe[0][0]}PE (+{top_pe[0][1]/1000:.0f}k OI)"
        elif top_ce and top_pe and top_ce[0][1] > top_pe[0][1]*1.3:
            fii_msg = f"🔴 FII CALL ENTRY {top_ce[0][0]}CE (+{top_ce[0][1]/1000:.0f}k OI)"
        else:
            fii_msg = f"⚖️ Mix CE {top_ce[0][0]} PE {top_pe[0][0]}" if top_ce else "Option Mix"
        pcr_text = f"PCR {pcr:.2f} {'Oversold' if pcr>1.2 else 'Overbought' if pcr<0.8 else 'Neutral'}"
    else:
        fii_msg = "Option Chain NSE busy - Yahoo price se kaam chal raha hai"
        pcr_text = "PCR N/A (NSE block)"

    liq = f"🔥 SSL {l5l:.0f} Sweep Watch" if close<=l5l+30 else f"🔥 BSL {l5h:.0f} Sweep Watch" if close>=l5h-30 else f"Range H{l5h:.0f} L{l5l:.0f}"

    msg = f"📊 *V7.2 WORKING - NO BLOCK*\n\n💰 NIFTY {close:.0f} | {pcr_text}\n{liq}\nPrev H {prev_h:.0f} L {prev_l:.0f}\n\n🎯 *FII RADAR:*\n{fii_msg}\n\n✅ Yahoo se hai isliye block nahi hoga.\n\n⏰ {datetime.datetime.now().strftime('%d-%m %I:%M %p')}"
    send_telegram(msg)

if __name__ == "__main__":
    Thread(target=run_flask, daemon=True).start()
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(check_market, 'cron', hour=9, minute=20, day_of_week='mon-fri')
    scheduler.add_job(check_market, 'cron', hour=14, minute=45, day_of_week='mon-fri')
    scheduler.start()
    check_market()
    while True: time.sleep(60)
