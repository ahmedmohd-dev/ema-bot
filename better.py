import pandas as pd
import numpy as np

# Load + fix columns
df = pd.read_csv("xauusd_m1.csv", sep="\t")
df.columns = df.columns.str.replace("<", "").str.replace(">", "").str.strip()

# Use correct column name (UPPERCASE)
df["ema20"] = df["CLOSE"].ewm(span=20).mean()
df["ema50"] = df["CLOSE"].ewm(span=50).mean()

# Find crossovers
crosses = []

for i in range(1, len(df)):
    prev_fast = df.iloc[i-1]["ema20"]
    prev_slow = df.iloc[i-1]["ema50"]
    curr_fast = df.iloc[i]["ema20"]
    curr_slow = df.iloc[i]["ema50"]

    # Detect cross
    if prev_fast < prev_slow and curr_fast > curr_slow:
        cross_type = "BUY"
    elif prev_fast > prev_slow and curr_fast < curr_slow:
        cross_type = "SELL"
    else:
        continue

    # Simple method
    simple = (curr_fast + curr_slow) / 2

    # Advanced interpolation
    numerator = prev_slow - prev_fast
    denominator = (curr_fast - prev_fast) - (curr_slow - prev_slow)

    if denominator != 0:
        t_cross = numerator / denominator
        advanced = prev_fast + t_cross * (curr_fast - prev_fast)
    else:
        advanced = np.nan

    crosses.append({
    "type": cross_type,
    "date": df.iloc[i]["DATE"],
    "time": df.iloc[i]["TIME"],
    "simple": simple,
    "advanced": advanced,
    "ema20": curr_fast,
    "ema50": curr_slow
})

# Show first 10 examples
for c in crosses[:10]:
    print(c)