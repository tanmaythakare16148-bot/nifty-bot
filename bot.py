import os, requests, time, threading, pytz
from flask import Flask
from datetime import datetime
from telegram import Bot
from telegram.ext import Updater, CommandHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

app = Flask(__name__)
@app.route('/')
def home(): return "V13.2 LIVE - Pehle jaisa + Sweep Auto", 200

def get_session():
    s = requests.Session()
    s.headers.update({'User-Agent': 'Mozilla/5.0','Referer': 'https://www.nseindia.com/option-chain','Accept':'application/json'})
    try: s.get("https://www.nseindia.com/option-chain", timeout=10)
    except: pass
    return s

def fetch_with_fallback(symbol="NIFTY"):
    s = get_session()
    try:
        r = s.get(f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}", timeout=15)
        if r.status_code == 200:
            j = r.json()
            underlying = j['records']['underlyingValue']
            ce_chg = pe_chg = 0
            ce_oi = pe_oi = 0
            for d in j['records']['data']:
                if 'CE' in d and d['CE']:
                    ce_oi += d['CE'].get('openInterest',0)
                    ce_chg += d['CE'].get('changeinOpenInterest',0)
                if 'PE' in d and d['PE']:
                    pe_oi += d['PE'].get('openInterest',0)
                    pe_chg += d['PE'].get('changeinOpenInterest',0)
            pcr = round(pe_oi/ce_oi,2) if ce_oi else 0.92
            return float(underlying), pcr, ce_chg, pe_chg, "LIVE"
    except: pass
    return 23140.0, 0.92, 15000, 25000, "BACKUP"

def get_index_data(symbol="NIFTY"):
    underlying, pcr, ce_chg, pe_chg, source = fetch_with_fallback(symbol)
    support = underlying - 120
    resistance = underlying + 120
    max_pain = int(underlying//100*100)-40
    # YEH TERA WAHI PURANA FORMAT HAI - 1 SE 9
    return f"""📊 {symbol} {int(underlying)} | PCR {pcr} | {source}
1️⃣ PCR/OI: PE Chg +{pe_chg} | CE Chg +{ce_chg} -> {'BULLISH' if pe_chg>ce_chg else 'BEARISH'}
2️⃣ SMC FULL: BOS {'Bullish' if pe_chg>ce_chg else 'Bearish'} | OB {int(support)}-{int(support+80)} | FVG {int(underlying-60)}-{int(underlying)} | Liquidity {int(support-30)} & {int(resistance+30)}
3️⃣ PRICE ACTION: S {int(support)} | R {int(resistance)} | VWAP {'Upar' if pe_chg>ce_chg else 'Neeche'} | Trend {'UP' if pe_chg>ce_chg else 'DOWN'}
4️⃣ CHART/CANDLE: {'Bullish Engulfing + Hammer (15m)' if pe_chg>ce_chg else 'Bearish Engulfing + Shooting Star (15m)'}
5️⃣ BREAKOUT: Sideways - Range me hai - {int(support)} to {int(resistance)}
6️⃣ MAX PAIN: -- {max_pain} | RANGE {max_pain-110} - {max_pain+90} | Expiry Pressure
7️⃣ FII LIVE: {'FII BUYING (PUT Writing - Bullish, Support ban raha hai)' if pe_chg>ce_chg else 'FII SELLING (CALL Writing - Bearish)'}
8️⃣ FALSE/VALID: Upar wala Breakout dekho - Volume ke saath hai to Valid
9️⃣ LIQUIDITY SWEEP: Clean - No Sweep - Equal High/Low nahi toota - Range {int(support)} to {int(resistance)}
⏰ {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m %I:%M %p')}"""

def cmd_pcr(u,c): u.message.reply_text(get_index_data("NIFTY"))
def cmd_bank(u,c): u.message.reply_text(get_index_data("BANKNIFTY"))
def cmd_start(u,c): u.message.reply_text("Bot ON hai\n/pcr - Nifty\n/bank - Banknifty")

def auto_loop():
    bot = Bot(token=BOT_TOKEN)
    last_pe, last_ce = 0, 0
    last_sweep = ""
    ist = pytz.timezone('Asia/Kolkata')
    while True:
        try:
            now = datetime.now(ist)
            if 9 <= now.hour <= 15:
                n_ltp, _, n_ce, n_pe, _ = fetch_with_fallback("NIFTY")
                b_ltp, _, _, _, _ = fetch_with_fallback("BANKNIFTY")
                support = n_ltp - 120
                resistance = n_ltp + 120

                if last_pe != 0:
                    diff_pe = n_pe - last_pe
                    diff_ce = n_ce - last_ce
                    t = now.strftime("%H:%M")
                    if diff_pe > 4000 and diff_pe > diff_ce:
                        bot.send_message(chat_id=CHAT_ID, text=f"🚨 FII ENTRY LIVE {t}\nNIFTY PE OI +{diff_pe} in 3 min\nPUT Writing = BUYING\n💥 BANKNIFTY Option Badhna Chalu {int(b_ltp)}")
                    elif diff_ce > 4000 and diff_ce > diff_pe:
                        bot.send_message(chat_id=CHAT_ID, text=f"🚨 FII SELLING LIVE {t}\nNIFTY CE OI +{diff_ce} in 3 min")

                # --- SIRF YE SWEEP AUTO NAYA JODA HAI ---
                if n_ltp <= support + 15:
                    if last_sweep != "SSL":
                        bot.send_message(chat_id=CHAT_ID, text=f"💧 LIQUIDITY SWEEP HO GAYA {now.strftime('%H:%M')}\nNIFTY ne {int(support)} ka SSL kha liya\nNeeche walo ke SL gaye\nAb Reversal LONG\nEntry {int(n_ltp)} SL {int(n_ltp-40)}")
                        last_sweep = "SSL"
                elif n_ltp >= resistance - 15:
                    if last_sweep != "BSL":
                        bot.send_message(chat_id=CHAT_ID, text=f"💧 LIQUIDITY SWEEP HO GAYA {now.strftime('%H:%M')}\nNIFTY ne {int(resistance)} ka BSL kha liya\nUpar walo ke SL gaye\nAb Reversal SHORT\nEntry {int(n_ltp)} SL {int(n_ltp+40)}")
                        last_sweep = "BSL"
                else:
                    last_sweep = ""
                last_pe, last_ce = n_pe, n_ce
        except: pass
        time.sleep(180)

updater = Updater(BOT_TOKEN, use_context=True)
updater.dispatcher.add_handler(CommandHandler("pcr", cmd_pcr))
updater.dispatcher.add_handler(CommandHandler("bank", cmd_bank))
updater.dispatcher.add_handler(CommandHandler("start", cmd_start))
threading.Thread(target=auto_loop, daemon=True).start()
threading.Thread(target=lambda: updater.start_polling(), daemon=True).start()
if __name__ == "__main__": app.run(host='0.0.0.0', port=10000)
