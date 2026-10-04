import joblib
import pandas as pd
from typing import List, Dict, Optional
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
        
        global_importance = self.get_global_feature_importance()
        
        results = []
        for pred, prob in zip(predictions, probabilities):
            risk = RiskLevel.HIGH if pred == 1 else RiskLevel.LOW
            results.append(DengueRiskOutput(
                risk_level=risk, 
                probability=float(prob),
                feature_importances=global_importance
            ))
            
        return results

    def get_global_feature_importance(self) -> Optional[Dict[str, float]]:
        model_to_inspect = self._model
        if hasattr(self._model, "named_steps"):
            model_to_inspect = list(self._model.named_steps.values())[-1]
            
        if hasattr(model_to_inspect, "feature_importances_"):
            return dict(zip(self._features, [float(v) for v in model_to_inspect.feature_importances_]))
        elif hasattr(model_to_inspect, "coef_"):
            return dict(zip(self._features, [float(v) for v in model_to_inspect.coef_[0]]))
            
        return None
