from agent import BaseAgent
from . import model_dict


class NLLBAgent(BaseAgent):
    def __init__(self, repo, target, model="nllb-1.3B"):
        super().__init__(repo, target)
        self.model = model_dict[model]

    def call(self, input_text):
        pass

    def name(self):
        return self.model
