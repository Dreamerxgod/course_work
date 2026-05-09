import random

class NewsProcess:
    def __init__(self, probability=0.1, volatility=1.0):
        self.probability = probability
        self.volatility = volatility
        self.current_news = 0.0

    def step(self):
        if random.random() < self.probability:
            self.current_news = random.uniform(-self.volatility, self.volatility)
        else:
            self.current_news = 0.0

    def get_news(self):
        return self.current_news
