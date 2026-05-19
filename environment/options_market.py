from environment.options_order_book import OptionsOrderBook
from utils.bs_utils import bs_price, bs_delta
from utils import random_utils as ru
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
        for K_books in self.order_books.values():
            for ob in K_books.values():
                ob.agents = self.agents

    def theoretical_price(self, S, K, option_type='call'):
        return bs_price(S, K, self.r, self.q, self.vol, self.tau, option_type=option_type)

    def settle_expiry(self, S, agents, spot_order_book=None):
        for agent in agents:
            inv_map = getattr(agent, 'inventory_by_option', None)
            if not inv_map:
                continue
            for (K, opt_type), qty in list(inv_map.items()):
                if qty == 0:
                    continue
                if opt_type == 'call':
                    payoff = max(S - K, 0.0)
                else:
                    payoff = max(K - S, 0.0)
                cash_change = qty * payoff
                if not hasattr(agent, 'settlement_pnl'):
                    agent.settlement_pnl = 0.0
                agent.settlement_pnl += cash_change
            inv_map.clear()

        for K_books in self.order_books.values():
            for ob in K_books.values():
                ob.bids.clear()
                ob.asks.clear()

        new_tau = cfg.OPTION_TAU
        for K in self.strikes:
            self.mid_prices_call[K] = max(0.0001,
                bs_price(S, K, self.r, self.q, self.vol, new_tau, option_type='call'))
            self.mid_prices_put[K] = max(0.0001,
                bs_price(S, K, self.r, self.q, self.vol, new_tau, option_type='put'))
            self.order_books[K]['call'].last_price = self.mid_prices_call[K]
            self.order_books[K]['put'].last_price = self.mid_prices_put[K]

        for agent in agents:
            if hasattr(agent, 'last_quoted_S'):
                agent.last_quoted_S = None
                agent.tick_since_quote = 0

        if spot_order_book is not None:
            for agent in agents:
                if not getattr(agent, 'closes_spot_on_expiry', False):
                    continue
                spot_inv = getattr(agent, 'inventory', 0)
                if spot_inv == 0:
                    continue
                side = 'sell' if spot_inv > 0 else 'buy'
                close_order = {
                    'agent_id': agent.id,
                    'instrument': 'spot',
                    'order_type': 'market',
                    'side': side,
                    'qty': abs(int(spot_inv)),
                }
                spot_order_book.add_order(close_order)

        if hasattr(self, 'logger') and self.logger:
            self.logger.log(f"[EXPIRY S={S:.2f} new_tau={new_tau:.4f}]")

    def step(self, t, S, agents, vol=None, spot_order_book=None):

        option_trades = []
        spot_trades_from_options = []

        if vol is not None:
            vol = float(vol)
            self.vol = vol

        self.tau -= 1.0 / cfg.STEPS_PER_YEAR
        if self.tau <= 1e-6:
            self.settle_expiry(S, agents, spot_order_book=spot_order_book)
            self.tau = cfg.OPTION_TAU

        for K_books in self.order_books.values():
            for ob in K_books.values():
                ob.set_time(t)
                ob.expire_old(cfg.ORDER_TTL)

        agent_order = list(agents)
        ru.shuffle(agent_order)
        for agent in agent_order:
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

            if orders and hasattr(agent, "inventory_by_option"):
                has_option_order = any(o.get('instrument') == 'option' for o in orders)
                if has_option_order:
                    for K_books in self.order_books.values():
                        for ob in K_books.values():
                            ob.cancel_orders_for_agent(agent.id)

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
            hedge_order = list(agents)
            ru.shuffle(hedge_order)
            for agent in hedge_order:
                if not getattr(agent, "needs_external_hedge", False):
                    continue
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

                side = 'sell' if delta_exposure > 0 else 'buy'


                spot_order = {
                    'agent_id': agent.id,
                    'instrument': 'spot',
                    'order_type': 'market',
                    'side': side,
                    'qty': hedge_qty,
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
