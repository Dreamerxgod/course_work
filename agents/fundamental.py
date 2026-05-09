from agents.base_agent import Agent
import config as cfg
import random


class FundamentalTrader(Agent):
    def __init__(self, id, fundamental_price=100, aggressiveness=cfg.FUNDAMENTAL_TRADER_AGGRESSIVENESS, order_prob = cfg.FUNDAMENTAL_TRADER_ORDER_PROB):
        super().__init__(id)
        self.fundamental_price = fundamental_price
        self.aggressiveness = aggressiveness
        self.order_prob = order_prob


    def act(self, market_state):
        mid = market_state['mid_price']
        self.fundamental_price = market_state['fundamental_price']

        if random.random() > self.order_prob:
            return []

        deviation = self.fundamental_price - mid
        side = 'buy' if deviation > 0 else 'sell'

        # price = mid + deviation * 0.5
        price = mid + deviation/abs(deviation + 0.0000001)*0.95
        qty = max(1, int(abs(deviation) / self.aggressiveness))
        return [{
            'agent_id': self.id,
            'instrument': 'spot',
            'order_type': 'limit',
            'side': side,
            'price': float(price),
            'qty': int(qty),
        }]

