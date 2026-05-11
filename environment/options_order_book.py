class OptionsOrderBook:


    def __init__(self, strike, option_type, initial_price=1.0):
        self.strike = strike
        self.option_type = option_type
        self.bids = []
        self.asks = []
        self.last_price = initial_price
        self.trades = []
        self.agents = {}

    def cancel_orders_for_agent(self, agent_id):
        self.bids = [b for b in self.bids if b[2] != agent_id]
        self.asks = [a for a in self.asks if a[2] != agent_id]

    def add_order(self, order):
        price = order['price']
        qty = order['qty']
        agent = order['agent_id']
        side = order['side']

        if side == 'buy':
            trades, remaining = self._cross_buy(price, qty, agent)
            if remaining > 0:
                self._insert_bid(price, remaining, agent)
        else:
            trades, remaining = self._cross_sell(price, qty, agent)
            if remaining > 0:
                self._insert_ask(price, remaining, agent)

        self.trades.extend(trades)
        return trades

    def _cross_buy(self, price, qty, agent):
        trades = []
        remaining = qty
        while remaining > 0 and self.asks and self.asks[0][0] <= price:
            ask_price, ask_qty, ask_agent = self.asks[0]
            if ask_agent == agent:
                self.asks.pop(0)
                continue
            trade_qty = min(remaining, ask_qty)
            trade_price = ask_price
            self._apply_inventory(agent, +trade_qty)
            self._apply_inventory(ask_agent, -trade_qty)
            trades.append({
                'price': trade_price,
                'qty': trade_qty,
                'buyer': agent,
                'seller': ask_agent,
                'aggressor': 'buy',
            })
            self.last_price = trade_price
            remaining -= trade_qty
            if ask_qty > trade_qty:
                self.asks[0] = (ask_price, ask_qty - trade_qty, ask_agent)
            else:
                self.asks.pop(0)
        return trades, remaining

    def _cross_sell(self, price, qty, agent):
        trades = []
        remaining = qty
        while remaining > 0 and self.bids and self.bids[0][0] >= price:
            bid_price, bid_qty, bid_agent = self.bids[0]
            if bid_agent == agent:
                self.bids.pop(0)
                continue
            trade_qty = min(remaining, bid_qty)
            trade_price = bid_price
            self._apply_inventory(bid_agent, +trade_qty)
            self._apply_inventory(agent, -trade_qty)
            trades.append({
                'price': trade_price,
                'qty': trade_qty,
                'buyer': bid_agent,
                'seller': agent,
                'aggressor': 'sell',
            })
            self.last_price = trade_price
            remaining -= trade_qty
            if bid_qty > trade_qty:
                self.bids[0] = (bid_price, bid_qty - trade_qty, bid_agent)
            else:
                self.bids.pop(0)
        return trades, remaining

    def _apply_inventory(self, agent_id, delta):
        agent = self.agents.get(agent_id)
        if agent is None:
            return
        if hasattr(agent, "inventory_by_option"):
            key = (self.strike, self.option_type)
            agent.inventory_by_option[key] = agent.inventory_by_option.get(key, 0) + delta
        if hasattr(agent, "inventory"):
            agent.inventory += delta

    def _insert_bid(self, price, qty, agent):
        self.bids.append((price, qty, agent))
        self.bids.sort(key=lambda x: x[0], reverse=True)

    def _insert_ask(self, price, qty, agent):
        self.asks.append((price, qty, agent))
        self.asks.sort(key=lambda x: x[0])

    def get_mid_price(self, last_price=1.0):
        if self.bids and self.asks:
            mid = (self.bids[0][0] + self.asks[0][0]) / 2
        elif self.bids:
            mid = self.bids[0][0]
        elif self.asks:
            mid = self.asks[0][0]
        else:
            mid = last_price
        return max(mid, 0.0001)
