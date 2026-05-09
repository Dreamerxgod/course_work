import matplotlib.pyplot as plt
import math


def plot_price_series(price_history):
    plt.figure(figsize=(10, 5))
    plt.plot(price_history, label='Mid Price')
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.title('Price Evolution')
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_options_prices(option_price_history, strikes, title='Options Prices Evolution'):
    plt.figure(figsize=(12, 6))
    for K in strikes:
        prices = [step[K] for step in option_price_history]
        plt.plot(prices, label=f'Strike {K}')
    plt.xlabel('Time')
    plt.ylabel('Option Price')
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_realised_vol(rv_history, rv_avg, title="Realised Vol"):
    import matplotlib.pyplot as plt
    rv_plot = [x if x is not None else float("nan") for x in rv_history]
    avg_plot = [x if x is not None else float("nan") for x in rv_avg]

    plt.figure(figsize=(12, 5))
    plt.plot(rv_plot, label="Realised vol")
    plt.plot(avg_plot, label="Average vol")
    plt.xlabel("Time")
    plt.ylabel("Vol (annualized)")
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.show()

def _moving_average(series, window=50):
    if window <= 1:
        return [float(x) if x is not None else float("nan") for x in series]

    ma = []
    for i in range(len(series)):
        start = max(0, i - window + 1)
        window_vals = [
            x
            for x in series[start : i + 1]
            if x is not None
            and not (isinstance(x, float) and math.isnan(x))
        ]
        if not window_vals:
            ma.append(float("nan"))
        else:
            ma.append(sum(window_vals) / len(window_vals))
    return ma


def plot_implied_vol_series(iv_history, strikes, title="Implied Volatility", window=50):
    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 5))
    for K in strikes:
        raw = [step.get(K, float("nan")) for step in iv_history]
        raw = [x if x is not None else float("nan") for x in raw]
        ma = _moving_average(raw, window=window)

        # Сырые значения — полупрозрачные, MA — основная линия
        plt.plot(raw, label=f"K={K} raw", alpha=0.2)
        plt.plot(ma, label=f"K={K} MA{window}")

    plt.xlabel("Time")
    plt.ylabel("IV (annualized)")
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.show()

def plot_series(series, title="", ylabel="value"):
    xs = list(range(len(series)))
    ys = [v if v is not None else float("nan") for v in series]
    plt.figure()
    plt.plot(xs, ys)
    plt.title(title)
    plt.xlabel("t")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.3)
    plt.show()

def plot_binary_regime(regime, title="Regime"):
    xs = list(range(len(regime)))
    ys = [int(v) for v in regime]
    plt.figure()
    plt.step(xs, ys, where="post")
    plt.ylim(-0.1, 1.1)
    plt.title(title)
    plt.xlabel("t")
    plt.ylabel("active (0/1)")
    plt.grid(True, alpha=0.3)
    plt.show()

def plot_scatter(x, y, title="", xlabel="x", ylabel="y", alpha=0.4):
    xs, ys = [], []
    for a, b in zip(x, y):
        if a is None or b is None:
            continue
        xs.append(float(a))
        ys.append(float(b))

    plt.figure(figsize=(6, 5))
    plt.scatter(xs, ys, alpha=alpha, s=10)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.grid(alpha=0.3)
    plt.show()

def plot_two_regimes(series, idx_high, idx_low, title="", ylabel="value"):
    high = [series[t] if t in idx_high else None for t in range(len(series))]
    low  = [series[t] if t in idx_low  else None for t in range(len(series))]

    high_plot = [v if v is not None else float("nan") for v in high]
    low_plot  = [v if v is not None else float("nan") for v in low]

    plt.figure(figsize=(10, 4))
    plt.plot(high_plot, label="High news impact", alpha=0.85)
    plt.plot(low_plot,  label="Low news impact",  alpha=0.85)
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel("t")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.show()
