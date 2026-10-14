import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app.main import build_simulator_coverage, build_simulator_url, evaluate_risk_for_row, row_to_input
from src.application.use_cases.dashboard_analytics import DashboardAnalyticsUseCase
from src.infrastructure.data.csv_repository import CsvDataRepository


def test_app_loads_and_predicts(dashboard_data):
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "main.py")
    at = AppTest.from_file(script_path, default_timeout=20).run()

    assert not at.exception
    assert at.title[0].value == "Sistema de Classificacao de Risco de Dengue"
    assert next(m.value for m in at.metric if m.label == "Base gerada em") == "Não registrada"
    assert next(m.value for m in at.metric if m.label == "Último mês disponível na base") == "04/2025"
    assert next(m.value for m in at.metric if m.label == "Atualização dos dados") == "Manual"

    at.number_input[0].set_value(30.0)

    at.button[0].click().run()

    assert not at.exception
    assert len(at.subheader) > 0
    assert at.subheader[0].value == "Resultado da Analise"


def test_build_simulator_url_and_risk_metrics():
    row = {
        "temperatura_media": 25.0,
        "umidade_media": 70.0,
        "precipitacao_total": 100.0,
        "densidade_demografica": 100.0,
        "mes": 1,
        "casos_lag1": 10.0,
        "incidencia_lag1": 5.0,
    }

    url = build_simulator_url(row)

    assert "temperatura_media=25.0" in url
    assert "mes=1" in url
    assert "simulador" in url.lower()

    risk_value, probability = evaluate_risk_for_row(row)

    assert risk_value in {"Baixo", "Alto"}
    assert 0.0 <= probability <= 1.0


@pytest.mark.skipif(
    not Path("data/processed/base_analitica_sc.csv").exists(),
    reason="Base real não disponível localmente; consistência também coberta por dados controlados.",
)
def test_simulator_consistency_with_real_rows_from_dataset():
    df = pd.read_csv("data/processed/base_analitica_sc.csv", parse_dates=["ano_mes"])
    df = DashboardAnalyticsUseCase.prepare_temporal_features(df)
    df = df.dropna(subset=[
        "temperatura_media",
        "umidade_media",
        "precipitacao_total",
        "densidade_demografica",
        "mes",
        "casos_lag1",
        "incidencia_lag1",
    ])

    sample = df.sample(n=10, random_state=42, replace=False)

    for _, row in sample.iterrows():
        row_dict = {
            "temperatura_media": row["temperatura_media"],
            "umidade_media": row["umidade_media"],
            "precipitacao_total": row["precipitacao_total"],
            "densidade_demografica": row["densidade_demografica"],
            "mes": row["mes"],
            "casos_lag1": row["casos_lag1"],
            "incidencia_lag1": row["incidencia_lag1"],
        }

        risk_value, probability = evaluate_risk_for_row(row_dict)
        url = build_simulator_url(row_dict)
        parsed = parse_qs(urlsplit(url).query)

        assert float(parsed["temperatura_media"][0]) == float(row_dict["temperatura_media"])
        assert int(parsed["mes"][0]) == int(row_dict["mes"])
        assert risk_value in {"Baixo", "Alto"}
        assert 0.0 <= probability <= 1.0


def test_table_and_simulator_roundtrip_preserves_all_inputs_and_prediction(analytical_data):
    frame = DashboardAnalyticsUseCase.prepare_temporal_features(analytical_data)
    for _, row in frame.loc[frame["mes"] == 2].iterrows():
        values = {key: value[0] for key, value in parse_qs(urlsplit(build_simulator_url(row)).query).items()}
        assert row_to_input(values) == row_to_input(row)
        simulator_risk, simulator_probability = evaluate_risk_for_row(values)
        table_risk, table_probability = evaluate_risk_for_row(row)
        assert simulator_risk == table_risk
        assert simulator_probability == pytest.approx(table_probability)


