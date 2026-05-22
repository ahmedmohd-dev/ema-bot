import pandas as pd
import numpy as np

# ==============================
# CONFIG
# ==============================
RISK_PER_TRADE = 0.003   # 0.3%
RR = 4                   # 1:4
BE_RR = 2               # break even at 1:2
PIP_VALUE = 1.0          # 10 pips = 1.0 for XAUUSD


# ==============================
# LOAD DATA
# ==============================
def load_data(path):
    df = pd.read_csv(path, sep="\t")
    df.columns = df.columns.str.replace("<", "").str.replace(">", "").str.strip()
    
    df["datetime"] = pd.to_datetime(df["DATE"] + " " + df["TIME"])
    df = df.sort_values("datetime").reset_index(drop=True)

    return df


# ==============================
# INDICATORS
# ==============================
def calculate_indicators(df):
    df["ema20"] = df["CLOSE"].ewm(span=20).mean()
    df["ema50"] = df["CLOSE"].ewm(span=50).mean()
    return df


# ==============================
# SIGNALS
# ==============================
def generate_signals(df):
    signals = []

    for i in range(1, len(df)):
        prev_fast = df.iloc[i-1]["ema20"]
        prev_slow = df.iloc[i-1]["ema50"]
        curr_fast = df.iloc[i]["ema20"]
        curr_slow = df.iloc[i]["ema50"]

        if prev_fast < prev_slow and curr_fast > curr_slow:
            signals.append((i, "BUY"))
        elif prev_fast > prev_slow and curr_fast < curr_slow:
            signals.append((i, "SELL"))

    return signals


# ==============================
# BACKTEST ENGINE
# ==============================
def run_backtest(df, signals):
    balance = 1000
    equity_curve = []
    trades = []

    for idx, signal in signals:
        if idx + 1 >= len(df):
            continue

        entry_row = df.iloc[idx + 1]
        entry_price = entry_row["OPEN"]

        spread = entry_row["SPREAD"] / 1000

        if signal == "BUY":
            entry_price += spread

        # SL from EMA cross
        ema20 = df.iloc[idx]["ema20"]
        ema50 = df.iloc[idx]["ema50"]
        cross_price = (ema20 + ema50) / 2

        if signal == "BUY":
            sl = cross_price - PIP_VALUE
            risk = entry_price - sl
            tp = entry_price + RR * risk
        else:
            sl = cross_price + PIP_VALUE
            risk = sl - entry_price
            tp = entry_price - RR * risk

        if risk <= 0:
            continue

        # Position sizing
        risk_amount = balance * RISK_PER_TRADE
        lot = risk_amount / risk

        trade_result = None
        result = None
        be_triggered = False

        for j in range(idx + 1, len(df)):
            row = df.iloc[j]
            high = row["HIGH"]
            low = row["LOW"]

            if signal == "BUY":

                # BE trigger
                if not be_triggered and high >= entry_price + BE_RR * risk:
                    sl = entry_price
                    be_triggered = True

                if low <= sl:
                    if be_triggered:
                        trade_result = 0
                        result = "BE"
                    else:
                        trade_result = (sl - entry_price) * lot
                        result = "LOSS"
                    break

                elif high >= tp:
                    trade_result = (tp - entry_price) * lot
                    result = "WIN"
                    break

            else:

                if not be_triggered and low <= entry_price - BE_RR * risk:
                    sl = entry_price
                    be_triggered = True

                if high >= sl:
                    if be_triggered:
                        trade_result = 0
                        result = "BE"
                    else:
                        trade_result = (entry_price - sl) * lot
                        result = "LOSS"
                    break

                elif low <= tp:
                    trade_result = (entry_price - tp) * lot
                    result = "WIN"
                    break

        if trade_result is not None:
            balance += trade_result
            equity_curve.append(balance)

            trades.append({
                "type": signal,
                "entry": entry_price,
                "sl": sl,
                "tp": tp,
                "profit": trade_result,
                "balance": balance,
                "result": result,
                "time": entry_row["datetime"]
            })

    return trades, equity_curve


# ==============================
# ANALYTICS
# ==============================
def analyze_results(trades):
    df = pd.DataFrame(trades)

    total = len(df)
    wins = len(df[df["result"] == "WIN"])
    losses = len(df[df["result"] == "LOSS"])
    be = len(df[df["result"] == "BE"])

    winrate = (wins / total) * 100 if total > 0 else 0

    avg_win = df[df["result"] == "WIN"]["profit"].mean()
    avg_loss = df[df["result"] == "LOSS"]["profit"].mean()

    expectancy = df["profit"].mean()

    profit_factor = abs(
        df[df["result"] == "WIN"]["profit"].sum() /
        df[df["result"] == "LOSS"]["profit"].sum()
    ) if losses > 0 else 0

    print("\n===== OVERALL STATS =====")
    print(f"Total Trades: {total}")
    print(f"Wins: {wins} | Losses: {losses} | BE: {be}")
    print(f"Winrate: {winrate:.2f}%")
    print(f"Avg Win: {avg_win:.2f}")
    print(f"Avg Loss: {avg_loss:.2f}")
    print(f"Expectancy: {expectancy:.2f}")
    print(f"Profit Factor: {profit_factor:.2f}")

    return df


# ==============================
# TIME FEATURES
# ==============================
def add_time_features(df):
    df["hour"] = df["time"].dt.hour

    def get_session(hour):
        if hour >= 22:
            return "Sydney"
        elif hour < 7:
            return "Tokyo"
        elif hour < 14:
            return "London"
        else:
            return "NewYork"

    df["session"] = df["hour"].apply(get_session)
    return df


# ==============================
# SESSION ANALYSIS
# ==============================
def session_analysis(df):
    print("\n===== SESSION ANALYSIS =====")

    grouped = df.groupby("session")

    for name, group in grouped:
        total = len(group)
        wins = len(group[group["result"] == "WIN"])

        winrate = (wins / total) * 100 if total > 0 else 0
        profit = group["profit"].sum()

        print(f"{name}:")
        print(f"  Trades: {total}")
        print(f"  Winrate: {winrate:.2f}%")
        print(f"  Profit: {profit:.2f}")
        print("---------------------------")


# ==============================
# HOUR ANALYSIS
# ==============================
def hour_analysis(df):
    print("\n===== HOUR ANALYSIS =====")

    grouped = df.groupby("hour")

    for hour, group in grouped:
        total = len(group)
        wins = len(group[group["result"] == "WIN"])

        winrate = (wins / total) * 100 if total > 0 else 0
        profit = group["profit"].sum()

        print(f"Hour {hour}:")
        print(f"  Trades: {total}")
        print(f"  Winrate: {winrate:.2f}%")
        print(f"  Profit: {profit:.2f}")
        print("---------------------------")


# ==============================
# SAVE CSV
# ==============================
def save_results(df):
    df.to_csv("backtest_results.csv", index=False)
    print("\nResults saved to backtest_results.csv")


# ==============================
# MAIN
# ==============================
df = load_data("xauusd_2025.csv")
df = calculate_indicators(df)
signals = generate_signals(df)

trades, equity = run_backtest(df, signals)

results_df = analyze_results(trades)
results_df = add_time_features(results_df)

session_analysis(results_df)
hour_analysis(results_df)

save_results(results_df)

print(f"\nFinal Balance: {equity[-1] if equity else 1000}")