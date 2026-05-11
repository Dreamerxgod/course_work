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
    ):
        super().__init__(id)
        self.fundamental_price = fundamental_price
        self.aggressiveness = aggressiveness
        self.order_prob = order_prob
        self.price_alpha = price_alpha

    def act(self, market_state):
        mid = market_state['mid_price']
        self.fundamental_price = market_state['fundamental_price']

        if ru.random() > self.order_prob:
            return []

        deviation = self.fundamental_price - mid
        if deviation == 0:
            return []
        side = 'buy' if deviation > 0 else 'sell'

        # Линейный value-trader: цена котировки тянется к fair value пропорционально отклонению.
        # См. Chiarella & Iori (2002), "A simulation analysis of the microstructure of double auction markets".
        price = mid + self.price_alpha * deviation
        qty = max(1, int(abs(deviation) / self.aggressiveness))
        return [{
            'agent_id': self.id,
            'instrument': 'spot',
            'order_type': 'limit',
            'side': side,
            'price': float(price),
            'qty': int(qty),
        }]

