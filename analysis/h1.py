import csv
import math
import os
import sys

from scipy import stats

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as cfg


SCENARIOS = [
    "h1p_low", "h1p_high",
    "low_info", "high_info",
    "low_trend", "high_trend",
    "tight_inv", "loose_inv",
]


def read_column(path, col):
    out = []
    with open(path) as f:
        for row in csv.DictReader(f):
            try:
                out.append(float(row[col]))
            except (TypeError, ValueError, KeyError):
                pass
    return out


def log_return_variance(price_history_path):
    prices = []
    with open(price_history_path) as f:
        for row in csv.DictReader(f):
            try:
                prices.append(float(row["price"]))
            except (TypeError, ValueError, KeyError):
                pass
    if len(prices) < 3:
        return None
    rets = []
    for i in range(1, len(prices)):
        p0, p1 = prices[i - 1], prices[i]
        if p0 <= 0 or p1 <= 0:
            continue
        rets.append(math.log(p1 / p0))
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    return sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)


def collect_pairs(scenario_dir):
    summary = os.path.join(scenario_dir, "mc_summary.csv")
    if not os.path.exists(summary):
        return []
    rho_by_seed = {}
    with open(summary) as f:
        for row in csv.DictReader(f):
            try:
                rho_by_seed[int(float(row["seed"]))] = float(row["lag1_autocorr"])
            except (TypeError, ValueError, KeyError):
                pass
    pairs = []
    for entry in sorted(os.listdir(scenario_dir)):
        if not entry.startswith("seed_"):
            continue
        try:
            seed = int(entry.split("_", 1)[1])
        except ValueError:
            continue
        rho = rho_by_seed.get(seed)
        if rho is None:
            continue
        ph = os.path.join(scenario_dir, entry, "price_history.csv")
        if not os.path.exists(ph):
            continue
        var_r = log_return_variance(ph)
        if var_r is None:
            continue
        pairs.append((rho, var_r))
    return pairs


def main():
    values = []
    all_pairs = []
    for scen in SCENARIOS:
        path = os.path.join("out/mc", scen, "mc_summary.csv")
        if os.path.exists(path):
            values.extend(read_column(path, "lag1_autocorr"))
        all_pairs.extend(collect_pairs(os.path.join("out/mc", scen)))

    n = len(values)
    mean = sum(values) / n

    t, p_t_two = stats.ttest_1samp(values, 0.0)
    p_t = p_t_two / 2 if t < 0 else 1 - p_t_two / 2

    w, p_w = stats.wilcoxon(values, alternative="less")

    print(f"n             = {n}")
    print(f"mean ρ₁       = {mean:+.4f}")
    print(f"Welch t       = {t:+.4f}   p (one-sided, ρ1<0) = {p_t:.2e}")
    print(f"Wilcoxon W    = {w:.1f}     p (one-sided)       = {p_w:.2e}")

    spreads = []
    for rho, var_r in all_pairs:
        if rho < 0 and var_r > 0:
            spreads.append(2.0 * math.sqrt(-rho * var_r))
    if spreads:
        mean_spread = sum(spreads) / len(spreads)
        print()
        print(f"Roll-implied effective spread) = {mean_spread:.4f}")
        print(f"configured floor spread (cfg.MM_BASE_SPREAD)                  = {cfg.MM_BASE_SPREAD:.4f}")
        ratio = mean_spread / cfg.MM_BASE_SPREAD
        print(f"ratio (Roll / floor)                                          = {ratio:.3f}")
    else:
        print("\n no data")

    print()
    if p_t < 0.05 and p_w < 0.05 and mean < 0:
        print("H1 accepted")
    else:
        print("H1 not accepted")


if __name__ == "__main__":
    main()
