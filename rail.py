import pandas as pd
import time
import requests

# =========================
# SETTINGS
# =========================

BOT_TOKEN = "8567849177:AAFxsueSGVHcOpEI1a0DVgIY1vu-jIl9Fbc"
CHAT_ID = "6674481670"

TWELVE_API_KEY = "43fb3f50fca54f4b9ccc79780ab1cbe5"

SYMBOL = "XAU/USD"
INTERVAL = "1min"

RR = 4
BE_RR = 2
PIP_VALUE = 1.0

# =========================
# TELEGRAM
# =========================

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.get(url, params={"chat_id": CHAT_ID, "text": text})

# =========================
# GET DATA FROM TWELVE DATA
# =========================

def get_data():
    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "outputsize": 30,
        "apikey": TWELVE_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "values" not in data:
        print("❌ API Error:", data)
        return None

    df = pd.DataFrame(data["values"])

    # convert columns to float
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    # oldest -> newest
    df = df.iloc[::-1].reset_index(drop=True)

    return df

# =========================
# START
# =========================

print("✅ Connected to Twelve Data")
send_message("✅ Bot is running using Twelve Data")

# =========================
# STATE
# =========================

last_signal = None
active_trade = None

# =========================
# MAIN LOOP
# =========================

while True:

    try:

        df = get_data()

        if df is None or len(df) < 30:
            time.sleep(60)
            continue

        # =========================
        # EMA
        # =========================

        df["ema12"] = df["close"].ewm(span=12).mean()
        df["ema26"] = df["close"].ewm(span=26).mean()

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        price = curr["close"]

        # =========================
        # ACTIVE TRADE MANAGEMENT
        # =========================

        if active_trade is not None:

            high = curr["high"]
            low = curr["low"]

            entry = active_trade["entry"]
            sl = active_trade["sl"]
            tp = active_trade["tp"]
            risk = active_trade["risk"]
            direction = active_trade["type"]

            # ===== BUY =====
            if direction == "BUY":

                # Move to BE
                if not active_trade["be"] and high >= entry + BE_RR * risk:
                    active_trade["sl"] = entry
                    active_trade["be"] = True

                    send_message("⚖️ Move SL to entry")

                # SL Hit
                if low <= active_trade["sl"]:

                    if active_trade["be"]:
                        send_message("⚖️ Break Even hit")
                    else:
                        send_message("❌ SL hit")

                    active_trade = None

                # TP Hit
                elif high >= tp:

                    send_message("🔥 Full TP smashed")
                    active_trade = None

            # ===== SELL =====
            else:

                if not active_trade["be"] and low <= entry - BE_RR * risk:

                    active_trade["sl"] = entry
                    active_trade["be"] = True

                    send_message("⚖️ Move SL to entry")

                # SL Hit
                if high >= active_trade["sl"]:

                    if active_trade["be"]:
                        send_message("⚖️ Break Even hit")
                    else:
                        send_message("❌ SL hit")

                    active_trade = None

                # TP Hit
                elif low <= tp:

                    send_message("🔥 Full TP smashed")
                    active_trade = None

        # =========================
        # NEW SIGNAL
        # =========================

        if active_trade is None:

            # ===== BUY SIGNAL =====
            if prev["ema12"] < prev["ema26"] and curr["ema12"] > curr["ema26"]:

                if last_signal != "BUY":

                    entry = price

                    cross_price = (curr["ema12"] + curr["ema26"]) / 2
                    sl = cross_price - PIP_VALUE

                    risk = entry - sl
                    tp = entry + RR * risk

                    if risk > 0:

                        active_trade = {
                            "type": "BUY",
                            "entry": entry,
                            "sl": sl,
                            "tp": tp,
                            "risk": risk,
                            "be": False
                        }

                        send_message(
                            f"HIGH risk traDE ☠️\n"
                            f"👉🏾 BUY GOLD\n"
                            f"Entry {entry:.2f}\n"
                            f"🛑 SL {sl:.2f}\n"
                            f"✅ TP {tp:.2f}\n"
                            f"disclaimer: Past profits do not predict future earnings.\n"
                            f"Risk only 1-3% per position."
                        )

                        last_signal = "BUY"

            # ===== SELL SIGNAL =====
            elif prev["ema12"] > prev["ema26"] and curr["ema12"] < curr["ema26"]:

                if last_signal != "SELL":

                    entry = price

                    cross_price = (curr["ema12"] + curr["ema26"]) / 2
                    sl = cross_price + PIP_VALUE

                    risk = sl - entry
                    tp = entry - RR * risk

                    if risk > 0:

                        active_trade = {
                            "type": "SELL",
                            "entry": entry,
                            "sl": sl,
                            "tp": tp,
                            "risk": risk,
                            "be": False
                        }

                        send_message(
                            f"HIGH risk traDE ☠️\n"
                            f"👉🏾 SELL GOLD\n"
                            f"Entry {entry:.2f}\n"
                            f"🛑 SL {sl:.2f}\n"
                            f"✅ TP {tp:.2f}\n"
                            f"disclaimer: Past profits do not predict future earnings.\n"
                            f"Risk only 1-3% per position."
                        )

                        last_signal = "SELL"

        # =========================
        # WAIT
        # =========================

        time.sleep(60)

    except Exception as e:

        print("Error:", e)
        time.sleep(10)