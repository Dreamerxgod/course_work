import csv
import os
import subprocess
import sys
from collections import defaultdict, deque

from scipy import stats

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# allow `from h2 import test_metric`
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h2 import test_metric  # noqa: E402


LOW = "out/mc/low_info"
HIGH = "out/mc/high_info"
N_RUNS = 50
MM_IDS = set(range(6, 12))


def needs_full_run(path):
    summary = os.path.join(path, "mc_summary.csv")
    if not os.path.exists(summary):
        return True
    # check that columns + trades.csv per seed are present
    with open(summary) as f:
        header = f.readline().strip().split(",")
    if "mean_distance_from_F" not in header:
        return True
    seed_dirs = [d for d in os.listdir(path) if d.startswith("seed_")]
    if not seed_dirs:
        return True
    sample = os.path.join(path, seed_dirs[0], "trades.csv")
    return not os.path.exists(sample)


def ensure_mc():
    procs = []
    for path, num_inf in [(LOW, 2), (HIGH, 20)]:
        if not needs_full_run(path):
            continue
        print(f"[h3] running MC for {path} (NUM_INFORMED_TRADERS={num_inf})")
        procs.append(subprocess.Popen([
            sys.executable, "mc_runner.py",
            "--n_runs", str(N_RUNS), "--base_seed", "1",
            "--out_dir", path,
            "--override", f"NUM_INFORMED_TRADERS={num_inf}",
        ]))
    for p in procs:
        p.wait()


def get_final_price(seed_dir):
    path = os.path.join(seed_dir, "price_history.csv")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    return float(rows[-1]["price"])


def mm_pnl_with_mtm(trades_path, final_price):
    inv = defaultdict(deque)
    pnl = defaultdict(float)

    rows = list(csv.DictReader(open(trades_path)))
    rows.sort(key=lambda x: int(x["time"]))

    for r in rows:
        p, q = float(r["price"]), float(r["qty"])
        b, s = int(float(r["buyer"])), int(float(r["seller"]))
        for who, sign in [(b, +1), (s, -1)]:
            if who not in MM_IDS:
                continue
            rem = q
            qu = inv[who]
            while rem > 0 and qu and qu[0][1] != sign:
                op, os_, oq = qu[0]
                cq = min(rem, oq)
                pnl[who] += (p - op) * cq * os_
                if cq == oq:
                    qu.popleft()
                else:
                    qu[0] = (op, os_, oq - cq)
                rem -= cq
            if rem > 0:
                qu.append([p, sign, rem])

    for who, qu in inv.items():
        for entry_price, sign, qty in qu:
            pnl[who] += sign * qty * (final_price - entry_price)

    return sum(pnl.values())


def collect_pnls(scenario_dir):
    pnls = []
    for entry in sorted(os.listdir(scenario_dir)):
        if not entry.startswith("seed_"):
            continue
        seed_dir = os.path.join(scenario_dir, entry)
        trades = os.path.join(seed_dir, "trades.csv")
        if not os.path.exists(trades):
            continue
        fp = get_final_price(seed_dir)
        if fp is None:
            continue
        pnls.append(mm_pnl_with_mtm(trades, fp))
    return pnls


def test_pnl():
    a = collect_pnls(LOW)
    b = collect_pnls(HIGH)
    if not a or not b:
        print("\n missing")
        return False

    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)

    t, p_t_two = stats.ttest_ind(a, b, equal_var=False)
    p_t = p_t_two / 2 if t > 0 else 1 - p_t_two / 2
    u, p_u = stats.mannwhitneyu(a, b, alternative="greater")

    rel = (mean_a - mean_b) / mean_a * 100 if mean_a else float("nan")

    print("\nmm_pnl")
    print(f"  low_info  (N_inf=2)  mean = {mean_a:+.2f}  (n={len(a)})")
    print(f"  high_info (N_inf=20) mean = {mean_b:+.2f}  (n={len(b)})")
    print(f"  diff (low - high)        = {mean_a - mean_b:+.2f}   ({rel:+.2f}%)")
    print(f"  Welch t  = {t:+.4f}   p (one-sided, low>high) = {p_t:.5f}")
    print(f"  Mann-Whitney = {u:.1f}     p (one-sided)            = {p_u:.5f}")

    return p_t < 0.05 and p_u < 0.05 and mean_a > mean_b


def main():
    ensure_mc()

    # H3
    ok_rv = test_metric("mean_rv", LOW, HIGH,
                        label_low="low_info", label_high="high_info")

    # H3 (a)
    ok_eff = test_metric("mean_distance_from_F", LOW, HIGH,
                         label_low="low_info", label_high="high_info")

    # H3 (b)
    ok_pnl = test_pnl()

    print()
    if ok_rv and ok_eff and ok_pnl:
        print("H3 accepted on all three")
    else:
        bad = [name for name, ok in
               [("RV", ok_rv), ("efficiency", ok_eff), ("MM PnL", ok_pnl)]
               if not ok]
        print(f"H3 partial — failed on: {', '.join(bad)}")


if __name__ == "__main__":
    main()
