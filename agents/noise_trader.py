from agents.base_agent import Agent
from utils import random_utils as ru
import config as cfg


class NoiseTrader(Agent):

    def __init__(self, id,
                 noise_level=cfg.NOISE_TRADER_NOISE_LEVEL,
                 order_prob=cfg.NOISE_ORDER_PROB,
                 max_inventory=cfg.NOISE_MAX_INVENTORY,
                 market_order_prob=cfg.NOISE_MARKET_PROB):
        super().__init__(id)
        self.noise_level = noise_level
        self.order_prob = order_prob
        self.max_inventory = max_inventory
        self.market_order_prob = market_order_prob
        self.inventory = 0

    def act(self, market_state):
        mid = market_state['mid_price']

        if ru.random() > self.order_prob:
            return []

        inv_frac = self.inventory / self.max_inventory
        inv_frac = max(-1.0, min(1.0, inv_frac))
        buy_prob = 0.5 - 0.5 * inv_frac
        side = 'buy' if ru.random() < buy_prob else 'sell'

        if side == 'buy':
            possible_left = self.max_inventory - self.inventory
        else:
            possible_left = self.inventory + self.max_inventory
        if possible_left <= 0:
            return []

        qty = min(ru.randint(1, 5), possible_left)

        if ru.random() < self.market_order_prob:
            return [{
                'agent_id': self.id,
                'instrument': 'spot',
                'order_type': 'market',
                'side': side,
                'qty': int(qty),
            }]

        price = mid * (1 + ru.uniform(-self.noise_level, self.noise_level))
        return [{
            'agent_id': self.id,
            'instrument': 'spot',
            'order_type': 'limit',
            'side': side,
            'price': float(price),
            'qty': int(qty),
        }]
