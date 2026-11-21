import math

import numpy as np
import pandas as pd
import pytest

from src.application.use_cases.features import add_model_features, neighbor_table

NEIGHBORS = {1: [2], 2: [1]}


@pytest.fixture
def features(analytical_data):
    return add_model_features(analytical_data.sample(frac=1, random_state=7), NEIGHBORS).set_index(["codigo_ibge", "ano_mes"])


def test_lags_use_previous_calendar_month_and_keep_gaps(features):
    feb = features.xs(pd.Timestamp("2025-02-01"), level="ano_mes")
    assert feb["casos_lag1"].to_dict() == {1: 10, 2: 20}
    assert feb["incidencia_lag1"].to_dict() == {1: 100, 2: 200}
    assert feb["precipitacao_total_lag1"].to_dict() == {1: 110, 2: 210}
    # janeiro não tem mês anterior e abril vem depois de uma lacuna (março): sem preencher com zero
    for month in ("2025-01-01", "2025-04-01"):
        row = features.xs(pd.Timestamp(month), level="ano_mes")
        assert row["casos_lag1"].isna().all() and row["incidencia_lag1"].isna().all()
    apr = features.xs(pd.Timestamp("2025-04-01"), level="ano_mes")
    assert apr["incidencia_lag2"].to_dict() == {1: 300, 2: 400}


def test_neighbors_state_and_history(features):
    feb = features.xs(pd.Timestamp("2025-02-01"), level="ano_mes")
    assert feb["incidencia_vizinhos_lag1"].to_dict() == {1: 200, 2: 100}
    assert feb["incidencia_estado_lag1"].iat[0] == pytest.approx((10 + 20) * 1e5 / (1000 + 2000))
    assert feb["incidencia_historica"].to_dict() == {1: 100, 2: 200}
    assert math.isnan(feb["crescimento"].iat[0])  # sem incidência de 2 meses antes
    assert feb["log_populacao"].to_dict() == pytest.approx({1: np.log(1001), 2: np.log(2001)})


def test_year_transition_and_zero_are_preserved(analytical_data):
    frame = analytical_data.iloc[:2].copy()
    frame["codigo_ibge"] = 1
    frame["ano_mes"] = pd.to_datetime(["2024-12-01", "2025-01-01"])
    frame.loc[frame.index[0], "casos"] = 0
    result = add_model_features(frame, {})
    assert result.iloc[1]["casos_lag1"] == 0


def test_duplicate_municipality_month_is_rejected(analytical_data):
    with pytest.raises(ValueError, match="mais de um registro"):
        add_model_features(pd.concat([analytical_data, analytical_data.iloc[:1]]), NEIGHBORS)


def test_neighbor_table_picks_nearest():
    coords = pd.DataFrame({"codigo_ibge": [1, 2, 3], "lat": [-27.0, -27.01, -28.0], "lon": [-49.0, -49.01, -50.0]})
    table = neighbor_table(coords, k=1)
    assert table == {1: [2], 2: [1], 3: [2]} or table[3] == [1]
    assert table[1] == [2] and table[2] == [1]
