# agents/options_market_maker.py
from agents.base_agent import Agent
import config as cfg
from utils.bs_utils import bs_price, bs_delta
from collections import defaultdict
import math
from utils import random_utils as ru

class OptionsMarketMaker(Agent):
    def __init__(self, id, base_spread_factor=cfg.OPTION_SPREAD_FACTOR, base_size=1, hedge_aggressiveness=1.0):
        super().__init__(id)
        self.inventory = 0
        self.inventory_by_option = {}
        self.base_spread_factor = base_spread_factor
        self.base_size = base_size
        self.hedge_aggressiveness = hedge_aggressiveness
        self.max_spot_inventory = 50
        self.pnl_option = 0.0
        self.pnl_hedge = 0.0
        self.total_pnl = 0.0
        self.pnl_history = []

        self.prev_option_prices = {}
        self.prev_spot_price = None

    def act(self, market_state):
        S = market_state['spot']
        vol = market_state['vol']
        tau = market_state['tau']
        r = market_state.get('r', 0.0)
        q = market_state.get('q', 0.0)
        strikes = market_state['strikes']

        orders = []
        for K in strikes:
            for option_type in ['call', 'put']:
                theo = bs_price(S, K, r, q, vol, tau, option_type=option_type)
                theo = max(float(theo), 0.0001)


                spread = self.base_spread_factor * theo

                bid = theo - spread / 2
                ask = theo + spread / 2


                qty = float(ru.uniform(1, 3))

                long_limit_hit = self.inventory >= self.max_spot_inventory
                short_limit_hit = self.inventory <= -self.max_spot_inventory

                if not long_limit_hit:
                    orders.append({
                        'agent_id': self.id,
                        'instrument': 'option',
                        'order_type': 'limit',
                        'side': 'buy',
                        'price': float(bid),
                        'qty': qty,
                        'strike': K,
                        'option_type': option_type,
                    })

                if not short_limit_hit:
                    orders.append({
                        'agent_id': self.id,
                        'instrument': 'option',
                        'order_type': 'limit',
                        'side': 'sell',
                        'price': float(ask),
                        'qty': qty,
                        'strike': K,
                        'option_type': option_type,
                    })

        return orders
