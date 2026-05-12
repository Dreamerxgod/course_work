class OrderBook:


    def __init__(self, initial_price=100):
        self.bids = []
        self.asks = []
        self.last_price = initial_price
        self.trades = []
        self.agents = {}
        self.current_t = 0

    def set_time(self, t):
        self.current_t = t

    def cancel_orders_for_agent(self, agent_id):
        self.bids = [b for b in self.bids if b[2] != agent_id]
        self.asks = [a for a in self.asks if a[2] != agent_id]

    def expire_old(self, ttl):
        cutoff = self.current_t - ttl
        self.bids = [b for b in self.bids if b[3] > cutoff]
        self.asks = [a for a in self.asks if a[3] > cutoff]

    def add_order(self, order):
        qty = order['qty']
        agent = order['agent_id']
        side = order['side']
        order_type = order.get('order_type', 'limit')

        if order_type == 'market':
            return self.handle_market(side, qty, agent)

        return self._handle_limit(side, order['price'], qty, agent)

    def _handle_limit(self, side, price, qty, agent):
        if side == 'buy':
            trades, remaining = self.cross_buy(price, qty, agent)
            if remaining > 0:
                self.insert_bid(price, remaining, agent)
        else:
            trades, remaining = self.cross_sell(price, qty, agent)
            if remaining > 0:
                self.insert_ask(price, remaining, agent)
        self.trades.extend(trades)
        return trades

    def handle_market(self, side, qty, agent):
        if side == 'buy':
            trades, unfilled_qty = self.cross_buy(float('inf'), qty, agent)
        else:
            trades, unfilled_qty = self.cross_sell(0.0, qty, agent)
        self.trades.extend(trades)
        return trades

    def cross_buy(self, price, qty, agent):
        trades = []
        remaining = qty
        while remaining > 0 and self.asks and self.asks[0][0] <= price:
            ask_price, ask_qty, ask_agent, ask_placed_at = self.asks[0]
            if ask_agent == agent:
                self.asks.pop(0)
                continue
            trade_qty = min(remaining, ask_qty)
            trade_price = ask_price  # resting price
            self.apply_inventory(agent, +trade_qty)
            self.apply_inventory(ask_agent, -trade_qty)
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
                self.asks[0] = (ask_price, ask_qty - trade_qty, ask_agent, ask_placed_at)
            else:
                self.asks.pop(0)
        return trades, remaining

    def cross_sell(self, price, qty, agent):
        trades = []
        remaining = qty
        while remaining > 0 and self.bids and self.bids[0][0] >= price:
            bid_price, bid_qty, bid_agent, bid_placed_at = self.bids[0]
            if bid_agent == agent:
                self.bids.pop(0)
                continue
            trade_qty = min(remaining, bid_qty)
            trade_price = bid_price  # resting price
            self.apply_inventory(bid_agent, +trade_qty)
            self.apply_inventory(agent, -trade_qty)
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
                self.bids[0] = (bid_price, bid_qty - trade_qty, bid_agent, bid_placed_at)
            else:
                self.bids.pop(0)
        return trades, remaining

    def apply_inventory(self, agent_id, delta):
        agent = self.agents.get(agent_id)
        if agent is not None and hasattr(agent, "inventory"):
            agent.inventory += delta

    def insert_bid(self, price, qty, agent):
        self.bids.append((price, qty, agent, self.current_t))
        self.bids.sort(key=lambda entry: entry[0], reverse=True)

    def insert_ask(self, price, qty, agent):
        self.asks.append((price, qty, agent, self.current_t))
        self.asks.sort(key=lambda entry: entry[0])

    def get_best_excluding(self, agent_id):
        best_bid_other = next(
            (price for price, qty, owner, placed_at in self.bids if owner != agent_id),
            None,
        )
        best_ask_other = next(
            (price for price, qty, owner, placed_at in self.asks if owner != agent_id),
            None,
        )
        return best_bid_other, best_ask_other

    def get_mid_price(self, last_price=100):
        if self.bids and self.asks:
            best_bid = self.bids[0][0]
            best_ask = self.asks[0][0]
            mid = (best_bid + best_ask) / 2
        elif self.bids:
            mid = self.bids[0][0]
        elif self.asks:
            mid = self.asks[0][0]
        else:
            mid = last_price
        return max(mid, 1.0)
