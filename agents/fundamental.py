from agents.base_agent import Agent
from utils import random_utils as ru
import config as cfg


class FundamentalTrader(Agent):
    def __init__(
        self,
        id,
        fundamental_price=100,
        aggressiveness=cfg.FUNDAMENTAL_TRADER_AGGRESSIVENESS,
        order_prob=cfg.FUNDAMENTAL_TRADER_ORDER_PROB,
        price_alpha=cfg.FUNDAMENTAL_TRADER_PRICE_ALPHA,
        max_qty=cfg.FUNDAMENTAL_TRADER_MAX_QTY,
        f_bias=0.0,
    ):
        super().__init__(id)
        self.fundamental_price = fundamental_price
        self.aggressiveness = aggressiveness
        self.order_prob = order_prob
        self.price_alpha = price_alpha
        self.max_qty = max_qty
        self.f_bias = f_bias

    def act(self, market_state):
        mid = market_state['mid_price']
        self.fundamental_price = market_state['fundamental_price'] + self.f_bias

        if ru.random() > self.order_prob:
            return []

        deviation = self.fundamental_price - mid
        if deviation == 0:
            return []
        side = 'buy' if deviation > 0 else 'sell'

        price = mid + self.price_alpha * deviation
        qty = max(1, min(self.max_qty, int(abs(deviation) / self.aggressiveness)))
        return [{
            'agent_id': self.id,
            'instrument': 'spot',
            'order_type': 'limit',
            'side': side,
            'price': float(price),
            'qty': int(qty),
        }]

