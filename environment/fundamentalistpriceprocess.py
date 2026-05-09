import random
import config as cfg

class FundamentalPriceProcess:
    def __init__(self, initial_price=100, drift=cfg.FUNDAMENTAL_DRIFT, step_interval=cfg.FUNDAMENTAL_INTERVAL):
        self.fundamental_price = initial_price
        self.drift = drift
        self.step_interval = step_interval
        self.counter = 0

    def step(self):
        self.counter += 1

        if self.counter >= self.step_interval:
            self.counter = 0
            self.fundamental_price += random.gauss(self.drift, cfg.FUNDAMENTAL_SIGMA)

        return self.fundamental_price
