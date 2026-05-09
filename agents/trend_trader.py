from agents.base_agent import Agent
import numpy as np
from collections import deque
import config as cfg

class TrendTrader(Agent):
    def __init__(self, id,
                 lookback=cfg.TREND_TRADER_LOOKBACK,
                 threshold=cfg.TREND_TRADER_THRESHOLD,
                 k=cfg.TREND_TRADER_AGGRESSIVENESS,
                 max_qty=cfg.TREND_TRADER_MAX_QTY):
        super().__init__(id)
        self.lookback = lookback
        self.threshold = threshold
        self.k = k
        self.max_qty = max_qty
        self.price_history = deque(maxlen=lookback)

    def atr(self):
        if len(self.price_history) < 20:
            return None
        closes = np.array(self.price_history)
        returns = np.abs(np.diff(closes))
        atr = np.mean(returns)
        return atr if atr > 0 else None

    def trend(self):
        if len(self.price_history) < 10:
            return 0
        prices = np.array(self.price_history)
        logp = np.log(prices)
        x = np.arange(len(logp))
        slope = np.polyfit(x, logp, 1)[0]
        ret = np.diff(logp)
        vol = np.std(ret) if len(ret) > 1 else 0
        if vol == 0:
            return 0
        return slope / vol

    def act(self, market_state):
        mid = market_state['mid_price']
        self.price_history.append(mid)

        trend = self.trend()
        if abs(trend) < self.threshold:
            return []

        atr = self.atr()
        if atr is None:
            return []

        side = 'buy' if trend > 0 else 'sell'

        strength = abs(trend) / (self.k * self.threshold)
        strength = max(0.0, min(1.0, strength))

        qty = 1 + int(strength * (self.max_qty - 1))

        spread = max(mid * 0.002, 2 * atr)
        price = mid - spread / 2 if side == 'buy' else mid + spread / 2

        return [{
            'agent_id': self.id,
            'instrument': 'spot',
            'order_type': 'limit',
            'side': side,
            'price': float(price),
            'qty': int(qty),
        }]

