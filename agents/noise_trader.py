from agents.base_agent import Agent
from utils import random_utils as ru
import config as cfg
import random

class NoiseTrader(Agent):

    def __init__(self, id, noise_level=cfg.NOISE_TRADER_NOISE_LEVEL, order_prob = cfg.NOISE_ORDER_PROB):
        super().__init__(id)
        self.noise_level = noise_level
        self.order_prob = order_prob

    def act(self, market_state):
        mid = market_state['mid_price']

        if random.random() > self.order_prob:
            return []
        price = mid * (1 + ru.uniform(-self.noise_level, self.noise_level))
        qty = ru.randint(1, 5)
        side = ru.choice(['buy', 'sell'])

        return [{
            'agent_id': self.id,
            'instrument': 'spot',
            'order_type': 'limit',
            'side': side,
            'price': float(price),
            'qty': int(qty),
        }]

