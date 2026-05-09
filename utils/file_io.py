import csv
import math

def save_price_history(filename, price_history):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'mid_price'])
        for t, price in enumerate(price_history):
            writer.writerow([t, price])

def save_trades(filename, trades):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['time', 'buyer', 'seller', 'price', 'qty'])
        for trade in trades:
            writer.writerow([trade.get('time', 0), trade['buyer'], trade['seller'], trade['price'], trade['qty']])

def save_price_history(path, price_history):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "price"])
        for t, p in enumerate(price_history):
            w.writerow([t, p])

def load_price_history(path):
    prices = []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            if "price" in row:
                v = row["price"]
            else:
                keys = list(row.keys())
                v = row[keys[1]] if len(keys) > 1 else None
            try:
                prices.append(float(v))
            except Exception:
                prices.append(None)
    return prices

def save_trades(path, trades):
    if not trades:
        with open(path, "w", newline="") as f:
            f.write("time,price,qty,buyer,seller\n")
        return

    keys = set()
    for tr in trades:
        keys |= set(tr.keys())
    keys = ["time"] + sorted([k for k in keys if k != "time"])

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for tr in trades:
            w.writerow(tr)

def load_trades(path):
    trades = []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            tr = {}
            for k, v in row.items():
                if v is None or v == "":
                    tr[k] = None
                    continue

                if k in ("time", "buyer", "seller"):
                    try:
                        tr[k] = int(float(v))
                        continue
                    except Exception:
                        tr[k] = v
                        continue

                if k in ("price", "qty", "strike"):
                    try:
                        tr[k] = float(v)
                        if k == "qty":
                            if abs(tr[k] - round(tr[k])) < 1e-9:
                                tr[k] = int(round(tr[k]))
                        continue
                    except Exception:
                        tr[k] = v
                        continue

                tr[k] = v
            trades.append(tr)
    return trades

def save_wide_series_csv(path, history, index_name="t"):
    if not history:
        with open(path, "w", newline="") as f:
            f.write(index_name + "\n")
        return

    keys = sorted({k for step in history if step for k in step.keys()})

    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([index_name] + keys)
        for t, step in enumerate(history):
            step = step or {}
            row = [t] + [step.get(k, "") for k in keys]
            w.writerow(row)

def load_wide_series_csv(path, index_name="t"):
    out = []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        strike_cols = [c for c in r.fieldnames if c != index_name]
        strike_map = {}
        for c in strike_cols:
            try:
                strike_map[c] = float(c)
            except Exception:
                strike_map[c] = c

        for row in r:
            d = {}
            for c in strike_cols:
                v = row.get(c, "")
                if v is None or v == "":
                    d[strike_map[c]] = None
                else:
                    try:
                        x = float(v)
                        if isinstance(x, float) and math.isnan(x):
                            d[strike_map[c]] = None
                        else:
                            d[strike_map[c]] = x
                    except Exception:
                        d[strike_map[c]] = None
            out.append(d)
    return out

def save_series_csv(path, series, colname="value"):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", colname])
        for t, v in enumerate(series):
            w.writerow([t, v])

def load_series_csv(path, colname=None):
    out = []
    with open(path, "r", newline="") as f:
        r = csv.DictReader(f)
        if colname is None:
            keys = r.fieldnames
            colname = keys[1] if keys and len(keys) > 1 else "value"
        for row in r:
            v = row.get(colname)
            try:
                out.append(float(v))
            except Exception:
                out.append(None)
    return out
