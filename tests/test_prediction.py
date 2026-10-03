import os
import pytest
from src.domain.entities import DengueRiskInput, RiskLevel
from src.infrastructure.ml.predictor import SklearnPredictor

def test_model_prediction_successful():
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "modelo_baseline_risco_dengue.pkl")
    predictor = SklearnPredictor(model_path)
    
    input_data = DengueRiskInput(
        temperatura_media=25.0,
        umidade_media=70.0,
        precipitacao_total=100.0,
        densidade_demografica=100.0,
        mes=1,
        casos_lag1=10.0,
        incidencia_lag1=5.0
    )
    
    result = predictor.predict(input_data)
    
    assert result.risk_level in [RiskLevel.LOW, RiskLevel.HIGH]
    assert 0.0 <= result.probability <= 1.0
