import pandas as pd
import pytest

from src.application.use_cases.dashboard_analytics import DashboardAnalyticsUseCase
from src.infrastructure.data.csv_repository import CsvDataRepository


def test_lags_use_previous_calendar_month_of_same_municipality(analytical_data):
    frame = DashboardAnalyticsUseCase.prepare_temporal_features(
        analytical_data.sample(frac=1, random_state=7)
    )
    feb = frame.loc[frame["mes"] == 2].set_index("codigo_ibge")
    assert feb["casos_lag1"].to_dict() == {1: 10, 2: 20}
    assert feb["incidencia_lag1"].to_dict() == {1: 100, 2: 200}
    assert feb["precipitacao_total_lag1"].to_dict() == {1: 110, 2: 210}
    assert frame.loc[frame["mes"].isin([1, 4]), [
        "casos_lag1", "incidencia_lag1", "precipitacao_total_lag1"
    ]].isna().all().all()


def test_lags_handle_year_transition_and_preserve_zero(analytical_data):
    frame = analytical_data.iloc[:2].copy()
    frame["codigo_ibge"] = 1
    frame["ano_mes"] = pd.to_datetime(["2024-12-01", "2025-01-01"])
    frame.loc[frame.index[0], "casos"] = 0
    result = DashboardAnalyticsUseCase.prepare_temporal_features(frame)
    assert result.iloc[1]["casos_lag1"] == 0


def test_population_counts_each_municipality_once_in_latest_period(analytical_data):
    population, period = DashboardAnalyticsUseCase.population_snapshot(analytical_data)
    assert population == 3004
    assert period == pd.Timestamp("2025-04-01")


def test_duplicate_municipality_month_is_rejected(analytical_data):
    with pytest.raises(ValueError, match="mais de um registro"):
        DashboardAnalyticsUseCase.prepare_temporal_features(
            pd.concat([analytical_data, analytical_data.iloc[:1]])
        )


def test_precipitation_hypothesis_uses_lag_for_both_filters(dashboard_data):
    analytics = DashboardAnalyticsUseCase(CsvDataRepository("unused.csv"))
    state = analytics.build_dashboard_snapshot()["hypotheses"]["precipitacao"]
    municipality = analytics.build_municipality_snapshot("Município A")["precipitacao_x_incidencia"]
    assert sorted(state["precipitacao_total_lag1"].tolist()) == [110, 210]
    assert municipality["precipitacao_total_lag1"].tolist() == [110]
