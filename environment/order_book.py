class OrderBook:
    def __init__(self, initial_price=100):
        self.bids = []      # (price, qty, agent_id)
        self.asks = []      # (price, qty, agent_id)
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

        if order['side'] == 'buy':
            self.bids.append((price, qty, agent))
            self.bids.sort(key=lambda x: x[0], reverse=True)
        else:
            self.asks.append((price, qty, agent))
            self.asks.sort(key=lambda x: x[0])

        return self.match_orders()

    def match_orders(self):
        trades = []

        while self.bids and self.asks and self.bids[0][0] >= self.asks[0][0]:
            bid_price, bid_qty, bid_agent = self.bids[0]
            ask_price, ask_qty, ask_agent = self.asks[0]

            if bid_agent == ask_agent:
                self.bids.pop(0)
                self.asks.pop(0)
                continue

            trade_qty = min(bid_qty, ask_qty)
            trade_price = (bid_price + ask_price) / 2

            for agent_id, delta in [(bid_agent, +trade_qty), (ask_agent, -trade_qty)]:
                agent = self.agents.get(agent_id)
                if agent and hasattr(agent, "inventory"):
                    agent.inventory += delta

            trades.append({
                'price': trade_price,
                'qty': trade_qty,
                'buyer': bid_agent,
                'seller': ask_agent
            })

            # обновляем заявки
            if bid_qty > trade_qty:
                self.bids[0] = (bid_price, bid_qty - trade_qty, bid_agent)
            else:
                self.bids.pop(0)

            if ask_qty > trade_qty:
                self.asks[0] = (ask_price, ask_qty - trade_qty, ask_agent)
            else:
                self.asks.pop(0)

        self.trades.extend(trades)
        return trades

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
