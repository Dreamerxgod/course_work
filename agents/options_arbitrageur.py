from agents.base_agent import Agent
import config as cfg
import math


class OptionsArbitrageur(Agent):

    def __init__(self, id,
                 threshold=cfg.OPTION_ARB_THRESHOLD,
                 estimated_costs=cfg.OPTION_ARB_ESTIMATED_COSTS,
                 max_qty=5):
        super().__init__(id)
        self.threshold = threshold
        self.estimated_costs = estimated_costs
        self.max_qty = max_qty
        self.inventory = 0
        self.inventory_by_option = {}
        self.closes_spot_on_expiry = True

    def act(self, market_state):
        S = market_state['spot']
        strikes = market_state['strikes']
        tau = market_state['tau']
        r = market_state.get('r', 0.0)
        q = market_state.get('q', 0.0)
        mid_prices_call = market_state['mid_prices_call']
        mid_prices_put = market_state['mid_prices_put']

        orders = []
        trigger = self.threshold + self.estimated_costs

        for K in strikes:
            C_market = mid_prices_call.get(K)
            P_market = mid_prices_put.get(K)
            if C_market is None or P_market is None:
                continue

            parity_diff = (C_market - P_market) - (S * math.exp(-q * tau) - K * math.exp(-r * tau))

            if abs(parity_diff) <= trigger:
                continue

            if parity_diff > 0:
                orders.extend(self.three_ord(K, call_side='sell',
                                                    put_side='buy', spot_side='buy'))
            else:
                orders.extend(self.three_ord(K, call_side='buy',
                                                    put_side='sell', spot_side='sell'))

        return orders

    def three_ord(self, K, call_side, put_side, spot_side):
        return [
            {
                'agent_id': self.id,
                'instrument': 'option',
                'order_type': 'market',
                'side': call_side,
                'qty': int(self.max_qty),
                'strike': K,
                'option_type': 'call',
            },
            {
                'agent_id': self.id,
                'instrument': 'option',
                'order_type': 'market',
                'side': put_side,
                'qty': int(self.max_qty),
                'strike': K,
                'option_type': 'put',
            },
            {
                'agent_id': self.id,
                'instrument': 'spot',
                'order_type': 'market',
                'side': spot_side,
                'qty': int(self.max_qty),
            },
        ]
