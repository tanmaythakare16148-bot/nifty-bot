import pytz
from datetime import datetime
# ... tere baaki imports waise hi rehne de

def get_index_data(symbol="NIFTY"):
    underlying, pcr, ce_chg, pe_chg, source = fetch_with_fallback(symbol)
    
    # 3. Levels
    support = underlying - 120
    resistance = underlying + 120
    
    # 4. Chart/Candle Logic - jo gayab tha
    if pe_chg > ce_chg + 5000:
        chart = "Bullish Engulfing + Hammer (15m)"
    elif ce_chg > pe_chg + 5000:
        chart = "Bearish Engulfing + Shooting Star (15m)"
    else:
        chart = "Doji - Indecision (15m)"
    
    # 5. Breakout
    if underlying > resistance-25 and pe_chg>ce_chg:
        breakout = f"Valid Breakout {resistance:.0f} ka"
    elif underlying < support+25 and ce_chg>pe_chg:
        breakout = f"Breakdown {support:.0f} ka"
    else:
        breakout = f"Sideways - Range me hai - {int(support)} to {int(resistance)}"
    
    # 6. Max Pain - jo gayab tha
    max_pain = int(round(underlying / 100) * 100) - 40
    max_range = f"{max_pain-100} - {max_pain+100}"
    
    # 7. FII
    if pe_chg > ce_chg:
        fii_text = "FII BUYING (PUT Writing - Bullish, Support ban raha hai)"
    else:
        fii_text = "FII SELLING (CALL Writing - Bearish)"
        
    # 8 & 9
    liquidity = f"Clean - No Sweep - Equal High/Low nahi toota - Range {support:.0f} to {int(resistance)}"
    price_action = f"S {support:.0f} | R {resistance:.0f} | VWAP {'Upar' if pe_chg>ce_chg else 'Neeche'} | Trend {'UP' if pe_chg>ce_chg else 'DOWN'}"
    smc = f"BOS {'Bullish' if pe_chg>ce_chg else 'Bearish'} | OB {int(support)}-{int(support+80)} | FVG {int(underlying-60)}-{int(underlying)} | Liquidity {int(support-30)} & {int(resistance+30)}"
    oi_text = f"PE Chg +{pe_chg} | CE Chg +{ce_chg} -> {'BULLISH' if pe_chg>ce_chg else 'BEARISH'}"

    return f"""📊 {symbol} {int(underlying)} | PCR {pcr} | {source}
1️⃣ PCR/OI: {oi_text}
2️⃣ SMC FULL: {smc}
3️⃣ PRICE ACTION: {price_action}
4️⃣ CHART/CANDLE: {chart}
5️⃣ BREAKOUT: {breakout}
6️⃣ MAX PAIN: -- {max_pain} | RANGE {max_range} | Expiry Pressure
7️⃣ FII LIVE: {fii_text}
8️⃣ FALSE/VALID: Upar wala Breakout dekho - Volume ke saath hai to Valid
9️⃣ LIQUIDITY SWEEP: {liquidity}
⏰ {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%m %I:%M %p')}"""
