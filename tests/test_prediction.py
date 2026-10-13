import os
import pytest
import numpy as np
from unittest.mock import Mock
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


@pytest.mark.parametrize("classes", [[0, 1], [1, 0]])
def test_saved_threshold_controls_risk_including_boundary(monkeypatch, classes):
    model = Mock(spec=["classes_", "predict_proba", "predict", "feature_importances_"])
    model.classes_ = np.array(classes)
    probabilities = np.array([0.54, 0.55, 0.56])
    model.predict_proba.return_value = np.column_stack(
        [probabilities if cls == 1 else 1 - probabilities for cls in classes]
    )
    model.feature_importances_ = np.array([1.0])
    monkeypatch.setattr("joblib.load", lambda path: {
        "modelo": model, "atributos": ["mes"], "limiar_decisao_modelo": 0.55,
    })
    predictor = SklearnPredictor("unused.pkl")
    data = DengueRiskInput(25, 70, 100, 100, 1, 10, 5)
    results = predictor.predict_batch([data] * 3)
    assert [result.risk_level for result in results] == [RiskLevel.LOW, RiskLevel.HIGH, RiskLevel.HIGH]
    assert [result.probability for result in results] == pytest.approx(probabilities)
    model.predict.assert_not_called()
    assert predictor.predict_batch([]) == []


def test_actual_artifact_prediction_matches_saved_threshold():
    predictor = SklearnPredictor("models/modelo_baseline_risco_dengue.pkl")
    data = DengueRiskInput(25, 70, 100, 100, 1, 10, 5)
    result = predictor.predict(data)
    assert predictor._threshold == 0.55
    expected = RiskLevel.HIGH if result.probability >= 0.55 else RiskLevel.LOW
    assert result.risk_level == expected
