import math

import numpy as np
import pandas as pd
import pytest

from src.application.use_cases.build_analytics_data import (
    CASE_FEATURES,
    build_monthly,
    build_scenarios,
    build_typical_profile,
    geometry_centroid,
    validate_model_inputs,
)
from src.application.use_cases.predict_risk import PredictRiskUseCase
from src.domain.validation import MODEL_FIELDS, build_risk_input, parse_field
from src.infrastructure.ml.predictor import SklearnPredictor

NEIGHBORS = {1: [2], 2: [1]}


@pytest.fixture(scope="module")
def use_case():
    return PredictRiskUseCase(SklearnPredictor("models/modelo_risco_dengue.pkl"))


EDGE_VALUES = [None, np.nan, math.inf, -math.inf, "", "  ", "abc", "12", -1, 0, 0.0, 1, 1.5, 12, 13, 50, 100, 100.5, -5.0, 25.0]


@pytest.mark.parametrize("key", list(MODEL_FIELDS))
def test_vectorized_validation_matches_scalar_rule(key):
    frame = pd.DataFrame({field: [25.0] * len(EDGE_VALUES) for field in MODEL_FIELDS})
    frame["mes"] = 1
    frame[key] = pd.Series(EDGE_VALUES, dtype="object")
    valid, pending = validate_model_inputs(frame)
    for index, value in enumerate(EDGE_VALUES):
        try:
            parse_field(key, value)
            expected = True
        except ValueError:
            expected = False
        assert bool(valid.iat[index]) is expected, (key, value)
        label = MODEL_FIELDS[key].label
        if expected:
            assert pending.iat[index] == "Nenhum"
        else:
            absent = value is None or (isinstance(value, float) and math.isnan(value)) or (isinstance(value, str) and not value.strip())
            assert pending.iat[index] == f"{label} ({'ausente' if absent else 'inválido'})"


def test_optional_fields_may_be_missing_but_required_may_not():
    assert math.isnan(parse_field("incidencia_vizinhos_lag1", None))
    with pytest.raises(ValueError):
        parse_field("incidencia_vizinhos_lag1", -1)
    with pytest.raises(ValueError):
        parse_field("casos_lag1", None)


def test_monthly_predictions_match_single_prediction(analytical_data, use_case):
    monthly = build_monthly(analytical_data, use_case, NEIGHBORS)
    assert len(monthly) == len(analytical_data)
    classified = monthly.loc[monthly["entradas_validas"]]
    assert set(classified["mes"]) == {2}  # jan e abr não têm mês anterior na base
    for _, row in classified.iterrows():
        expected = use_case.execute(build_risk_input(row))
        assert row["prob_alto"] == pytest.approx(expected.probability)
        assert row["risco"] == expected.risk_level.value
    unclassified = monthly.loc[~monthly["entradas_validas"]]
    assert unclassified["prob_alto"].isna().all() and unclassified["risco"].isna().all()
    assert unclassified["campos_pendentes"].str.contains("Casos de dengue no mês anterior (ausente)", regex=False).all()


def test_observed_high_incidence_uses_threshold(analytical_data, use_case):
    monthly = build_monthly(analytical_data, use_case, NEIGHBORS, high_incidence_threshold=300)
    assert monthly.set_index("incidencia_100k")["incidencia_alta_observada"].to_dict() == {
        100: False, 200: False, 300: True, 400: True, 500: True, 600: True,
    }


def test_scenarios_use_typical_climate_and_fixed_case_reference(analytical_data, use_case):
    base = analytical_data.copy()
    base.loc[(base.codigo_ibge == 1) & (base.ano_mes == "2025-01-01"), "temperatura_media"] = 30.0
    # adiciona um ano anterior para que exista clima típico de maio a julho
    previous_year = base.assign(ano_mes=base["ano_mes"] - pd.DateOffset(years=1))
    extra = previous_year.assign(ano_mes=previous_year["ano_mes"] + pd.DateOffset(months=4))
    base = pd.concat([previous_year, extra, base]).drop_duplicates(["codigo_ibge", "ano_mes"], keep="last")
    scenarios = build_scenarios(base, use_case, NEIGHBORS, horizon=3)

    assert sorted(scenarios["ano_mes"].unique()) == list(pd.to_datetime(["2025-05-01", "2025-06-01", "2025-07-01"]))
    assert (scenarios["periodo_referencia"] == pd.Timestamp("2025-04-01")).all()
    by_key = scenarios.set_index(["codigo_ibge", "ano_mes"])
    # casos e incidência de referência: último mês observado (abril), fixos nos três meses
    may = by_key.xs(pd.Timestamp("2025-05-01"), level="ano_mes")
    assert may["casos_lag1"].to_dict() == {1: 50, 2: 60}
    assert may["incidencia_lag1"].to_dict() == {1: 500, 2: 600}
    for column in CASE_FEATURES:
        per_municipality = scenarios.groupby("codigo_ibge")[column].nunique(dropna=False)
        assert (per_municipality == 1).all(), column
    # incidência de 12 meses antes vem do histórico observado
    assert by_key.loc[(1, pd.Timestamp("2025-05-01")), "incidencia_lag12"] == 100
    for _, row in scenarios.loc[scenarios["entradas_validas"]].iterrows():
        assert row["prob_alto"] == pytest.approx(use_case.execute(build_risk_input(row)).probability)


def test_typical_profile_averages_calendar_months(analytical_data, use_case):
    monthly = build_monthly(analytical_data, use_case, NEIGHBORS)
    profile = build_typical_profile(monthly).set_index(["codigo_ibge", "mes"])
    assert profile.loc[(1, 2), "casos_lag1"] == 10
    assert profile.loc[(2, 2), "incidencia_lag1"] == 200
    assert profile.loc[(1, 1), "populacao"] == 1002  # população mais recente


def test_centroid_of_largest_polygon():
    square = [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]
    tiny = [[[10, 10], [10.1, 10], [10.1, 10.1], [10, 10.1], [10, 10]]]
    assert geometry_centroid({"type": "Polygon", "coordinates": square}) == pytest.approx((1, 1))
    assert geometry_centroid({"type": "MultiPolygon", "coordinates": [tiny, square]}) == pytest.approx((1, 1))
