import math

import config as cfg
from utils import random_utils as ru


class FundamentalPriceProcess:

    def __init__(self, initial_price=100,
                 mu=cfg.FUNDAMENTAL_MU,
                 sigma=cfg.FUNDAMENTAL_VOL,
                 steps_per_year=cfg.STEPS_PER_YEAR,
                 news_impact=cfg.NEWS_IMPACT_ON_F):
        self.fundamental_price = float(initial_price)
        self.mu = mu
        self.sigma = sigma
        self.dt = 1.0 / steps_per_year
        self.drift_per_step = (mu - 0.5 * sigma * sigma) * self.dt
        self.diff_per_step = sigma * math.sqrt(self.dt)
        self.news_impact = news_impact

    def step(self, news_shock=0.0):
        z = ru.gauss(0.0, 1.0)
        log_return = self.drift_per_step + self.diff_per_step * z + self.news_impact * news_shock
        self.fundamental_price *= math.exp(log_return)
        return self.fundamental_price
