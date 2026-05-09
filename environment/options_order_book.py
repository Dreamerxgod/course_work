class OptionsOrderBook:
    def __init__(self, strike, option_type, initial_price=1.0):
        self.strike = strike
        self.option_type = option_type
        self.bids = []  # (price, qty, agent_id)
        self.asks = []  # (price, qty, agent_id)
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
                # self-cross skip
                if bid_qty <= ask_qty:
                    self.bids.pop(0)
                else:
                    self.bids[0] = (bid_price, bid_qty - ask_qty, bid_agent)
                continue

            trade_qty = min(bid_qty, ask_qty)
            # обновляем inventory ТОЛЬКО если агент это market maker (hasattr inventory)
            for agent_id, delta in [(bid_agent, +trade_qty), (ask_agent, -trade_qty)]:
                agent_obj = self.agents.get(agent_id)
                if agent_obj is not None:
                    if hasattr(agent_obj, "inventory_by_option"):
                        key = (self.strike, self.option_type)
                        agent_obj.inventory_by_option[key] = agent_obj.inventory_by_option.get(key, 0) + delta
                    if hasattr(agent_obj, "inventory"):
                        agent_obj.inventory += delta

            trade_price = (bid_price + ask_price) / 2

            trades.append({
                'price': trade_price,
                'qty': trade_qty,
                'buyer': bid_agent,
                'seller': ask_agent
            })

            if bid_qty > trade_qty:
                self.bids[0] = (bid_price, bid_qty - trade_qty, bid_agent)
            else:
                self.bids.pop(0)

            if ask_qty > trade_qty:
                self.asks[0] = (ask_price, ask_qty - trade_qty, ask_agent)
            else:
                self.asks.pop(0)

            self.last_price = trade_price

        # после цикла добавляем все сделки в общий список
        self.trades.extend(trades)
        return trades

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