from agents.base_agent import Agent
import config as cfg
from utils.bs_utils import bs_price, bs_delta
from collections import defaultdict
import math
from utils import random_utils as ru

class OptionsMarketMaker(Agent):
    def __init__(self, id, base_spread_factor=cfg.OPTION_SPREAD_FACTOR, base_size=1, hedge_aggressiveness=1.0,
                 requote_threshold=cfg.OPT_MM_REQUOTE_THRESHOLD,
                 max_quote_age=cfg.OPT_MM_MAX_QUOTE_AGE):
        super().__init__(id)
        self.needs_external_hedge = True
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

        self.requote_threshold = requote_threshold
        self.max_quote_age = max_quote_age
        self.last_quoted_S = None
        self.tick_since_quote = 0

    def should_requote(self, S):
        if self.last_quoted_S is None:
            return True
        if abs(S - self.last_quoted_S) >= self.requote_threshold:
            return True
        if self.tick_since_quote >= self.max_quote_age:
            return True
        return False

    def act(self, market_state):
        S = market_state['spot']
        vol = market_state['vol']
        tau = market_state['tau']
        r = market_state.get('r', 0.0)
        q = market_state.get('q', 0.0)
        strikes = market_state['strikes']

        if not self.should_requote(S):
            self.tick_since_quote += 1
            return []

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

        if orders:
            self.last_quoted_S = S
            self.tick_since_quote = 0

        return orders
