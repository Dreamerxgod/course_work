# Dynamic Finance System Modeling Using Agent-Based Approach

Agent-based model of a financial market with a spot instrument and European options on it. Used to test three empirical hypotheses by Monte Carlo simulation.

## Requirements

```bash
pip install -r requirements.txt
```

Python 3.10+.

## Single run

```bash
python runner.py --seed 42
```

Options:
- `--seed N` — random seed (default: from `config.SEED`)
- `--n_steps N` — number of simulation steps
- `--warmup N` — warm-up steps before measurement
- `--out_dir DIR` — directory for artifacts (default: `out/<timestamp>_seed<N>`)
- `--no_plots` — skip figure generation
- `--quiet` — disable per-step console output
- `--override KEY=VAL` — override any parameter from `config.py`

Output artifacts: `price_history.csv`, `fundamental_history.csv`, `news_history.csv`, `rv_history.csv`, `option_mid_call.csv`, `option_mid_put.csv`, `iv_call.csv`, `iv_put.csv`, `trades.csv`, `option_trades.csv`, `mm_inventory.csv`, `config_snapshot.json`.

## Monte Carlo

```bash
python mc_runner.py --n_runs 50 --base_seed 1 --out_dir out/mc/my_scenario
```

Add `--override NUM_MARKET_MAKERS=12` to override parameters per scenario.

Produces `mc_summary.csv` with one row per seed.

## Hypothesis testing

```bash
python analysis/h1.py
python analysis/h2.py
python analysis/h3.py
```

- `h1.py` — Bid-ask bounce: tests $\rho_1 < 0$ across all scenarios.
- `h2.py` — Liquidity provision: contrasts `h2_low_mm` vs `h2_high_mm` on RV and $\overline{|S-F|}$.
- `h3.py` — Information aggregation: contrasts `low_info` vs `high_info` on RV, $\overline{|S-F|}$, MM PnL.

`h2.py` and `h3.py` will automatically run the required MC if `mc_summary.csv` is missing.

## Project structure

```
agents/         agent classes (NoiseTrader, MarketMaker, InformedTrader, etc.)
environment/    order book, matching engine, fundamental and news processes
utils/          Black-Scholes, RNG, logging, plotting, file I/O
analysis/       hypothesis tests (h1.py, h2.py, h3.py)
config.py       all simulation parameters
runner.py       single-run CLI
mc_runner.py    Monte Carlo orchestrator
main.py         simulation core
```

## Reproducibility

All randomness is routed through `utils/random_utils.py` with a single seed. Two runs with the same seed and configuration produce identical trajectories. Cross-scenario comparisons use matched seeds.
