import csv
import math
import os


def read_series(path, colname):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            v = row.get(colname)
            try:
                out.append(float(v))
            except (TypeError, ValueError):
                out.append(None)
    return out


def read_wide(path, index_name="t"):
    if not os.path.exists(path):
        return [], []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        fields = [c for c in r.fieldnames if c != index_name]
        rows = []
        for row in r:
            d = {}
            for c in fields:
                v = row.get(c, "")
                try:
                    d[c] = float(v) if v not in ("", None) else None
                except (TypeError, ValueError):
                    d[c] = None
            rows.append(d)
    return fields, rows


def mean_safe(xs):
    vals = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return sum(vals) / len(vals) if vals else None


def lag1_autocorr(returns):
    n = len(returns)
    if n < 3:
        return None
    a = returns[1:]
    b = returns[:-1]
    ma = sum(a) / len(a)
    mb = sum(b) / len(b)
    num = sum((ai - ma) * (bi - mb) for ai, bi in zip(a, b))
    den_a = math.sqrt(sum((ai - ma) ** 2 for ai in a))
    den_b = math.sqrt(sum((bi - mb) ** 2 for bi in b))
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)


def mean_run_length(returns, eps=1e-12):
    runs = []
    cur_len = 0
    cur_sign = 0
    for r in returns:
        if r > eps:
            s = +1
        elif r < -eps:
            s = -1
        else:
            continue
        if s == cur_sign:
            cur_len += 1
        else:
            if cur_len > 0:
                runs.append(cur_len)
            cur_sign = s
            cur_len = 1
    if cur_len > 0:
        runs.append(cur_len)
    return sum(runs) / len(runs) if runs else None


def count_csv_rows(path):
    if not os.path.exists(path):
        return 0
    with open(path, "r") as f:
        total = sum(1 for line in f)
    return max(0, total - 1)


def avg_iv(path):
    fields, rows = read_wide(path)
    vals = []
    for row in rows:
        for v in row.values():
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                vals.append(v)
    return mean_safe(vals)


def summarize_run(out_dir):
    rv_series = read_series(os.path.join(out_dir, "rv_history.csv"), "rv")
    mean_rv = mean_safe(rv_series)

    prices = read_series(os.path.join(out_dir, "price_history.csv"), "price")
    f_series = read_series(os.path.join(out_dir, "fundamental_history.csv"), "F")
    mean_dist_F = None
    max_dist_F = None
    if prices and f_series:
        n = min(len(prices), len(f_series))
        diffs = [abs(prices[i] - f_series[i]) for i in range(n)
                 if prices[i] is not None and f_series[i] is not None]
        if diffs:
            mean_dist_F = sum(diffs) / len(diffs)
            max_dist_F = max(diffs)

    returns = []
    for i in range(1, len(prices)):
        p0, p1 = prices[i - 1], prices[i]
        if p0 is None or p1 is None or p0 <= 0 or p1 <= 0:
            continue
        returns.append(math.log(p1 / p0))
    ar1 = lag1_autocorr(returns)
    run_len = mean_run_length(returns)

    inv_fields, inv_rows = read_wide(os.path.join(out_dir, "mm_inventory.csv"))
    abs_vals = []
    for row in inv_rows:
        for c in inv_fields:
            v = row.get(c)
            if v is not None:
                abs_vals.append(abs(v))
    mean_abs_mm_inv = (sum(abs_vals) / len(abs_vals)) if abs_vals else None

    mean_iv_call = avg_iv(os.path.join(out_dir, "iv_call.csv"))
    mean_iv_put = avg_iv(os.path.join(out_dir, "iv_put.csv"))

    return {
        "mean_rv": mean_rv,
        "mean_distance_from_F": mean_dist_F,
        "max_distance_from_F": max_dist_F,
        "lag1_autocorr": ar1,
        "mean_run_length": run_len,
        "mean_abs_mm_inventory": mean_abs_mm_inv,
        "mean_iv_call": mean_iv_call,
        "mean_iv_put": mean_iv_put,
        "spot_trades_count": count_csv_rows(os.path.join(out_dir, "trades.csv")),
        "option_trades_count": count_csv_rows(os.path.join(out_dir, "option_trades.csv")),
    }