def test_dashboard_population_and_detail_table(dashboard_data, monkeypatch):
    original_expander = st.expander

    def expanded_details(label, **kwargs):
        if label == "Detalhamento dos fatores por período":
            kwargs["expanded"] = True
        return original_expander(label, **kwargs)

    monkeypatch.setattr(st, "expander", expanded_details)
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / "app/main.py", default_timeout=20).run()
    assert not at.exception
    assert next(metric.value for metric in at.metric if metric.label == "Populacao") == "3.004"
    table = at.dataframe[0].value
    assert len(table) == len(dashboard_data)
    assert (table["Risco"] == "Dados insuficientes").sum() == 4
    assert table["Simulador"].notna().all()
    for _, row in table.loc[table["Risco"] != "Dados insuficientes"].iterrows():
        inputs = {key: value[0] for key, value in parse_qs(urlsplit(row["Simulador"]).query).items()}
        risk, probability = evaluate_risk_for_row(inputs)
        assert row["Risco"] == risk
        assert row["Probabilidade de risco alto"] == f"{probability:.2%}"

    at.selectbox[1].set_value("Município A").run()
    assert not at.exception
    assert next(metric.value for metric in at.metric if metric.label == "Populacao") == "1.002"
    assert set(at.dataframe[0].value["Município"]) == {"Município A"}


def test_simulator_remains_available_without_csv(monkeypatch):
    def missing_csv(self):
        raise FileNotFoundError("base ausente")

    monkeypatch.setattr(CsvDataRepository, "load", missing_csv)
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / "app/main.py", default_timeout=20).run()
    assert not at.exception
    assert "Base analítica não encontrada" in at.warning[0].value
    at.button[0].click().run()
    assert not at.exception
    assert at.success or at.error


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_incomplete_inputs_produce_links_with_blank_fields(analytical_data, value):
    frame = DashboardAnalyticsUseCase.prepare_temporal_features(analytical_data)
    row = frame.loc[frame["mes"] == 2].iloc[0].copy()
    row["casos_lag1"] = value
    params = parse_qs(urlsplit(build_simulator_url(row)).query, keep_blank_values=True)
    assert params["casos_lag1"] == [""]
    assert float(params["temperatura_media"][0]) == row["temperatura_media"]


def test_incomplete_row_can_be_completed_in_simulator(dashboard_data):
    frame = DashboardAnalyticsUseCase.prepare_temporal_features(dashboard_data)
    row = frame.loc[frame["mes"] == 2].iloc[0].copy()
    row["precipitacao_total"] = float("nan")
    params = {key: value[0] for key, value in parse_qs(
        urlsplit(build_simulator_url(row)).query, keep_blank_values=True
    ).items()}
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / "app/main.py", default_timeout=20)
    at.query_params.update(params)
    at.run()
    assert not at.exception
    assert at.number_input[2].value is None
    assert at.number_input[0].value == row["temperatura_media"]
    assert at.selectbox[0].value == 2
    assert "Chuva acumulada no mês (mm)" in at.warning[0].value
    at.button[0].click().run()
    assert not at.exception
    assert not at.success and not at.error
    assert any("Ainda faltam dados" in warning.value for warning in at.warning)
    at.number_input[2].set_value(150.0)
    at.number_input[0].set_value(30.0)
    at.button[0].click().run()
    assert not at.exception
    assert at.number_input[2].value == 150.0
    assert at.number_input[0].value == 30.0
    assert not at.warning
    assert at.success or at.error


def test_first_month_missing_lags_remain_blank_in_simulator(dashboard_data):
    row = DashboardAnalyticsUseCase.prepare_temporal_features(dashboard_data).iloc[0]
    params = {key: value[0] for key, value in parse_qs(
        urlsplit(build_simulator_url(row)).query, keep_blank_values=True
    ).items()}
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / "app/main.py", default_timeout=20)
    at.query_params.update(params)
    at.run()
    assert not at.exception
    assert at.number_input[4].value is None
    assert at.number_input[5].value is None
    assert "Casos de dengue no mês anterior" in at.warning[0].value


@pytest.mark.parametrize("field,value", [
    ("umidade_media", -1),
    ("umidade_media", 101),
    ("precipitacao_total", -1),
    ("densidade_demografica", -1),
    ("casos_lag1", -1),
    ("incidencia_lag1", -1),
    ("mes", 0),
    ("mes", 13),
    ("mes", 1.5),
    ("temperatura_media", float("inf")),
    ("temperatura_media", float("nan")),
    ("temperatura_media", "abc"),
])
def test_invalid_values_cannot_reach_prediction(analytical_data, field, value):
    row = DashboardAnalyticsUseCase.prepare_temporal_features(analytical_data).loc[lambda frame: frame["mes"] == 2].iloc[0].copy()
    row[field] = value
    with pytest.raises(ValueError):
        row_to_input(row)
    params = parse_qs(urlsplit(build_simulator_url(row)).query, keep_blank_values=True)
    assert params[field] == [""]


