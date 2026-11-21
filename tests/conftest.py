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


def _square(lon, lat, size=0.1):
    return {"type": "Polygon", "coordinates": [[
        [lon, lat], [lon + size, lat], [lon + size, lat + size], [lon, lat + size], [lon, lat],
    ]]}


@pytest.fixture
def app_data_root(tmp_path, analytical_data):
    """Raiz de projeto mínima (CSV, modelo real, malha e regiões) com a base do app gerada."""
    import json
    import shutil
    from pathlib import Path

    from src.infrastructure.data.app_data_builder import AppDataPaths, build_app_data

    paths = AppDataPaths(tmp_path)
    for path in (paths.csv, paths.model, paths.geojson):
        path.parent.mkdir(parents=True, exist_ok=True)
    analytical_data.to_csv(paths.csv, index=False)
    shutil.copy(Path(__file__).resolve().parents[1] / "models" / "modelo_risco_dengue.pkl", paths.model)
    paths.geojson.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": 1, "properties": {"codigo_ibge": 1, "nome": "Município A"}, "geometry": _square(-49.0, -27.0)},
        {"type": "Feature", "id": 2, "properties": {"codigo_ibge": 2, "nome": "Município B"}, "geometry": _square(-50.0, -26.5)},
    ]}))
    pd.DataFrame({
        "codigo_ibge": [1, 2], "nome": ["Município A", "Município B"],
        "mesorregiao": ["Norte", "Oeste"], "microrregiao": ["M1", "M2"],
        "regiao_intermediaria": ["I1", "I2"], "regiao_imediata": ["R1", "R2"],
    }).to_csv(paths.regions, index=False)
    build_app_data(tmp_path)
    return tmp_path
