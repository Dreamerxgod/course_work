from agents.base_agent import Agent
import config as cfg

class MarketMaker(Agent):
    def __init__(
        self,
        id,
        base_spread=cfg.MM_BASE_SPREAD,
        inventory_risk_aversion=cfg.MM_INV_RISK,
        max_inventory=cfg.MM_MAX_INVENTORY,
        base_size=cfg.MM_BASE_SIZE
    ):
        super().__init__(id)
        self.inventory = 0
        self.max_inventory = max_inventory
        self.base_spread = base_spread
        self.inventory_risk_aversion = inventory_risk_aversion
        self.base_size = base_size

    def compute_spread(self):
        inv_penalty = self.inventory_risk_aversion * abs(self.inventory) / self.max_inventory
        return self.base_spread * (1 + inv_penalty)

    def compute_sizes(self):
        inv_frac = self.inventory / self.max_inventory
        bid_size = self.base_size * (1 - inv_frac)
        ask_size = self.base_size * (1 + inv_frac)

        max_buy = self.max_inventory - self.inventory
        max_sell = self.inventory + self.max_inventory

        bid_size = max(0, min(int(bid_size), max_buy))
        ask_size = max(0, min(int(ask_size), max_sell))

        return bid_size, ask_size

    def act(self, market_state):
        mid = market_state["mid_price"]
        spread = self.compute_spread()
        bid_price = mid - spread / 2
        ask_price = mid + spread / 2
        bid_qty, ask_qty = self.compute_sizes()

        orders = []

        if bid_qty > 0:
            orders.append({
                'agent_id': self.id,
                'instrument': 'spot',
                'order_type': 'limit',
                'side': 'buy',
                'price': float(bid_price),
                'qty': int(bid_qty),
            })

        if ask_qty > 0:
            orders.append({
                'agent_id': self.id,
                'instrument': 'spot',
                'order_type': 'limit',
                'side': 'sell',
                'price': float(ask_price),
                'qty': int(ask_qty),
            })

        return orders
