import math
from collections import deque

from environment.order_book import OrderBook
from environment.news_process import NewsProcess
import config as cfg
from utils.logger import Logger
from utils import random_utils as ru
from environment.fundamentalistpriceprocess import FundamentalPriceProcess


class Market:
    def __init__(self, initial_price=100.0,
                 news_persistence=cfg.NEWS_PERSISTENCE,
                 news_shock_probability=cfg.NEWS_SHOCK_PROBABILITY,
                 news_shock_sigma=cfg.NEWS_SHOCK_SIGMA,
                 fundamental_mu=cfg.FUNDAMENTAL_MU,
                 fundamental_vol=cfg.FUNDAMENTAL_VOL,
                 steps_per_year=cfg.STEPS_PER_YEAR,
                 vol_window=200,
                 ):
        self.fundamental_price = initial_price
        self.mid_price = initial_price
        self.order_book = OrderBook(initial_price=initial_price)
        self.news_process = NewsProcess(persistence=news_persistence,
                                        shock_probability=news_shock_probability,
                                        shock_sigma=news_shock_sigma)
        self.news = 0.0

        self.fundamental_process = FundamentalPriceProcess(
            initial_price=initial_price,
            mu=fundamental_mu,
            sigma=fundamental_vol,
            steps_per_year=steps_per_year,
        )
        self.logger = Logger()

        self.recent_prices = deque(maxlen=vol_window + 1)
        self.recent_prices.append(initial_price)
        self.recent_vol = fundamental_vol * math.sqrt(1.0 / steps_per_year)

    def update_vol_estimate(self):
        if len(self.recent_prices) < 10:
            return
        prices = list(self.recent_prices)
        returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
        mean_r = sum(returns) / len(returns)
        var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        self.recent_vol = math.sqrt(var) if var > 0 else self.recent_vol

    def update_news(self):
        shock = self.news_process.step()
        self.news = self.news_process.get_news()
        return shock

    def get_state(self):
        return {'mid_price': self.mid_price, 'news': self.news, 'fundamental_price': self.fundamental_price}

    def get_state_for(self, agent_id):
        bb_other, ba_other = self.order_book.get_best_excluding(agent_id)
        return {
            'mid_price': self.mid_price,
            'news': self.news,
            'fundamental_price': self.fundamental_price,
            'best_bid_other': bb_other,
            'best_ask_other': ba_other,
            'recent_vol': self.recent_vol,
        }

    def set_agents(self, agents):
        self.order_book.agents = {a.id: a for a in agents}

    def step(self, t, agents):
        news_shock = self.update_news()
        self.fundamental_price = self.fundamental_process.step(news_shock=news_shock)

        self.logger.log(f"[FUNDAMENTAL t={t}] F={self.fundamental_price:.2f}")
        self.logger.log_news(t, self.news)

        self.order_book.set_time(t)
        self.order_book.expire_old(cfg.ORDER_TTL)

        trades = []
        agent_order = list(agents)
        ru.shuffle(agent_order)
        for agent in agent_order:
            per_agent_state = self.get_state_for(agent.id)
            orders = agent.act(per_agent_state)


            if orders and hasattr(agent, "inventory"):
                self.order_book.cancel_orders_for_agent(agent.id)

            for o in orders:
                self.logger.log_order(t, o, agent=agent)
                trades += self.order_book.add_order(o)

        self.mid_price = self.order_book.get_mid_price(last_price=self.mid_price)
        self.recent_prices.append(self.mid_price)
        self.update_vol_estimate()
        self.logger.log_mid_price(t, self.mid_price)

        for tr in trades:
            self.logger.log_trade(t, tr)

        return trades
