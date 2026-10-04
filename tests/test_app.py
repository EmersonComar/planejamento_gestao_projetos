import os
from urllib.parse import parse_qs, urlsplit

import pandas as pd
from streamlit.testing.v1 import AppTest

from app.main import build_simulator_url, evaluate_risk_for_row


def test_app_loads_and_predicts():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "main.py")
    at = AppTest.from_file(script_path).run()

    assert not at.exception
    assert at.title[0].value == "Sistema de Classificacao de Risco de Dengue"

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


def test_simulator_consistency_with_real_rows_from_dataset():
    df = pd.read_csv("data/processed/base_analitica_sc.csv", parse_dates=["ano_mes"])
    df = df.sort_values(["nome_municipio", "ano_mes"]).copy()
    df["mes"] = df["ano_mes"].dt.month
    df["casos_lag1"] = df.groupby("nome_municipio")["casos"].shift(1).fillna(0.0)
    df["incidencia_lag1"] = df.groupby("nome_municipio")["incidencia_100k"].shift(1).fillna(0.0)
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
