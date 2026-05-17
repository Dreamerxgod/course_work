from agents.base_agent import Agent
from utils import random_utils as ru
import config as cfg


class InformedTrader(Agent):

    def __init__(self, id,
                 sensitivity=cfg.INFORMED_TRADER_SENSITIVITY,
                 aggressiveness=cfg.INFORMED_TRADER_AGGRESSIVENESS,
                 max_qty=cfg.INFORMED_TRADER_MAX_QTY,
                 signal_noise_sigma=cfg.INFORMED_SIGNAL_NOISE_MIN,
                 trade_threshold=cfg.INFORMED_TRADE_THRESHOLD,
                 max_inventory=cfg.INFORMED_MAX_INVENTORY):
        super().__init__(id)
        self.sensitivity = sensitivity
        self.aggressiveness = aggressiveness
        self.max_qty = max_qty
        self.signal_noise_sigma = signal_noise_sigma
        self.trade_threshold = trade_threshold
        self.max_inventory = max_inventory
        self.inventory = 0

    def act(self, market_state):
        F = market_state['fundamental_price']
        mid = market_state['mid_price']

        my_F_estimate = F + ru.gauss(0.0, self.signal_noise_sigma)
        gap = my_F_estimate - mid

        if abs(gap) < self.trade_threshold:
            return []

        side = 'buy' if gap > 0 else 'sell'
        if side == 'buy':
            possible_left = self.max_inventory - self.inventory
        else:
            possible_left = self.inventory + self.max_inventory
        if possible_left <= 0:
            return []

        price = mid + 0.5 * gap
        qty = max(1, min(self.max_qty, int(abs(gap) / self.aggressiveness)))
        qty = min(qty, possible_left)

        return [{
            'agent_id': self.id,
            'instrument': 'spot',
            'order_type': 'limit',
            'side': side,
            'price': float(price),
            'qty': int(qty),
        }]
