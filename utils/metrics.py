import config as cfg
import scipy.stats as stats
from agents.noise_trader import NoiseTrader
from agents.market_maker import MarketMaker
from agents.informed_trader import InformedTrader
from agents.fundamental import FundamentalTrader
from agents.trend_trader import TrendTrader
from environment.market import Market
from environment.options_market import OptionsMarket
from agents.options_market_maker import OptionsMarketMaker
from agents.options_noise_trader import OptionsNoiseTrader
from agents.options_arbitrageur import OptionsArbitrageur
from utils.vol_utils import realised_vol_last
from utils import bs_utils


def compute_iv_roughness(iv_history_call, iv_history_put, strikes):
    roughness_call = []
    roughness_put = []
    for t in range(1, len(iv_history_call)):
        r_call = sum(abs(iv_history_call[t][K] - iv_history_call[t-1][K]) for K in strikes) / len(strikes)
        r_put = sum(abs(iv_history_put[t][K] - iv_history_put[t-1][K]) for K in strikes) / len(strikes)
        roughness_call.append(r_call)
        roughness_put.append(r_put)
    avg_rough_call = sum(roughness_call)/len(roughness_call) if roughness_call else 0
    avg_rough_put = sum(roughness_put)/len(roughness_put) if roughness_put else 0
    return avg_rough_call, avg_rough_put, roughness_call, roughness_put



def run_simulation(include_arbitrage=True):
    agents = []
    for i in range(cfg.NUM_NOISE_TRADERS):
        agents.append(NoiseTrader(id=i+1, noise_level=cfg.NOISE_TRADER_NOISE_LEVEL))
    for i in range(cfg.NUM_MARKET_MAKERS):
        agents.append(MarketMaker(
            id=cfg.NUM_NOISE_TRADERS + i + 1,
            base_spread=cfg.MM_BASE_SPREAD,
            inventory_risk_aversion=cfg.MM_INV_RISK,
            max_inventory=cfg.MM_MAX_INVENTORY,
            base_size=cfg.MM_BASE_SIZE
        ))
    for i in range(cfg.NUM_INFORMED_TRADERS):
        agents.append(InformedTrader(
            id=cfg.NUM_NOISE_TRADERS + cfg.NUM_MARKET_MAKERS + i + 1,
            sensitivity=cfg.INFORMED_TRADER_SENSITIVITY,
            aggressiveness=cfg.INFORMED_TRADER_AGGRESSIVENESS
        ))
    for i in range(cfg.NUM_TREND_TRADERS):
        agents.append(TrendTrader(
            id=cfg.NUM_NOISE_TRADERS + cfg.NUM_MARKET_MAKERS + cfg.NUM_INFORMED_TRADERS + i + 1
        ))
    for i in range(cfg.NUM_FUNDAMENTAL_TRADERS):
        agents.append(FundamentalTrader(
            id=cfg.NUM_NOISE_TRADERS + cfg.NUM_MARKET_MAKERS + cfg.NUM_INFORMED_TRADERS + cfg.NUM_TREND_TRADERS + i + 1,
            fundamental_price=cfg.INITIAL_PRICE,
            aggressiveness=cfg.FUNDAMENTAL_TRADER_AGGRESSIVENESS
        ))

    market = Market(initial_price=cfg.INITIAL_PRICE)
    market.set_agents(agents)

    options_market = OptionsMarket(
        strikes=cfg.OPTION_STRIKES,
        tau=cfg.OPTION_TAU,
        r=cfg.OPTION_R,
        q=cfg.OPTION_Q,
        vol=cfg.OPTION_VOL
    )

    options_agents = []
    for i in range(cfg.NUM_OPTION_MARKET_MAKERS):
        options_agents.append(OptionsMarketMaker(id=1000 + i + 1))
    for i in range(cfg.NUM_OPTION_NOISE_TRADERS):
        options_agents.append(OptionsNoiseTrader(id=2000 + i + 1))
    if include_arbitrage:
        for i in range(cfg.NUM_OPTION_ARB):
            options_agents.append(OptionsArbitrageur(id=3000 + i + 1))

    options_market.set_agents(options_agents)

    price_history = []
    iv_history_call = []
    iv_history_put = []

    for t in range(cfg.WARMUP_STEPS):
        market.step(t, agents)

    for t in range(cfg.WARMUP_STEPS, cfg.WARMUP_STEPS + cfg.NUM_STEPS):
        market.step(t, agents)
        S = market.mid_price
        price_history.append(S)
        rv = realised_vol_last(price_history, lookback=200, annualization=252)
        vol_for_options = rv if rv is not None else cfg.OPTION_VOL

        options_market.step(t=t, S=S, agents=options_agents, vol=vol_for_options, spot_order_book=market.order_book)

        iv_step_call = {}
        iv_step_put = {}
        for K in cfg.OPTION_STRIKES:
            C_mid = options_market.mid_prices_call.get(K)
            P_mid = options_market.mid_prices_put.get(K)
            iv_step_call[K] = bs_utils.implied_volatility(price=C_mid, S=S, K=K, r=cfg.OPTION_R, q=cfg.OPTION_Q, T=cfg.OPTION_TAU, option_type='call')
            iv_step_put[K] = bs_utils.implied_volatility(price=P_mid, S=S, K=K, r=cfg.OPTION_R, q=cfg.OPTION_Q, T=cfg.OPTION_TAU, option_type='put')
        iv_history_call.append(iv_step_call)
        iv_history_put.append(iv_step_put)

    avg_rough_call, avg_rough_put, rough_call, rough_put = compute_iv_roughness(iv_history_call, iv_history_put, cfg.OPTION_STRIKES)
    return avg_rough_call, avg_rough_put, rough_call, rough_put


def main():
    avg_rough_call_arb, avg_rough_put_arb, rough_call_arb, rough_put_arb = run_simulation(include_arbitrage=True)
    avg_rough_call_noarb, avg_rough_put_noarb, rough_call_noarb, rough_put_noarb = run_simulation(include_arbitrage=False)

    t_stat_call, p_val_call = stats.ttest_ind(rough_call_arb, rough_call_noarb, equal_var=False)
    t_stat_put, p_val_put = stats.ttest_ind(rough_put_arb, rough_put_noarb, equal_var=False)

    print("=== IV Roughness Test ===")
    print("Average IV roughness (calls) with arb:", avg_rough_call_arb)
    print("Average IV roughness (calls) without arb:", avg_rough_call_noarb)
    print("Average IV roughness (puts) with arb:", avg_rough_put_arb)
    print("Average IV roughness (puts) without arb:", avg_rough_put_noarb)
    print("\nStatistical test results (t-test, unequal variance):")
    print(f"Calls: t={t_stat_call:.4f}, p={p_val_call:.4f}")
    print(f"Puts: t={t_stat_put:.4f}, p={p_val_put:.4f}")

    alpha = 0.05
    def conclusion(p, instrument):
        if p < alpha:
            print(f"Hypothesis confirmed for {instrument} (p<{alpha})")
        else:
            print(f"Hypothesis NOT confirmed for {instrument} (p>={alpha})")

    conclusion(p_val_call, "calls")
    conclusion(p_val_put, "puts")


if __name__ == "__main__":
    main()
