import csv
import os
from collections import defaultdict, deque

from scipy import stats

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


LOW = "out/mc/h1p_low"
HIGH = "out/mc/h1p_high"
MM_IDS = set(range(6, 12))


def realized_mm_pnl(trades_path):
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
    return sum(pnl.values())


def collect_pnls(scenario_dir):
    pnls = []
    for entry in sorted(os.listdir(scenario_dir)):
        if not entry.startswith("seed_"):
            continue
        trades = os.path.join(scenario_dir, entry, "trades.csv")
        if os.path.exists(trades):
            pnls.append(realized_mm_pnl(trades))
    return pnls


def main():
    a = collect_pnls(LOW)
    b = collect_pnls(HIGH)
    mean_a = sum(a) / len(a)
    mean_b = sum(b) / len(b)

    t, p_t_two = stats.ttest_ind(a, b, equal_var=False)
    p_t = p_t_two / 2 if t > 0 else 1 - p_t_two / 2
    u, p_u = stats.mannwhitneyu(a, b, alternative="greater")

    print("mean_mm_pnl (realized, FIFO)")
    print(f"  low_info  (N_inf=2)  mean = {mean_a:+.2f}  (n={len(a)})")
    print(f"  high_info (N_inf=20) mean = {mean_b:+.2f}  (n={len(b)})")
    print(f"  diff (low − high)         = {mean_a - mean_b:+.2f}")
    print(f"  Welch t  = {t:+.4f}   p (one-sided, low>high) = {p_t:.5f}")
    print(f"  Mann-Whitney U = {u:.1f}      p (one-sided)       = {p_u:.5f}")

    print()
    if p_t < 0.05 and p_u < 0.05 and mean_a > mean_b:
        print("H3 accepted")
    else:
        print("H3 not accepted")


if __name__ == "__main__":
    main()
