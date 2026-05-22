import MetaTrader5 as mt5
import pandas as pd
import requests
import time


# =========================================================
# TELEGRAM
# =========================================================

BOT_TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"


def send_message(text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:

        requests.get(
            url,
            params={
                "chat_id": CHAT_ID,
                "text": text,
            },
            timeout=10
        )

    except Exception as e:

        print("Telegram Error:", e)


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

last_closed_bar_time = None


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

            time.sleep(CHECK_INTERVAL)

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
            span=FAST_EMA,
            adjust=False
        ).mean()

        df["ema26"] = df["close"].ewm(
            span=SLOW_EMA,
            adjust=False
        ).mean()

        # =================================================
        # ATR
        # =================================================

        df["atr"] = compute_atr(
            df,
            ATR_PERIOD
        )

        # =================================================
        # USE CLOSED CANDLES ONLY
        # =================================================

        prev2 = df.iloc[-3]

        prev1 = df.iloc[-2]

        current_closed_bar = prev1["time"]

        # avoid duplicate processing
        if last_closed_bar_time == current_closed_bar:

            time.sleep(CHECK_INTERVAL)

            continue

        last_closed_bar_time = current_closed_bar

        o = float(prev1["open"])

        h = float(prev1["high"])

        l = float(prev1["low"])

        c = float(prev1["close"])

        print(f"\n🕒 Closed Candle: {current_closed_bar}")

        # =================================================
        # CREATE VIRTUAL TRADE
        # =================================================

        if virtual_trade is None:

            cross_above = (

                prev2["ema12"] <= prev2["ema26"]

                and

                prev1["ema12"] > prev1["ema26"]

            )

            if cross_above:

                atr = float(prev1["atr"])

                sl_dist = ATR_SL_MULTIPLIER * atr

                if sl_dist > 0:

                    entry = c

                    sl = entry - sl_dist

                    tp = entry + (sl_dist * RR)

                    virtual_trade = {

                        "entry": entry,

                        "sl": sl,

                        "tp": tp,

                    }

                    print("📈 Virtual Trade Created")

                    print(f"Entry = {entry:.2f}")

                    print(f"SL    = {sl:.2f}")

                    print(f"TP    = {tp:.2f}")

        # =================================================
        # SECOND ENTRY SIGNAL
        # =================================================

        if (
            virtual_trade is not None
            and
            active_trade is None
        ):

            trigger_price = (
                virtual_trade["entry"]
                - SECOND_ENTRY_DROP
            )

            # pullback reached
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

                    }

                    send_message(
                        f"🔥 SECOND ENTRY SIGNAL\n\n"
                        f"👉 BUY GOLD\n\n"
                        f"Entry: {trigger_price:.2f}\n"
                        f"🛑 SL: {virtual_trade['sl']:.2f}\n"
                        f"🎯 TP: {tp:.2f}\n\n"
                        f"EMA Pullback Strategy"
                    )

                    print("✅ Second Entry Sent")

        # =================================================
        # ACTIVE TRADE MANAGEMENT
        # =================================================

        if active_trade is not None:

            # =============================================
            # SL HIT
            # =============================================

            if l <= active_trade["sl"]:

                pnl = (
                    active_trade["sl"]
                    - active_trade["entry"]
                )

                send_message(
                    f"❌ CLOSE THE TRADE NOW\n\n"
                    f"Exit: {active_trade['sl']:.2f}\n"
                    f"Result: {pnl:.2f} pips"
                )

                print("❌ SL HIT")

                active_trade = None

                virtual_trade = None

            # =============================================
            # TP HIT
            # =============================================

            elif h >= active_trade["tp"]:

                pnl = (
                    active_trade["tp"]
                    - active_trade["entry"]
                )

                send_message(
                    f"🔥 CLOSE THE TRADE NOW\n\n"
                    f"Exit: {active_trade['tp']:.2f}\n"
                    f"Result: +{pnl:.2f} pips"
                )

                print("🔥 TP HIT")

                active_trade = None

                virtual_trade = None

            # =============================================
            # EMA CROSS EXIT
            # =============================================

            else:

                cross_below = (

                    prev2["ema12"] >= prev2["ema26"]

                    and

                    prev1["ema12"] < prev1["ema26"]

                )

                if cross_below:

                    exit_price = c

                    pnl = (
                        exit_price
                        - active_trade["entry"]
                    )

                    if pnl >= 0:
                        pnl_text = f"+{pnl:.2f}"

                    else:
                        pnl_text = f"{pnl:.2f}"

                    send_message(
                        f"⚠️ CLOSE THE TRADE NOW\n\n"
                        f"EMA Cross Against Position\n\n"
                        f"Exit: {exit_price:.2f}\n"
                        f"Result: {pnl_text} pips"
                    )

                    print("⚠️ EMA EXIT")

                    active_trade = None

                    virtual_trade = None

        # =================================================
        # REMOVE OLD VIRTUAL TRADE
        # =================================================

        if virtual_trade is not None:

            cross_below_virtual = (

                prev2["ema12"] >= prev2["ema26"]

                and

                prev1["ema12"] < prev1["ema26"]

            )

            if cross_below_virtual and active_trade is None:

                print("❌ Virtual Trade Cancelled")

                virtual_trade = None

        time.sleep(CHECK_INTERVAL)

    except Exception as e:

        print("ERROR:", e)

        time.sleep(10)