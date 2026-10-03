from src.domain.entities import DengueRiskInput, DengueRiskOutput
from src.domain.ports import IModelPredictor

class PredictRiskUseCase:
    def __init__(self, predictor: IModelPredictor):
        self._predictor = predictor

    def execute(self, data: DengueRiskInput) -> DengueRiskOutput:
        return self._predictor.predict(data)
