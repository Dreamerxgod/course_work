from agents.base_agent import Agent
import config as cfg


class InformedTrader(Agent):
    def __init__(self, id,
                 sensitivity=cfg.INFORMED_TRADER_SENSITIVITY,
                 aggressiveness=cfg.INFORMED_TRADER_AGGRESSIVENESS,
                 max_qty=cfg.INFORMED_TRADER_MAX_QTY):
        super().__init__(id)
        self.sensitivity = sensitivity
        self.aggressiveness = aggressiveness
        self.max_qty = max_qty

    def act(self, market_state):
        mid = market_state['mid_price']
        news = market_state['news']
        news = float(news)
        if news == 0:
            return []

        price = mid * (1 + self.sensitivity * news)
        side = 'buy' if news > 0 else 'sell'
        qty = max(1, min(self.max_qty, int(abs(news) / self.aggressiveness)))
        return [{
            'agent_id': self.id,
            'instrument': 'spot',
            'order_type': 'limit',
            'side': side,
            'price': float(price),
            'qty': int(qty),
        }]


