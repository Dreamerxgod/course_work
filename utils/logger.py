import csv
from datetime import datetime
import os


class Logger:
    def __init__(self, trades_file="logs/trades.csv",
                 events_file="logs/events.log",
                 enable_console=True):
        self.trades_file = trades_file
        self.events_file = events_file
        self.enable_console = enable_console
        os.makedirs(os.path.dirname(self.trades_file), exist_ok=True)

        with open(self.trades_file.replace(".csv", "_options.csv"), "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "price", "qty", "buyer", "seller", "instrument", "strike", "option_type"])

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")

        with open(self.events_file, "a") as f:
            f.write(f"[{timestamp}] {message}\n")

        if self.enable_console:
            print(f"[{timestamp}] {message}")

    def log_trade(self, t, trade):
        with open(self.trades_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                t,
                trade["price"],
                trade["qty"],
                trade["buyer"],
                trade["seller"]
            ])

        if self.enable_console:
            print(f"[TRADE t={t}] "
                  f"{trade['buyer']} -> {trade['seller']} | "
                  f"qty={trade['qty']} price={trade['price']:.2f}")

    def log_news(self, t, news):
        self.log(f"[NEWS t={t}] news={news:.3f}")

    def log_mid_price(self, t, mid):
        self.log(f"[MID t={t}] mid_price={mid:.2f}")

    def log_order(self, t, order, agent=None):
        trader_type = agent.__class__.__name__ if agent is not None else "Unknown"

        inventory = getattr(agent, 'inventory', None)
        inv_str = f" inv={inventory}" if inventory is not None else ""

        trend = getattr(agent, 'last_trend', None)
        trend_str = f" trend={trend:+.4f}" if trend is not None else ""

        self.log(
            f"[ORDER t={t}] "
            f"{trader_type}({order['agent_id']}) {order['side']} "
            f"p={order['price']:.4f} qty={order['qty']}{inv_str}{trend_str}"
        )

    def log_option_trade(self, t, trade):
        with open(self.trades_file.replace(".csv", "_options.csv"), "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                t,
                trade.get("price", 0),
                trade.get("qty", 0),
                trade.get("buyer", ""),
                trade.get("seller", ""),
                trade.get("instrument", ""),
                trade.get("strike", ""),
                trade.get("option_type", "")
            ])

        if self.enable_console:
            print(f"[OPTION TRADE t={t}] "
                  f"{trade.get('buyer')} -> {trade.get('seller')} | "
                  f"{trade.get('instrument')} {trade.get('option_type')} "
                  f"K={trade.get('strike')} qty={trade.get('qty')} price={trade.get('price'):.2f}")

    def log_option_order(self, t, order, agent=None):
        trader_type = agent.__class__.__name__ if agent else "Unknown"
        self.log(
            f"[OPTION ORDER t={t}] {trader_type}({order['agent_id']}) "
            f"{order['side']} p={order['price']:.4f} qty={order['qty']} "
            f"K={order.get('strike')} "
            f"order_type={order.get('order_type')} option_type={order.get('option_type')}"
        )
