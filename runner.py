"""
    python runner.py --seed 42 --n_steps 3000
    python runner.py --seed 1 --n_steps 1000 --out_dir out/quick --no_plots
    python runner.py --seed 1 --n_steps 500 --warmup 20 --quiet
"""
import argparse
import json
import os
from datetime import datetime

# Matplotlib переводим в неинтерактивный режим ДО импорта main,
# чтобы plt.show() не блокировал и фигуры писались в файл.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config as cfg
from utils import random_utils as ru


_fig_counter = [0]
_fig_out_dir = [None]


def _save_show():
    _fig_counter[0] += 1
    fname = f"fig_{_fig_counter[0]:03d}.png"
    out = _fig_out_dir[0]
    path = os.path.join(out, fname) if out else fname
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()


def parse_args():
    p = argparse.ArgumentParser(description="ABM simulation runner")
    p.add_argument("--seed", type=int, default=None,
                   help="random seed (None = недетерминированно)")
    p.add_argument("--n_steps", type=int, default=None,
                   help="число основных шагов (override cfg.NUM_STEPS)")
    p.add_argument("--warmup", type=int, default=None,
                   help="warm-up шаги (override cfg.WARMUP_STEPS)")
    p.add_argument("--out_dir", type=str, default=None,
                   help="каталог для артефактов")
    p.add_argument("--no_plots", action="store_true",
                   help="не сохранять графики (только CSV)")
    p.add_argument("--quiet", action="store_true",
                   help="отключить per-step console output")
    return p.parse_args()


def make_run_id(seed):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    seed_part = f"seed{seed}" if seed is not None else "seednone"
    return f"{ts}_{seed_part}"


def main():
    args = parse_args()

    if args.n_steps is not None:
        cfg.NUM_STEPS = args.n_steps
    if args.warmup is not None:
        cfg.WARMUP_STEPS = args.warmup
    if args.seed is not None:
        cfg.SEED = args.seed

    ru.set_seed(cfg.SEED)

    out_dir = args.out_dir or os.path.join("out", make_run_id(cfg.SEED))
    os.makedirs(out_dir, exist_ok=True)
    _fig_out_dir[0] = out_dir

    if args.no_plots:
        plt.show = lambda *a, **kw: plt.close()
    else:
        plt.show = _save_show

    snapshot = {
        k: getattr(cfg, k) for k in dir(cfg)
        if not k.startswith("_") and isinstance(getattr(cfg, k), (int, float, str, list, tuple, type(None)))
    }
    with open(os.path.join(out_dir, "config_snapshot.json"), "w") as f:
        json.dump(snapshot, f, indent=2, default=str)

    from main import run
    print(f"[runner] seed={cfg.SEED} n_steps={cfg.NUM_STEPS} warmup={cfg.WARMUP_STEPS} out_dir={out_dir}")
    result = run(out_dir=out_dir, enable_console=not args.quiet)
    print(f"[runner] done. {len(result['price_history'])} price points, "
          f"{len(result['trades'])} spot trades, "
          f"{len(result['option_trades'])} option trades.")


if __name__ == "__main__":
    main()
