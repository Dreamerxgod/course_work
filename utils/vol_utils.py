import math

def realised_vol_last(prices, lookback=200, annualization=252):
    n = len(prices)
    if n < 3:
        return None

    start = max(1, n - lookback)
    rets = []
    for i in range(start, n):
        p0 = prices[i-1]
        p1 = prices[i]
        if p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
            continue
        rets.append(math.log(p1 / p0))

    if len(rets) < 2:
        return None

    m = sum(rets) / len(rets)
    var = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(max(var, 0.0)) * math.sqrt(annualization)

def rolling_mean(series, window=200):
    out = [None] * len(series)
    for t in range(len(series)):
        start = max(0, t - window + 1)
        vals = [x for x in series[start:t+1] if x is not None]
        if len(vals) == 0:
            continue
        out[t] = sum(vals) / len(vals)
    return out
