import os

from agents.noise_trader import NoiseTrader
from agents.market_maker import MarketMaker
from agents.informed_trader import InformedTrader
from agents.fundamental import FundamentalTrader
from utils.plotting import plot_price_series
from utils.plotting import plot_options_prices
import config as cfg
from utils import file_io
from utils import random_utils as ru
from environment.market import Market
from agents.trend_trader import TrendTrader
from environment.options_market import OptionsMarket
from agents.options_market_maker import OptionsMarketMaker
from agents.options_noise_trader import OptionsNoiseTrader
from agents.options_arbitrageur import OptionsArbitrageur
from utils.logger import Logger
from utils.vol_utils import rolling_mean, realised_vol_last
from utils.plotting import plot_realised_vol
from utils import bs_utils
from utils import plotting
from utils.bs_utils import print_iv_rv_summary


def _path(out_dir, name):
    if out_dir is None:
        return name
    return os.path.join(out_dir, name)


def run(out_dir=None, enable_console=True):
    if out_dir is not None:
        os.makedirs(out_dir, exist_ok=True)

    agents = []

    for i in range(cfg.NUM_NOISE_TRADERS):
        my_noise = ru.uniform(cfg.NOISE_LEVEL_MIN, cfg.NOISE_LEVEL_MAX)
        agents.append(NoiseTrader(id=i + 1, noise_level=my_noise))

    for i in range(cfg.NUM_MARKET_MAKERS):
        my_risk_aversion = ru.uniform(cfg.MM_RISK_AVERSION_MIN, cfg.MM_RISK_AVERSION_MAX)
        my_vol_sens = ru.uniform(cfg.MM_VOL_SENS_MIN, cfg.MM_VOL_SENS_MAX)
        agents.append(MarketMaker(
            id=cfg.NUM_NOISE_TRADERS + i + 1,
            base_spread=cfg.MM_BASE_SPREAD,
            inventory_risk_aversion=my_risk_aversion,
            max_inventory=cfg.MM_MAX_INVENTORY,
            base_size=cfg.MM_BASE_SIZE,
            vol_sens=my_vol_sens,
        ))

    for i in range(cfg.NUM_INFORMED_TRADERS):
        my_sensitivity = ru.uniform(cfg.INFORMED_SENSITIVITY_MIN, cfg.INFORMED_SENSITIVITY_MAX)
        my_signal_noise = ru.uniform(cfg.INFORMED_SIGNAL_NOISE_MIN, cfg.INFORMED_SIGNAL_NOISE_MAX)
        agents.append(InformedTrader(
            id=cfg.NUM_NOISE_TRADERS + cfg.NUM_MARKET_MAKERS + i + 1,
            sensitivity=my_sensitivity,
            aggressiveness=cfg.INFORMED_TRADER_AGGRESSIVENESS,
            signal_noise_sigma=my_signal_noise,
        ))

    for i in range(cfg.NUM_TREND_TRADERS):
        my_lookback = ru.randint(cfg.TREND_LOOKBACK_MIN, cfg.TREND_LOOKBACK_MAX)
        agents.append(TrendTrader(
            id=cfg.NUM_NOISE_TRADERS
               + cfg.NUM_MARKET_MAKERS
               + cfg.NUM_INFORMED_TRADERS
               + i + 1,
            lookback=my_lookback,
        ))

    for i in range(cfg.NUM_FUNDAMENTAL_TRADERS):
        my_f_bias = ru.gauss(0.0, cfg.FUNDAMENTAL_F_NOISE_SIGMA)
        agents.append(FundamentalTrader(
            id=cfg.NUM_NOISE_TRADERS
               + cfg.NUM_MARKET_MAKERS
               + cfg.NUM_INFORMED_TRADERS
               + cfg.NUM_TREND_TRADERS
               + i + 1,
            fundamental_price=cfg.INITIAL_PRICE,
            aggressiveness=cfg.FUNDAMENTAL_TRADER_AGGRESSIVENESS,
            f_bias=my_f_bias,
        ))

    logger = Logger(enable_console=enable_console)

    market = Market(initial_price=cfg.INITIAL_PRICE)
    market.logger = logger
    market.set_agents(agents)

    options_market = OptionsMarket(
        strikes=cfg.OPTION_STRIKES,
        tau=cfg.OPTION_TAU,
        r=cfg.OPTION_R,
        q=cfg.OPTION_Q,
        vol=cfg.OPTION_VOL
    )
    options_market.logger = logger

    options_agents = []
    for i in range(cfg.NUM_OPTION_MARKET_MAKERS):
        options_agents.append(OptionsMarketMaker(
            id=1000 + i + 1,
        ))

    for i in range(cfg.NUM_OPTION_NOISE_TRADERS):
        options_agents.append(OptionsNoiseTrader(
            id=2000 + i + 1,
        ))

    for i in range(cfg.NUM_OPTION_ARB):
        options_agents.append(OptionsArbitrageur(
            id=3000 + i + 1,
        ))

    options_market.set_agents(options_agents)


    for a in options_agents:
        market.order_book.agents[a.id] = a

    price_history = []
    trades = []
    option_trades = []
    option_price_history_call = []
    option_price_history_put = []
    rv_history = []
    iv_history_call = []
    iv_history_put = []
    news_history = []

    for t in range(cfg.WARMUP_STEPS):
        market.step(t, agents)

    for t in range(cfg.WARMUP_STEPS, cfg.WARMUP_STEPS + cfg.NUM_STEPS):
        step_trades = market.step(t, agents)

        if enable_console:
            print(f"[Time {t}] News: {market.news:.2f}")
            print(f"Mid price: {market.mid_price:.2f}\n")

        for tr in step_trades:
            tr['time'] = t
        trades.extend(step_trades)

        S = market.mid_price
        price_history.append(S)
        news_history.append(float(market.news))

        rv = realised_vol_last(price_history, lookback=200, annualization=252)
        rv_history.append(rv)

        vol_for_options = rv if rv is not None else cfg.OPTION_VOL

        opt_trades, spot_trades_from_options = options_market.step(
            t=t,
            S=S,
            agents=options_agents,
            vol=vol_for_options,
            spot_order_book=market.order_book,
        )

        # Спотовые сделки от дельта-хеджа и опционных агентов тоже учитываем
        trades.extend(spot_trades_from_options)

        # Пересчитываем mid после спотовых ордеров опционных агентов
        market.mid_price = market.order_book.get_mid_price(last_price=market.mid_price)
        S = market.mid_price

        option_price_history_call.append(options_market.mid_prices_call.copy())
        option_price_history_put.append(options_market.mid_prices_put.copy())

        iv_step_call = {}
        iv_step_put = {}

        for K in cfg.OPTION_STRIKES:
            C_mid = options_market.mid_prices_call.get(K)
            P_mid = options_market.mid_prices_put.get(K)

            current_tau = options_market.tau
            iv_step_call[K] = bs_utils.implied_volatility(
                price=C_mid, S=S, K=K,
                r=cfg.OPTION_R, q=cfg.OPTION_Q, T=current_tau,
                option_type='call'
            )
            iv_step_put[K] = bs_utils.implied_volatility(
                price=P_mid, S=S, K=K,
                r=cfg.OPTION_R, q=cfg.OPTION_Q, T=current_tau,
                option_type='put'
            )

        iv_history_call.append(iv_step_call)
        iv_history_put.append(iv_step_put)

        option_trades.extend(opt_trades)

        for tr in opt_trades:
            logger.log_option_trade(t, tr)

    print_iv_rv_summary(
        rv_history=rv_history,
        iv_history_call=iv_history_call,
        iv_history_put=iv_history_put,
        strikes=cfg.OPTION_STRIKES
    )

    agent_type_map = {}
    for a in agents:
        agent_type_map[a.id] = a.__class__.__name__
    for a in options_agents:
        agent_type_map[a.id] = a.__class__.__name__

    from collections import Counter
    spot_trade_counts = Counter()
    for tr in trades:
        spot_trade_counts[agent_type_map.get(tr['buyer'], 'Unknown')] += 1
        spot_trade_counts[agent_type_map.get(tr['seller'], 'Unknown')] += 1

    print(f"\nTotal spot trades: {len(trades)}")
    print("Spot trades by agent type (buyer + seller):")
    for agent_type, count in spot_trade_counts.most_common():
        print(f"  {agent_type}: {count}")

    option_trade_counts = Counter()
    for tr in option_trades:
        option_trade_counts[agent_type_map.get(tr.get('buyer'), 'Unknown')] += 1
        option_trade_counts[agent_type_map.get(tr.get('seller'), 'Unknown')] += 1

    print(f"\nTotal option trades: {len(option_trades)}")
    print("Option trades by agent type (as buyer + seller):")
    for agent_type, count in option_trade_counts.most_common():
        print(f"  {agent_type}: {count}")

    rv_avg = rolling_mean(rv_history, window=200)
    plot_realised_vol(rv_history, rv_avg, title="Spot realised vol + rolling average")

    plotting.plot_implied_vol_series(iv_history_call, strikes=cfg.OPTION_STRIKES, title="Implied Vol (Calls)")
    plotting.plot_implied_vol_series(iv_history_put, strikes=cfg.OPTION_STRIKES, title="Implied Vol (Puts)")

    plot_price_series(price_history)
    plot_options_prices(option_price_history_call, strikes=cfg.OPTION_STRIKES, title='Call Options Prices')
    plot_options_prices(option_price_history_put, strikes=cfg.OPTION_STRIKES, title='Put Options Prices')


    file_io.save_price_history(_path(out_dir, 'price_history.csv'), price_history)
    file_io.save_trades(_path(out_dir, 'trades.csv'), trades)
    file_io.save_trades(_path(out_dir, 'option_trades.csv'), option_trades)

    file_io.save_wide_series_csv(_path(out_dir, 'option_mid_call.csv'), option_price_history_call, index_name='t')
    file_io.save_wide_series_csv(_path(out_dir, 'option_mid_put.csv'), option_price_history_put, index_name='t')

    file_io.save_wide_series_csv(_path(out_dir, 'iv_call.csv'), iv_history_call, index_name='t')
    file_io.save_wide_series_csv(_path(out_dir, 'iv_put.csv'), iv_history_put, index_name='t')

    file_io.save_series_csv(_path(out_dir, "news_history.csv"), news_history, colname="news")

    return {
        "price_history": price_history,
        "trades": trades,
        "option_trades": option_trades,
        "rv_history": rv_history,
        "iv_history_call": iv_history_call,
        "iv_history_put": iv_history_put,
        "news_history": news_history,
    }


def main():
    run()


if __name__ == "__main__":
    main()
