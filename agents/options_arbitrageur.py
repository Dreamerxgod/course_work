from agents.base_agent import Agent
import config as cfg
from utils.bs_utils import bs_price
import math

class OptionsArbitrageur(Agent):
    def __init__(self, id, threshold=cfg.OPTION_ARB_THRESHOLD, max_qty=5):
        super().__init__(id)
        self.threshold = threshold
        self.max_qty = max_qty
        self.inventory_by_option = {}  # нужен для дельта-хеджа в OptionsMarket.step

    def act(self, market_state):
        S = market_state['spot']
        strikes = market_state['strikes']
        tau = market_state['tau']
        r = market_state.get('r', 0.0)
        q = market_state.get('q', 0.0)

        mid_prices_call = market_state['mid_prices_call']
        mid_prices_put = market_state['mid_prices_put']

        orders = []

        for K in strikes:
            C_market = mid_prices_call.get(K)
            P_market = mid_prices_put.get(K)

            if C_market is None or P_market is None:
                continue

            parity_diff = (C_market - P_market) - (S * math.exp(-q * tau) - K * math.exp(-r * tau))

            if abs(parity_diff) > self.threshold:
                if parity_diff > 0:
                    # call слишком дорогой относительно put
                    orders.append({
                        'agent_id': self.id,
                        'instrument': 'option',
                        'order_type': 'limit',
                        'side': 'sell',
                        'price': float(C_market),
                        'qty': int(self.max_qty),
                        'strike': K,
                        'option_type': 'call'
                    })
                    orders.append({
                        'agent_id': self.id,
                        'instrument': 'option',
                        'order_type': 'limit',
                        'side': 'buy',
                        'price': float(P_market),
                        'qty': int(self.max_qty),
                        'strike': K,
                        'option_type': 'put'
                    })
                else:
                    # put слишком дорогой относительно call
                    orders.append({
                        'agent_id': self.id,
                        'instrument': 'option',
                        'order_type': 'limit',
                        'side': 'buy',
                        'price': float(C_market),
                        'qty': int(self.max_qty),
                        'strike': K,
                        'option_type': 'call'
                    })
                    orders.append({
                        'agent_id': self.id,
                        'instrument': 'option',
                        'order_type': 'limit',
                        'side': 'sell',
                        'price': float(P_market),
                        'qty': int(self.max_qty),
                        'strike': K,
                        'option_type': 'put'
                    })

        return orders