import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import requests
import time


# =========================================================
# TELEGRAM
# =========================================================

BOT_TOKEN = "8737122866:AAE55FmnwltxwyEqlkydqNNVa3HsNjcEt2s"
CHAT_ID = "6674481670"


def send_message(text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.get(
        url,
        params={
            "chat_id": CHAT_ID,
            "text": text
        }
    )


# =========================================================
# CONFIG
# =========================================================

SYMBOL = "XAUUSDm"

TIMEFRAME = mt5.TIMEFRAME_M15

FAST_EMA = 12
SLOW_EMA = 26

ATR_PERIOD = 14
ATR_SL_MULTIPLIER = 1.0

RR = 5.0

SECOND_ENTRY_DROP = 10.0

CHECK_INTERVAL = 5


# =========================================================
# MT5 CONNECT
# =========================================================

if not mt5.initialize():

    if not mt5.initialize(
        "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    ):

        print("❌ Failed to connect MT5")
        quit()

print("✅ Connected to MT5")

send_message(
    "✅ EMA Second Entry Bot Connected"
)


# =========================================================
# SYMBOL CHECK
# =========================================================

symbol_info = mt5.symbol_info(SYMBOL)

if symbol_info is None:

    print(f"❌ Symbol {SYMBOL} not found")

    mt5.shutdown()

    quit()

if not symbol_info.visible:

    mt5.symbol_select(SYMBOL, True)


# =========================================================
# ATR
# =========================================================

def compute_atr(df, period=14):

    high = df["high"]
    low = df["low"]

    prev_close = df["close"].shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()


# =========================================================
# STATE
# =========================================================

virtual_trade = None

active_trade = None

last_bar_time = None


# =========================================================
# MAIN LOOP
# =========================================================

while True:

    try:

        rates = mt5.copy_rates_from_pos(
            SYMBOL,
            TIMEFRAME,
            0,
            500
        )

        if rates is None or len(rates) == 0:

            time.sleep(5)

            continue

        df = pd.DataFrame(rates)

        df["time"] = pd.to_datetime(
            df["time"],
            unit="s"
        )

        # =================================================
        # EMA
        # =================================================

        df["ema12"] = df["close"].ewm(
            span=FAST_EMA
        ).mean()

        df["ema26"] = df["close"].ewm(
            span=SLOW_EMA
        ).mean()

        # =================================================
        # ATR
        # =================================================

        df["atr"] = compute_atr(
            df,
            ATR_PERIOD
        )

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        current_bar_time = curr["time"]

        # =================================================
        # ONLY NEW CANDLE
        # =================================================

        if last_bar_time == current_bar_time:

            time.sleep(CHECK_INTERVAL)

            continue

        last_bar_time = current_bar_time

        o = float(curr["open"])
        h = float(curr["high"])
        l = float(curr["low"])
        c = float(curr["close"])

        print(f"\n🕒 New Candle {current_bar_time}")

        # =================================================
        # CREATE VIRTUAL TRADE
        # =================================================

        if virtual_trade is None:

            cross_above = (
                prev["ema12"] <= prev["ema26"]
                and
                curr["ema12"] > curr["ema26"]
            )

            if cross_above:

                atr = float(curr["atr"])

                sl_dist = ATR_SL_MULTIPLIER * atr

                if sl_dist > 0:

                    virtual_trade = {
                        "entry": o,
                        "sl": o - sl_dist,
                        "tp": o + (sl_dist * RR),
                    }

                    print("📈 Virtual Trade Created")

                    print(
                        f"Entry={virtual_trade['entry']:.2f}"
                    )

                    print(
                        f"SL={virtual_trade['sl']:.2f}"
                    )

                    print(
                        f"TP={virtual_trade['tp']:.2f}"
                    )

        # =================================================
        # SECOND ENTRY SIGNAL
        # =================================================

        if (
            virtual_trade is not None
            and active_trade is None
        ):

            trigger_price = (
                virtual_trade["entry"]
                - SECOND_ENTRY_DROP
            )

            if l <= trigger_price:

                risk = (
                    trigger_price
                    - virtual_trade["sl"]
                )

                if risk > 0:

                    tp = (
                        trigger_price
                        + (risk * RR)
                    )

                    active_trade = {
                        "entry": trigger_price,
                        "sl": virtual_trade["sl"],
                        "tp": tp,
                        "risk": risk,
                        "be": False,
                    }

                    send_message(
                        f"🔥 SECOND ENTRY SIGNAL\n\n"
                        f"👉 BUY GOLD\n\n"
                        f"Entry: {trigger_price:.2f}\n"
                        f"🛑 SL: {virtual_trade['sl']:.2f}\n"
                        f"🎯 TP: {tp:.2f}\n\n"
                        f"EMA Pullback Strategy"
                    )

                    print("✅ SECOND ENTRY SENT")

        # =================================================
        # ACTIVE TRADE MANAGEMENT
        # =================================================

        if active_trade is not None:

            # =============================================
            # BREAK EVEN
            # =============================================

            if (
                not active_trade["be"]
                and
                h >= (
                    active_trade["entry"]
                    + active_trade["risk"] * 2
                )
            ):

                active_trade["sl"] = (
                    active_trade["entry"]
                )

                active_trade["be"] = True

                send_message(
                    "⚖️ Move SL to Break Even"
                )

            # =============================================
            # SL HIT
            # =============================================

            if l <= active_trade["sl"]:

                if active_trade["be"]:

                    send_message(
                        "⚖️ Break Even Hit"
                    )

                else:

                    send_message(
                        "❌ SL Hit"
                    )

                active_trade = None
                virtual_trade = None

            # =============================================
            # TP HIT
            # =============================================

            elif h >= active_trade["tp"]:

                send_message(
                    "🔥 TP HIT"
                )

                active_trade = None
                virtual_trade = None

        # =================================================
        # CLOSE VIRTUAL TRADE
        # =================================================

        if virtual_trade is not None:

            virtual_close = False

            if l <= virtual_trade["sl"]:

                virtual_close = True

            elif h >= virtual_trade["tp"]:

                virtual_close = True

            elif (
                prev["ema12"] >= prev["ema26"]
                and
                curr["ema12"] < curr["ema26"]
            ):

                virtual_close = True

            if virtual_close:

                if active_trade is None:

                    virtual_trade = None

        time.sleep(CHECK_INTERVAL)

    except Exception as e:

        print("ERROR:", e)

        time.sleep(10)