def test_invalid_link_values_are_blank_and_can_be_corrected(dashboard_data):
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / "app/main.py", default_timeout=20)
    at.query_params.update({
        "simulador": "1", "temperatura_media": "-5", "umidade_media": "101",
        "precipitacao_total": "-10", "densidade_demografica": "abc",
        "mes": "13", "casos_lag1": "-2", "incidencia_lag1": "inf",
    })
    at.run()
    assert not at.exception
    assert at.number_input[0].value == -5
    assert all(widget.value is None for widget in at.number_input[1:])
    assert at.selectbox[0].value is None
    assert any("Valores inválidos" in caption.value for caption in at.caption)
    at.button[0].click().run()
    assert not at.exception and not at.success and not at.error
    for widget in at.number_input[1:]:
        widget.set_value(0.0)
    at.selectbox[0].set_value(1)
    at.button[0].click().run()
    assert not at.exception and not at.warning
    assert at.success or at.error


@pytest.mark.parametrize("humidity", [0.0, 100.0])
def test_valid_boundary_values_and_negative_temperature(analytical_data, humidity):
    row = DashboardAnalyticsUseCase.prepare_temporal_features(analytical_data).iloc[0].copy()
    row["temperatura_media"] = -5.0
    row["umidade_media"] = humidity
    for field in ("precipitacao_total", "densidade_demografica", "casos_lag1", "incidencia_lag1"):
        row[field] = 0.0
    inputs = row_to_input(row)
    assert inputs.temperatura_media == -5.0
    assert inputs.umidade_media == humidity
    assert inputs.casos_lag1 == 0.0


def test_coverage_identifies_missing_invalid_and_real_zero(analytical_data):
    frame = DashboardAnalyticsUseCase.prepare_temporal_features(analytical_data)
    feb_index = frame.loc[(frame.codigo_ibge == 1) & (frame.mes == 2)].index[0]
    frame.loc[feb_index, "precipitacao_total"] = float("nan")
    frame.loc[feb_index, "umidade_media"] = 101.0
    frame.loc[frame.mes == 1, "precipitacao_total"] = 0.0
    valid, summary, pending = build_simulator_coverage(frame)
    assert valid.sum() == 1
    summary = summary.set_index("Campo")
    assert summary.loc["Chuva acumulada no mês (mm)", "Dados ausentes"] == 1
    assert summary.loc["Chuva acumulada no mês (mm)", "Registros válidos"] == 5
    assert summary.loc["Umidade média do ar (%)", "Valores inválidos"] == 1
    assert "Chuva acumulada no mês (mm) (ausente)" in pending.loc[feb_index]
    assert "Umidade média do ar (%) (inválido)" in pending.loc[feb_index]
    assert pending.loc[valid].eq("Nenhum").all()


def test_dashboard_coverage_and_pending_fields_follow_municipality(dashboard_data, monkeypatch):
    original_expander = st.expander
    def opened_details(label, **kwargs):
        if label == "Detalhamento dos fatores por período":
            kwargs["expanded"] = True
        return original_expander(label, **kwargs)
    monkeypatch.setattr(st, "expander", opened_details)
    at = AppTest.from_file(Path(__file__).resolve().parents[1] / "app/main.py", default_timeout=20).run()
    assert not at.exception
    assert next(m.value for m in at.metric if m.label == "Registros completos para o simulador") == "2 de 6"
    assert next(m.value for m in at.metric if m.label == "Registros para preencher ou corrigir") == "4"
    coverage = at.table[0].value.set_index("Campo")
    assert coverage.loc["Casos de dengue no mês anterior", "Dados ausentes"] == 4
    table = at.dataframe[0].value
    assert table.loc[table.Risco == "Dados insuficientes", "Dados para preencher ou corrigir"].str.contains("Casos de dengue no mês anterior").all()
    assert table.loc[table.Risco != "Dados insuficientes", "Dados para preencher ou corrigir"].eq("Nenhum").all()
    assert table.Simulador.notna().all()
    at.selectbox[1].set_value("Município A").run()
    assert not at.exception
    assert next(m.value for m in at.metric if m.label == "Meses completos para o simulador") == "1 de 3"
    assert next(m.value for m in at.metric if m.label == "Meses para preencher ou corrigir") == "2"
    assert at.table[0].value.set_index("Campo").loc["Casos de dengue no mês anterior", "Dados ausentes"] == 2
