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
        self._threshold = float(self._model_data.get("limiar_decisao_modelo", 0.5))
        if not 0.0 <= self._threshold <= 1.0:
            raise ValueError("Limiar de decisão do modelo deve estar entre 0 e 1.")

    def predict(self, data: DengueRiskInput) -> DengueRiskOutput:
        return self.predict_batch([data])[0]

    def predict_batch(self, data_list: List[DengueRiskInput]) -> List[DengueRiskOutput]:
        if not data_list:
            return []
        df = pd.DataFrame([vars(d) for d in data_list])
        df = df[self._features]
        
        high_class_index = list(self._model.classes_).index(1)
        probabilities = self._model.predict_proba(df)[:, high_class_index]
        
        global_importance = self.get_global_feature_importance()
        
        results = []
        for prob in probabilities:
            risk = RiskLevel.HIGH if prob >= self._threshold else RiskLevel.LOW
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
