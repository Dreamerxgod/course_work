import csv
import os

from scipy import stats

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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


def main():
    values = []
    for scen in SCENARIOS:
        path = os.path.join("out/mc", scen, "mc_summary.csv")
        if os.path.exists(path):
            values.extend(read_column(path, "lag1_autocorr"))

    n = len(values)
    mean = sum(values) / n

    t, p_t_two = stats.ttest_1samp(values, 0.0)
    p_t = p_t_two / 2 if t < 0 else 1 - p_t_two / 2

    w, p_w = stats.wilcoxon(values, alternative="less")

    print(f"n             = {n}")
    print(f"mean ρ₁       = {mean:+.4f}")
    print(f"Welch t       = {t:+.4f}   p (one-sided, ρ1<0) = {p_t:.2e}")
    print(f"Wilcoxon W    = {w:.1f}     p (one-sided)       = {p_w:.2e}")

    if p_t < 0.05 and p_w < 0.05 and mean < 0:
        print("\nH1 accepted")
    else:
        print("\nH1 not accepted")


if __name__ == "__main__":
    main()
