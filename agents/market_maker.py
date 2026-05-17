import math

from agents.base_agent import Agent
import config as cfg


class MarketMaker(Agent):

    def __init__(
        self,
        id,
        base_spread=cfg.MM_BASE_SPREAD,
        inventory_risk_aversion=cfg.MM_INV_RISK,
        max_inventory=cfg.MM_MAX_INVENTORY,
        base_size=cfg.MM_BASE_SIZE,
        requote_threshold=cfg.MM_REQUOTE_THRESHOLD,
        max_quote_age=cfg.MM_MAX_QUOTE_AGE,
        passive_offset=cfg.PASSIVE_OFFSET,
        time_horizon=cfg.MM_TIME_HORIZON,
        order_intensity_k=cfg.MM_ORDER_INTENSITY_K,
        vol_sens=cfg.MM_VOL_SENS,
    ):
        super().__init__(id)
        self.inventory = 0
        self.max_inventory = max_inventory
        self.base_spread = base_spread
        self.gamma = inventory_risk_aversion
        self.base_size = base_size
        self.requote_threshold = requote_threshold
        self.max_quote_age = max_quote_age
        self.passive_offset = passive_offset
        self.T = time_horizon
        self.k = order_intensity_k
        self.vol_sens = vol_sens

        self.last_quoted_mid = None
        self.tick_since_quote = 0

    def compute_reservation_and_spread(self, mid, sigma):
        reservation = mid - self.inventory * self.gamma * (sigma**2) * self.T
        inv_risk_term = 0.5 * self.gamma * (sigma**2) * self.T
        if self.k > 0:
            intensity_term = (1.0 / self.gamma) * math.log(1.0 + self.gamma / self.k)
        else:
            intensity_term = 0.0
        half_spread = (inv_risk_term + intensity_term) * self.vol_sens
        half_spread = max(half_spread, self.base_spread / 2)
        return reservation, half_spread

    def compute_sizes(self):
        inv_frac = self.inventory / self.max_inventory
        bid_size = self.base_size * (1 - inv_frac)
        ask_size = self.base_size * (1 + inv_frac)

        max_buy = self.max_inventory - self.inventory
        max_sell = self.inventory + self.max_inventory

        bid_size = max(0, min(int(bid_size), max_buy))
        ask_size = max(0, min(int(ask_size), max_sell))

        return bid_size, ask_size

    def should_requote(self, mid):
        if self.last_quoted_mid is None:
            return True
        if abs(mid - self.last_quoted_mid) >= self.requote_threshold:
            return True
        if self.tick_since_quote >= self.max_quote_age:
            return True
        return False

    def act(self, market_state):
        mid = market_state["mid_price"]
        sigma = market_state.get("recent_vol", 0.005)

        if not self.should_requote(mid):
            self.tick_since_quote += 1
            return []

        reservation, half_spread = self.compute_reservation_and_spread(mid, sigma)
        bid_price = reservation - half_spread
        ask_price = reservation + half_spread

        bb_other = market_state.get("best_bid_other")
        ba_other = market_state.get("best_ask_other")
        if ba_other is not None and bid_price >= ba_other:
            bid_price = ba_other - self.passive_offset
        if bb_other is not None and ask_price <= bb_other:
            ask_price = bb_other + self.passive_offset

        bid_qty, ask_qty = self.compute_sizes()

        orders = []
        if bid_qty > 0 and bid_price > 0:
            orders.append({
                'agent_id': self.id,
                'instrument': 'spot',
                'order_type': 'limit',
                'side': 'buy',
                'price': float(bid_price),
                'qty': int(bid_qty),
            })

        if ask_qty > 0 and ask_price > 0:
            orders.append({
                'agent_id': self.id,
                'instrument': 'spot',
                'order_type': 'limit',
                'side': 'sell',
                'price': float(ask_price),
                'qty': int(ask_qty),
            })

        if orders:
            self.last_quoted_mid = mid
            self.tick_since_quote = 0

        return orders
