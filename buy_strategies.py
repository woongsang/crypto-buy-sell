def volatility_breakout_price(prev_high, prev_low, prev_price, x=0.5):
    prev_range = prev_high - prev_low
    return prev_price + (x * prev_range), prev_price - (x * prev_range)

