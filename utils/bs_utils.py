import math
from scipy.stats import norm

def d1(S, K, r, q, sigma, T):
    return (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))

def d2(S, K, r, q, sigma, T):
    return d1(S, K, r, q, sigma, T) - sigma * math.sqrt(T)

def bs_price(S, K, r, q, sigma, T, option_type='call'):
    if T <= 0:
        if option_type == 'call':
            return max(0.0, S - K)
        else:  # put
            return max(0.0, K - S)
    if sigma <= 0:
        if option_type == 'call':
            return max(0.0, S * math.exp(-q*T) - K * math.exp(-r*T))
        else:
            return max(0.0, K * math.exp(-r*T) - S * math.exp(-q*T))

    D1 = d1(S, K, r, q, sigma, T)
    D2 = D1 - sigma * math.sqrt(T)
    if option_type == 'call':
        return S * math.exp(-q*T) * norm.cdf(D1) - K * math.exp(-r*T) * norm.cdf(D2)
    else:
        return K * math.exp(-r*T) * norm.cdf(-D2) - S * math.exp(-q*T) * norm.cdf(-D1)

def bs_delta(S, K, r, q, sigma, T, option_type='call'):
    if T <= 0:
        if option_type == 'call':
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0
    D1 = d1(S, K, r, q, sigma, T)
    if option_type == 'call':
        return math.exp(-q*T) * norm.cdf(D1)
    else:
        return math.exp(-q*T) * (norm.cdf(D1) - 1.0)

def bs_vega(S, K, r, q, sigma, T):
    if T <= 0 or sigma <= 0:
        return 0.0
    D1 = d1(S, K, r, q, sigma, T)
    return S * math.exp(-q*T) * norm.pdf(D1) * math.sqrt(T)

def bs_gamma(S, K, r, q, sigma, T):
    if T <= 0 or sigma <= 0:
        return 0.0
    D1 = d1(S, K, r, q, sigma, T)
    return math.exp(-q*T) * norm.pdf(D1) / (S * sigma * math.sqrt(T))

def bs_theta(S, K, r, q, sigma, T, option_type='call'):
    if T <= 0:
        return 0.0
    D1 = d1(S, K, r, q, sigma, T)
    D2 = D1 - sigma * math.sqrt(T)
    term1 = - (S * norm.pdf(D1) * sigma * math.exp(-q*T)) / (2 * math.sqrt(T))
    if option_type == 'call':
        term2 = q * S * norm.cdf(D1) * math.exp(-q*T)
        term3 = - r * K * math.exp(-r*T) * norm.cdf(D2)
    else:
        term2 = q * S * math.exp(-q*T) * norm.cdf(-D1)
        term3 = - r * K * math.exp(-r*T) * norm.cdf(-D2)
    return term1 + term2 + term3

def implied_volatility(price, S, K, r, q, T, option_type='call',
                       sigma_low=1e-4, sigma_high=5.0, tol=1e-6, max_iter=100):
    if price is None or price <= 0 or S <= 0 or K <= 0:
        return None
    if T <= 0:
        return None

    lo, hi = sigma_low, sigma_high
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        pmid = bs_price(S, K, r, q, mid, T, option_type=option_type)
        if abs(pmid - price) < tol:
            return mid
        if pmid > price:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)

# что б безопасно было считать mean
def safe_mean(values):
    xs = []
    for v in values:
        if v is None:
            continue
        try:
            if isinstance(v, float) and math.isnan(v):
                continue
        except Exception:
            pass
        xs.append(float(v))
    return (sum(xs) / len(xs)) if xs else None


def mean_realised_vol(rv_history):
    return safe_mean(rv_history)


def mean_implied_vol_overall(iv_history):
    vals = []
    for step in iv_history:
        if not step:
            continue
        for iv in step.values():
            vals.append(iv)
    return safe_mean(vals)


def mean_implied_vol_by_strike(iv_history, strikes):
    out = {}
    for K in strikes:
        vals = []
        for step in iv_history:
            if step is None:
                continue
            vals.append(step.get(K))
        out[K] = safe_mean(vals)
    return out


def iv_rv_summary(rv_history, iv_history_call, iv_history_put, strikes=None):
    summary = {
        "mean_rv": mean_realised_vol(rv_history),
        "mean_iv_call": mean_implied_vol_overall(iv_history_call),
        "mean_iv_put": mean_implied_vol_overall(iv_history_put),
    }

    if strikes is not None:
        summary["mean_iv_call_by_strike"] = mean_implied_vol_by_strike(iv_history_call, strikes)
        summary["mean_iv_put_by_strike"] = mean_implied_vol_by_strike(iv_history_put, strikes)

    return summary


def print_iv_rv_summary(rv_history, iv_history_call, iv_history_put, strikes=None, precision=4):
    s = iv_rv_summary(rv_history, iv_history_call, iv_history_put, strikes=strikes)

    def fmt(x):
        return "None" if x is None else f"{x:.{precision}f}"

    print(f"Mean realised vol:          {fmt(s['mean_rv'])}")
    print(f"Mean implied vol (calls):   {fmt(s['mean_iv_call'])}")
    print(f"Mean implied vol (puts):    {fmt(s['mean_iv_put'])}")

    if strikes is not None:
        print("\nMean IV by strike (calls):")
        for K in strikes:
            print(f"  K={K}: {fmt(s['mean_iv_call_by_strike'].get(K))}")

        print("\nMean IV by strike (puts):")
        for K in strikes:
            print(f"  K={K}: {fmt(s['mean_iv_put_by_strike'].get(K))}")

    return s
