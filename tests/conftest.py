import pandas as pd
import pytest


@pytest.fixture
def analytical_data():
    """Controlled monthly data, including a gap and overlapping municipality dates."""
    rows = [
        (1, "Município A", "2025-01-01", 10, 100, 110, 1000),
        (2, "Município B", "2025-01-01", 20, 200, 210, 2000),
        (1, "Município A", "2025-02-01", 30, 300, 130, 1001),
        (2, "Município B", "2025-02-01", 40, 400, 240, 2001),
        (1, "Município A", "2025-04-01", 50, 500, 150, 1002),
        (2, "Município B", "2025-04-01", 60, 600, 260, 2002),
    ]
    frame = pd.DataFrame(rows, columns=[
        "codigo_ibge", "nome_municipio", "ano_mes", "casos",
        "incidencia_100k", "precipitacao_total", "populacao",
    ])
    frame["ano_mes"] = pd.to_datetime(frame["ano_mes"])
    frame["temperatura_media"] = 25.0
    frame["umidade_media"] = 70.0
    frame["densidade_demografica"] = 100.0
    return frame


@pytest.fixture
def dashboard_data(monkeypatch, analytical_data):
    from src.infrastructure.data.csv_repository import CsvDataRepository

    monkeypatch.setattr(CsvDataRepository, "load", lambda self: analytical_data.copy())
    return analytical_data
