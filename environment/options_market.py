from environment.options_order_book import OptionsOrderBook
from utils.bs_utils import bs_price, bs_delta
import config as cfg

class OptionsMarket:
    def __init__(self, strikes=None, tau=cfg.OPTION_TAU, r=cfg.OPTION_R, q=cfg.OPTION_Q, vol=cfg.OPTION_VOL, option_type = 'call'):
        self.strikes = strikes or cfg.OPTION_STRIKES
        self.tau = tau
        self.r = r
        self.q = q
        self.vol = vol
        self.option_type = option_type
        self.logger = None

        self.order_books = {
            K: {
                'call': OptionsOrderBook(
                    strike=K,
                    option_type='call',
                    initial_price=bs_price(cfg.INITIAL_PRICE, K, self.r, self.q, self.vol, self.tau, option_type='call')
                ),
                'put': OptionsOrderBook(
                    strike=K,
                    option_type='put',
                    initial_price=bs_price(cfg.INITIAL_PRICE, K, self.r, self.q, self.vol, self.tau, option_type='put')
                )
            }
            for K in self.strikes
        }
        self.mid_prices_call = {K: self.order_books[K]['call'].last_price for K in self.strikes}
        self.mid_prices_put = {K: self.order_books[K]['put'].last_price for K in self.strikes}
        self.agents = {}

    def set_agents(self, agents):
        self.agents = {a.id: a for a in agents}
        for K_books in self.order_books.values():  # K_books = {'call': ..., 'put': ...}
            for ob in K_books.values():  # ob = OptionsOrderBook
                ob.agents = self.agents

    def theoretical_price(self, S, K, option_type='call'):
        return bs_price(S, K, self.r, self.q, self.vol, self.tau, option_type=option_type)

    def step(self, t, S, agents, vol=None, spot_order_book=None):

        option_trades = []
        spot_trades_from_options = []

        if vol is not None:
            vol = float(vol)
            self.vol = vol

        for K in self.strikes:
            for opt_type in ['call', 'put']:
                theo = self.theoretical_price(S, K, option_type=opt_type)
                ob = self.order_books[K][opt_type]

        for agent in agents:
            for K_books in self.order_books.values():
                for ob in K_books.values():
                    ob.cancel_orders_for_agent(agent.id)

            orders = agent.act({
                'spot': S,
                'tau': self.tau,
                'r': self.r,
                'q': self.q,
                'vol': self.vol,
                'strikes': self.strikes,
                'mid_prices_call': self.mid_prices_call,
                'mid_prices_put': self.mid_prices_put
            })
            for o in orders:
                if o.get('instrument') == 'spot':
                    if spot_order_book is not None:
                        if hasattr(self, 'logger') and self.logger:
                            self.logger.log_order(t, o, agent=agent)
                        new_trades = spot_order_book.add_order(o)
                        for tr in new_trades:
                            tr['time'] = t
                            if hasattr(self, 'logger') and self.logger:
                                self.logger.log_trade(t, tr)
                        spot_trades_from_options += new_trades
                    continue

                K = o.get('strike')
                opt_type = o.get('option_type', 'call')
                if K not in self.order_books or opt_type not in ['call', 'put']:
                    continue
                if hasattr(self, 'logger') and self.logger:
                    self.logger.log_option_order(t, o, agent=agent)

                new_trades = self.order_books[K][opt_type].add_order(o)
                for tr in new_trades:
                    tr['time'] = t
                    tr['instrument'] = 'option'
                    tr['strike'] = K
                    tr['option_type'] = opt_type
                option_trades += new_trades

        for K in self.strikes:
            self.mid_prices_call[K] = self.order_books[K]['call'].get_mid_price(self.mid_prices_call[K])
            self.mid_prices_put[K] = self.order_books[K]['put'].get_mid_price(self.mid_prices_put[K])

            self.mid_prices_call[K] = max(self.mid_prices_call[K], 0.0001)
            self.mid_prices_put[K] = max(self.mid_prices_put[K], 0.0001)

        if spot_order_book is not None and t % cfg.DELTA_HEDGE_INTERVAL == 0:
            for agent in agents:
                inv_map = getattr(agent, "inventory_by_option", None)
                if not inv_map:
                    continue

                delta_exposure = 0.0
                for (K, opt_type), qty in inv_map.items():
                    if qty == 0:
                        continue
                    d = bs_delta(S, K, self.r, self.q, self.vol, self.tau, option_type=opt_type)
                    delta_exposure += qty * d

                hedge_qty = int(round(abs(delta_exposure)))

                if hedge_qty <= 0:
                    continue

                if delta_exposure > 0:
                    side = 'sell'
                    price = max(0.0001, S - 0.0001)
                else:
                    side = 'buy'
                    price = S + 0.0001

                spot_order = {
                    'agent_id': agent.id,
                    'instrument': 'spot',
                    'order_type': 'limit',
                    'side': side,
                    'price': float(price),
                    'qty': hedge_qty
                }

                if hasattr(self, 'logger') and self.logger:
                    self.logger.log_order(t, spot_order, agent=agent)
                hedge_trades = spot_order_book.add_order(spot_order)
                for tr in hedge_trades:
                    tr['time'] = t
                    if hasattr(self, 'logger') and self.logger:
                        self.logger.log_trade(t, tr)
                spot_trades_from_options += hedge_trades

        return option_trades, spot_trades_from_options
