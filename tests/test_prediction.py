import math
from unittest.mock import Mock

import numpy as np
import pytest

from src.domain.entities import DengueRiskInput, RiskLevel
from src.infrastructure.ml.predictor import SklearnPredictor

MODEL = "models/modelo_risco_dengue.pkl"


def test_model_predicts_with_required_inputs_only():
    predictor = SklearnPredictor(MODEL)
    result = predictor.predict(DengueRiskInput(25.0, 70.0, 100.0, 100.0, 1, 10.0, 5.0))
    assert result.risk_level in (RiskLevel.LOW, RiskLevel.HIGH)
    assert 0.0 <= result.probability <= 1.0


def test_model_artifact_describes_itself():
    predictor = SklearnPredictor(MODEL)
    assert set(predictor.features) <= set(DengueRiskInput.__dataclass_fields__)
    assert 0 < predictor.threshold < 1
    assert predictor.high_incidence_threshold == 300
    importance = predictor.get_global_feature_importance()
    assert set(importance) == set(predictor.features) and sum(importance.values()) == pytest.approx(1, abs=1e-3)
    metrics = predictor.metrics
    assert metrics["limiar_decisao"] == predictor.threshold
    assert {row["ano_teste"] for row in metrics["avaliacao_por_ano"]} >= {2023, 2024, 2025}


def test_more_recent_cases_raise_the_score():
    predictor = SklearnPredictor(MODEL)
    quiet = DengueRiskInput(26.0, 80.0, 150.0, 500.0, 3, 0.0, 0.0, temperatura_media_lag1=27.0)
    outbreak = DengueRiskInput(26.0, 80.0, 150.0, 500.0, 3, 3000.0, 900.0, temperatura_media_lag1=27.0,
                               incidencia_lag2=400.0, incidencia_vizinhos_lag1=600.0)
    assert predictor.predict(outbreak).probability > predictor.predict(quiet).probability


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


def test_optional_inputs_default_to_missing():
    data = DengueRiskInput(25, 70, 100, 100, 1, 10, 5)
    assert math.isnan(data.incidencia_vizinhos_lag1)
