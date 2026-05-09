class Agent:
    def __init__(self, id):
        self.id = id

    def act(self, market_state):
        raise NotImplementedError
