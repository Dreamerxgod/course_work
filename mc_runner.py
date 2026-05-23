import argparse
import csv
import os
import subprocess
import sys

from utils.metrics import summarize_run


def parse_args():
    p = argparse.ArgumentParser(description="Monte-Carlo runner")
    p.add_argument("--n_runs", type=int, default=30, help="число независимых прогонов")
    p.add_argument("--base_seed", type=int, default=1, help="seed первого прогона; далее base_seed+1, +2, ...")
    p.add_argument("--out_dir", type=str, required=True, help="каталог для всех прогонов и итогового summary")
    p.add_argument("--n_steps", type=int, default=None, help="override cfg.NUM_STEPS на прогоне")
    p.add_argument("--warmup", type=int, default=None, help="override cfg.WARMUP_STEPS")
    p.add_argument("--override", action="append", default=[],
                   help="параметр config")
    return p.parse_args()


def run_one(seed, run_dir, n_steps, warmup, overrides):
    cmd = [sys.executable, "runner.py", "--seed", str(seed),
           "--out_dir", run_dir, "--quiet", "--no_plots"]
    if n_steps is not None:
        cmd += ["--n_steps", str(n_steps)]
    if warmup is not None:
        cmd += ["--warmup", str(warmup)]
    for kv in overrides:
        cmd += ["--override", kv]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[mc_runner] seed={seed} FAILED:")
        print(result.stderr[-2000:])
        return None
    return summarize_run(run_dir)


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    rows = []
    for i in range(args.n_runs):
        seed = args.base_seed + i
        run_dir = os.path.join(args.out_dir, f"seed_{seed}")
        os.makedirs(run_dir, exist_ok=True)
        summary = run_one(seed, run_dir, args.n_steps, args.warmup, args.override)
        if summary is None:
            print(f"[mc_runner] seed={seed} skipped (failed)")
            continue
        summary["seed"] = seed
        rows.append(summary)
        rv = summary.get("mean_rv")
        print(f"[mc_runner] seed={seed}  mean_rv={rv:.4f}" if rv is not None else
              f"[mc_runner] seed={seed}  done")

    if not rows:
        raise SystemExit("1")

    summary_path = os.path.join(args.out_dir, "mc_summary.csv")
    keys = ["seed"] + [k for k in rows[0].keys() if k != "seed"]
    with open(summary_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    print(f"[mc_runner] saved {summary_path} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
