from utils import random_utils as ru


class NewsProcess:


    def __init__(self, persistence=0.9, shock_probability=0.05, shock_sigma=0.3):
        self.persistence = persistence
        self.shock_probability = shock_probability
        self.shock_sigma = shock_sigma
        self.current_news = 0.0

    def step(self):

        self.current_news *= self.persistence
        shock = 0.0
        if ru.random() < self.shock_probability:
            shock = ru.gauss(0.0, self.shock_sigma)
            self.current_news += shock
        return shock

    def get_news(self):
        return self.current_news
