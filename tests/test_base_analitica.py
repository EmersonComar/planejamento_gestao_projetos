import numpy as np
import pandas as pd
import pytest

from src.application.use_cases import base_analitica as ba

STATIONS = pd.DataFrame({"codigo_estacao": ["A", "B", "C"], "nome_estacao": ["Perto", "Médio", "Longe"],
                         "lat": [-27.0, -27.2, -29.5], "lon": [-49.0, -49.0, -49.0]})
CENTROIDS = pd.DataFrame({"codigo_ibge": [1, 2], "nome": ["Um", "Dois"], "lat": [-27.01, -29.2], "lon": [-49.0, -49.0]})


def test_station_mapping_orders_by_distance_within_limit():
    mapping = ba.station_mapping(STATIONS, CENTROIDS, max_km=60)
    one = mapping[mapping["codigo_ibge"] == 1]
    assert one["codigo_estacao"].tolist() == ["A", "B"]  # C fica a mais de 60 km
    assert one["ordem"].tolist() == [1, 2]
    assert one["distancia_km"].iat[0] == pytest.approx(1.1, abs=0.1)
    assert mapping.loc[mapping["codigo_ibge"] == 2, "codigo_estacao"].tolist() == ["C"]


def test_precipitation_uses_nearest_station_that_measured_the_month():
    mapping = ba.station_mapping(STATIONS, CENTROIDS, max_km=60)
    monthly = pd.DataFrame({
        "codigo_estacao": ["A", "B", "A", "B"],
        "ano_mes": pd.PeriodIndex(["2024-01", "2024-01", "2024-02", "2024-02"], freq="M"),
        "precipitacao_total": [100.0, 120.0, 5.0, 80.0],
        "horas_medidas": [744, 744, 100, 696],  # em fev, a estação A mediu pouco
    })
    rain = ba.precipitation_by_municipality(monthly, mapping).set_index(["codigo_ibge", "ano_mes"])["precipitacao_total"]
    assert rain[(1, pd.Period("2024-01"))] == 100.0   # estação mais próxima
    assert rain[(1, pd.Period("2024-02"))] == 80.0    # cai para a próxima que mediu o mês


def test_month_without_valid_station_stays_missing_instead_of_zero():
    mapping = ba.station_mapping(STATIONS, CENTROIDS, max_km=60)
    monthly = pd.DataFrame({"codigo_estacao": ["A", "B"], "ano_mes": pd.PeriodIndex(["2024-03", "2024-03"], freq="M"),
                            "precipitacao_total": [0.0, 0.0], "horas_medidas": [0, 0]})
    assert ba.precipitation_by_municipality(monthly, mapping).empty


def test_monthly_aggregation_uses_probable_cases_and_monthly_incidence():
    weeks = pd.to_datetime(["2024-01-07", "2024-01-14", "2024-02-04"])
    weekly = pd.DataFrame({
        "data_iniSE": (weeks - pd.Timestamp("1970-01-01")) // pd.Timedelta("1ms"), "codigo_ibge": 1, "nome_municipio": "Um",
        "casprov": [3, 4, 5], "casos": [10, 10, 10], "tempmed": [25, 27, 24], "tempmin": 20, "tempmax": 30,
        "umidmed": 80, "umidmin": 60, "umidmax": 95,
    })
    population = pd.DataFrame({"codigo_ibge": [1], "ano": [2024], "populacao": [10_000]})
    area = pd.DataFrame({"codigo_ibge": [1], "area_km2": [100.0]})
    base = ba.build_base(weekly, population, area, pd.DataFrame(columns=["codigo_ibge", "ano_mes", "precipitacao_total"]),
                         pd.DataFrame(columns=["codigo_ibge", "qtd_ete_ativas", "remocao_dbo_media"]), pd.Period("2024-02", "M"))
    jan = base.iloc[0]
    assert jan["casos"] == 7 and jan["notificacoes"] == 20
    assert jan["incidencia_100k"] == pytest.approx(70.0)
    assert jan["temperatura_media"] == pytest.approx(26.0)
    assert jan["densidade_demografica"] == pytest.approx(100.0)
    assert np.isnan(jan["precipitacao_total"])
