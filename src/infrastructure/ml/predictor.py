import joblib
import pandas as pd
from typing import List
from src.domain.entities import DengueRiskInput, DengueRiskOutput, RiskLevel
from src.domain.ports import IModelPredictor

class SklearnPredictor(IModelPredictor):
    def __init__(self, model_path: str):
        self._model_data = joblib.load(model_path)
        self._model = self._model_data["modelo"]
        self._features = self._model_data["atributos"]

    def predict(self, data: DengueRiskInput) -> DengueRiskOutput:
        return self.predict_batch([data])[0]

    def predict_batch(self, data_list: List[DengueRiskInput]) -> List[DengueRiskOutput]:
        df = pd.DataFrame([vars(d) for d in data_list])
        df = df[self._features]
        
        predictions = self._model.predict(df)
        probabilities = self._model.predict_proba(df)[:, 1]
        
        results = []
        for pred, prob in zip(predictions, probabilities):
            risk = RiskLevel.HIGH if pred == 1 else RiskLevel.LOW
            results.append(DengueRiskOutput(risk_level=risk, probability=float(prob)))
            
        return results
