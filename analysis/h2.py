import csv
import os
import subprocess
import sys

from scipy import stats

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


LOW = "out/mc/h2_low_mm"
HIGH = "out/mc/h2_high_mm"
N_RUNS = 50


def ensure_mc():
    procs = []
    for path, num_mm in [(LOW, 3), (HIGH, 12)]:
        if os.path.exists(os.path.join(path, "mc_summary.csv")):
            continue
        procs.append(subprocess.Popen([
            sys.executable, "mc_runner.py",
            "--n_runs", str(N_RUNS), "--base_seed", "1",
            "--out_dir", path,
            "--override", f"NUM_MARKET_MAKERS={num_mm}",
        ]))
    for p in procs:
        p.wait()


def read_column(path, col):
    out = []
    with open(path) as f:
        for row in csv.DictReader(f):
            try:
                out.append(float(row[col]))
            except (TypeError, ValueError, KeyError):
                pass
    return out


def test_metric(metric, low_path=None, high_path=None, label_low="low", label_high="high"):
    low_path = low_path or LOW
    high_path = high_path or HIGH
    a = read_column(os.path.join(low_path, "mc_summary.csv"), metric)
    b = read_column(os.path.join(high_path, "mc_summary.csv"), metric)

    if not a or not b:
        print(f"\n{metric}: missing data (low n={len(a)}, high n={len(b)})")
        return False

    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)

    t, p_t_two = stats.ttest_ind(a, b, equal_var=False)
    p_t = p_t_two / 2 if t > 0 else 1 - p_t_two / 2

    u, p_u = stats.mannwhitneyu(a, b, alternative="greater")

    rel = (mean_a - mean_b) / mean_a * 100 if mean_a else float("nan")

    print(f"\n{metric}")
    print(f"  {label_low}  mean = {mean_a:.4f}  (n={len(a)})")
    print(f"  {label_high} mean = {mean_b:.4f}  (n={len(b)})")
    print(f"  diff ({label_low} - {label_high}) = {mean_a - mean_b:+.4f}   ({rel:+.2f}%)")
    print(f"  Welch t      = {t:+.4f}   p (one-sided, {label_low}>{label_high}) = {p_t:.5f}")
    print(f"  Mann-Whitney = {u:.1f}      p (one-sided)            = {p_u:.5f}")

    return p_t < 0.05 and p_u < 0.05


def main():
    ensure_mc()
    ok_rv = test_metric("mean_rv")
    ok_eff = test_metric("mean_distance_from_F")

    print()
    if ok_rv and ok_eff:
        print("H2 accepted")
    else:
        print("partially accepted")


if __name__ == "__main__":
    main()
