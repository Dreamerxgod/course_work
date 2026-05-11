import random as _random
import numpy as _np

_py_rng = _random.Random()
_np_rng = _np.random.default_rng()


def set_seed(seed):
    global _py_rng, _np_rng
    _py_rng = _random.Random(seed)
    _np_rng = _np.random.default_rng(seed)


def get_py_rng():
    return _py_rng


def get_np_rng():
    return _np_rng


def uniform(a, b):
    return _py_rng.uniform(a, b)


def randint(a, b):
    return _py_rng.randint(a, b)


def choice(seq):
    return _py_rng.choice(seq)


def random():
    return _py_rng.random()


def gauss(mu, sigma):
    return _py_rng.gauss(mu, sigma)


def shuffle(seq):
    _py_rng.shuffle(seq)
