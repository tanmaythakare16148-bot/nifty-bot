import os, requests, time, threading, pytz, random
from flask import Flask
from datetime import datetime
from telegram import Bot
from telegram.ext import Updater, CommandHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
app = Flask(__name__)
@app.route('/')
def home(): return "V13 FII RADAR LIVE", 200

def get_session():
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://www.nseindia.com/option-chain',
    })
    try:
        s.get("https://www.nseindia.com/option-chain", timeout=10)
        time.sleep(1)
    except: pass
    return s

def fetch_with_fallback(symbol="NIFTY"):
    s = get_session()
    try:
        r = s.get(f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}", timeout=15)
        if r.status_code==200 and "underlyingValue" in r.text:
            j=r.json()
            underlying=j['records']['underlyingValue']
            ce_oi=ce_chg=pe_oi=pe_chg=0
            for d in j['records']['data']:
                if 'CE' in d:
                    ce_oi+=d['CE']['openInterest']; ce_chg+=d['CE']['changeinOpenInterest']
                if 'PE' in d:
                    pe_oi+=d['PE']['openInterest']; pe_chg+=d['PE']['changeinOpenInterest']
            pcr=round(pe_oi/ce_oi,2) if ce_oi else 0
            return underlying, pcr, ce_chg, pe_chg, "LIVE NSE"
    except: pass
    try:
        r = s.get("https://www.nseindia.com/api/allIndices", timeout=10).json()
        underlying = next((x['last'] for x in r['data'] if x['index']==symbol or x['index']=="NIFTY 50"), 24800)
        return float(str(underlying).replace(',','')), 0.92, 15000, 25000, "BACKUP"
    except: return 24850, 0.92, 10000, 20000, "EST"

def get_index_data(symbol="NIFTY"):
    underlying, pcr, ce_chg, pe_chg, source = fetch_with_fallback(symbol)
    support = underlying - 120; resistance = underlying + 120
    breakout = f"Sideways"
    if underlying > resistance-25 and pe_chg>ce_chg: breakout=f"VALID Breakout {resistance:.0f}"
    elif underlying < support+25: breakout=f"Breakdown {support:.0f}"
    
    if underlying >= resistance-15: liquidity=f"⚠️ BSL SWEEP {resistance:.0f} pe - SL khaye"
    elif underlying <= support+15: liquidity=f"⚠️ SSL SWEEP {support:.0f} pe - LONG ka mauka"
    else: liquidity=f"Clean - Range {support:.0f}-{resistance:.0f}"
    
    fii_text = "PUT Writing = BUYING (Support)" if pe_chg>ce_chg else "CALL Writing = SELLING (Resistance)"
    return f"""📊 {symbol} {underlying:.0f} | PCR {pcr} | {source}
1️⃣ OI: PE {pe_chg:+} | CE {ce_chg:+} -> {'BULLISH' if pe_chg>ce_chg else 'BEARISH'}
2️⃣ SMC: BOS {'Bull' if pe_chg>ce_chg else 'Bear'} | OB {support:.0f} | FVG {underlying-60:.0f}
3️⃣ S {support:.0f} R {resistance:.0f}
5️⃣ BREAKOUT: {breakout}
7️⃣ FII: {fii_text}
9️⃣ LIQUIDITY: {liquidity}
⏰ {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%I:%M %p')}"""

def get_global():
    try:
        s=get_session(); r=s.get("https://www.nseindia.com/api/allIndices", timeout=10).json()
        vix=next((x['last'] for x in r['data'] if x['index']=="INDIA VIX"), "12.8")
        return f"🌍 Nifty: {next((x['last'] for x in r['data'] if x['index']=='NIFTY 50'),0)} | VIX {vix}"
    except: return "Global: Gift +40"

def cmd_pcr(u,c): u.message.reply_text(get_index_data("NIFTY"))
def cmd_bank(u,c): u.message.reply_text(get_index_data("BANKNIFTY"))
def cmd_global(u,c): u.message.reply_text(get_global())
def cmd_start(u,c): u.message.reply_text("V13 FII RADAR ON\n/pcr /bank - 3 min auto radar")

# --- MAIN RADAR LOGIC ---
def auto_loop():
    bot=Bot(token=BOT_TOKEN)
    last_pe=last_ce=0; last_bank=0
    sent=set(); ist=pytz.timezone('Asia/Kolkata')
    while True:
        now=datetime.now(ist); t=now.strftime("%H:%M")
        # Market time only
        if 9 <= now.hour <= 15:
            try:
                n_ltp,_,n_ce,n_pe,_ = fetch_with_fallback("NIFTY")
                b_ltp,_,b_ce,b_pe,_ = fetch_with_fallback("BANKNIFTY")
                
                if last_pe != 0:
                    diff_n_pe = n_pe - last_pe
                    diff_n_ce = n_ce - last_ce
                    
                    # FII ENTRY LOGIC + BANK SURGE
                    if diff_n_pe > 4000 and diff_n_pe > diff_n_ce:
                        bank_jump = b_ltp - last_bank if last_bank else 0
                        bot.send_message(chat_id=CHAT_ID, text=f"🚨 FII ENTRY LIVE {t}\n\nNIFTY PE OI +{diff_n_pe} in 3 min\nFII PUT WRITING = BUYING\n\n💥 BANKNIFTY Option Badhna Chalu - {b_ltp:.0f} ({bank_jump:+.0f})\nBANK ke Call 50% tez bhagenge ab\nLONG side dekho BANK me")
                    elif diff_n_ce > 4000:
                        bank_jump = b_ltp - last_bank if last_bank else 0
                        bot.send_message(chat_id=CHAT_ID, text=f"🚨 FII SELLING LIVE {t}\n\nNIFTY CE OI +{diff_n_ce} in 3 min\nFII CALL WRITING = SELLING\n\n💥 BANKNIFTY girna chalu {b_ltp:.0f} ({bank_jump:+.0f})\nBANK ke Put tez honge")
                
                last_pe=n_pe; last_ce=n_ce; last_bank=b_ltp

                if t in ["09:30","10:20","11:20","12:20","13:20","14:20","15:20"] and t not in sent:
                    bot.send_message(chat_id=CHAT_ID, text=f"⏰ AUTO\n{get_index_data('NIFTY')}")
                    sent.add(t)
            except Exception as e: print(e)
        
        if t=="00:01": sent.clear()
        time.sleep(180) # Har 3 minute check

updater = Updater(BOT_TOKEN, use_context=True)
for cmd,fn in [("pcr",cmd_pcr),("bank",cmd_bank),("global",cmd_global),("start",cmd_start)]:
    updater.dispatcher.add_handler(CommandHandler(cmd, fn))
threading.Thread(target=auto_loop, daemon=True).start()
threading.Thread(target=lambda: updater.start_polling(), daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
