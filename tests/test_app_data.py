import json
from pathlib import Path

import pandas as pd
import pytest

from src.application.use_cases.predict_risk import PredictRiskUseCase
from src.domain.validation import build_risk_input
from src.infrastructure.data.app_data_builder import AppDataPaths
from src.infrastructure.data.duckdb_repository import AppDataUnavailableError, DuckDbAnalyticsRepository
from src.infrastructure.ml.predictor import SklearnPredictor
from app.ui import data as app_data

ROOT = Path(__file__).resolve().parents[1]
REAL_PATHS = AppDataPaths(ROOT)


# ----- base real versionada -----

@pytest.mark.skipif(not REAL_PATHS.csv.exists(), reason="Base real não disponível localmente.")
def test_published_app_data_is_up_to_date():
    metadata = json.loads(REAL_PATHS.metadata.read_text(encoding="utf-8"))
    assert {key: metadata[key] for key in REAL_PATHS.source_hashes()} == REAL_PATHS.source_hashes(), (
        "Base do app desatualizada: rode `uv run python scripts/build_data.py`."
    )


@pytest.mark.skipif(not REAL_PATHS.csv.exists(), reason="Base real não disponível localmente.")
def test_published_predictions_match_model_and_csv():
    repo = DuckDbAnalyticsRepository(ROOT)
    monthly = repo.monthly()
    csv = pd.read_csv(REAL_PATHS.csv)
    assert len(monthly) == len(csv)
    assert monthly["casos"].sum() == csv["casos"].sum()
    assert repo.metadata()["municipios_com_geometria"] == csv["codigo_ibge"].nunique()

    use_case = PredictRiskUseCase(SklearnPredictor(str(REAL_PATHS.model)))
    for frame in (monthly, repo.query("SELECT * FROM cenarios")):
        sample = frame.loc[frame["entradas_validas"]].sample(n=200, random_state=1)
        expected = use_case.execute_batch([build_risk_input(row) for _, row in sample.iterrows()])
        assert sample["prob_alto"].tolist() == pytest.approx([output.probability for output in expected])
        assert sample["risco"].tolist() == [output.risk_level.value for output in expected]


# ----- repositório sobre base controlada -----

def test_repository_queries(app_data_root, analytical_data):
    repo = DuckDbAnalyticsRepository(app_data_root)
    assert not repo.is_stale()
    assert [p.strftime("%Y-%m") for p in repo.periods()] == ["2025-01", "2025-02", "2025-04"]
    assert len(repo.scenario_periods()) == 3

    state = repo.state_monthly().set_index("ano_mes")
    feb = state.loc[pd.Timestamp("2025-02-01")]
    assert feb["casos"] == 70 and feb["populacao"] == 3002
    assert feb["incidencia_100k"] == pytest.approx(70 * 1e5 / 3002)
    assert feb["municipios_classificados"] == 2
    assert state["municipios_incidencia_alta"].to_dict() == {
        pd.Timestamp("2025-01-01"): 0, pd.Timestamp("2025-02-01"): 2, pd.Timestamp("2025-04-01"): 2,
    }

    ranking = repo.ranking(limit=1)
    assert ranking["nome_municipio"].tolist() == ["Município B"] and ranking["casos"].iat[0] == 120

    matrix = repo.month_year_matrix(codigo_ibge=1)
    assert matrix["casos"].tolist() == [10, 30, 50]

    municipalities = repo.municipalities().set_index("codigo_ibge")
    assert municipalities.loc[1, "mesorregiao"] == "Norte"
    assert municipalities.loc[1, ["lat", "lon"]].tolist() == pytest.approx([-26.95, -48.95])
    assert municipalities["possui_geometria"].all()
    assert len(repo.geojson()["features"]) == 2


def test_map_snapshot_historic_and_scenario(app_data_root):
    repo = DuckDbAnalyticsRepository(app_data_root)
    historic = repo.map_snapshot("2025-02-01")
    assert set(historic["tipo"]) == {"historico"} and len(historic) == 2
    assert historic["casos"].tolist() == [30, 40] and historic["risco"].notna().all()

    scenario = repo.map_snapshot("2025-06-01")
    assert set(scenario["tipo"]) == {"cenario"} and scenario["casos"].isna().all()
    assert (scenario["periodo_referencia"] == pd.Timestamp("2025-04-01")).all()
    # a base de teste não tem clima de junho: sem classificação e com o motivo registrado
    assert scenario["risco"].isna().all()
    assert scenario["campos_pendentes"].str.contains("(ausente)", regex=False).all()


def test_repository_detects_stale_sources(app_data_root):
    paths = AppDataPaths(app_data_root)
    paths.csv.write_text(paths.csv.read_text() + "\n")
    assert DuckDbAnalyticsRepository(app_data_root).is_stale()


def test_missing_app_data_raises_clear_error(tmp_path):
    with pytest.raises(AppDataUnavailableError, match="Base do app não encontrada"):
        DuckDbAnalyticsRepository(tmp_path)


def test_official_comparison_keeps_last_panel_month_before_latest_bulletin_month(tmp_path, monkeypatch):
    reference_dir = tmp_path / "data" / "referencia"
    reference_dir.mkdir(parents=True)
    reference = pd.DataFrame({
        "ano": [2026, 2026, 2026],
        "mes": [1, 2, 3],
        "casos_provaveis": [10, 20, 30],
        "notificacoes": [100, 200, 300],
        "documento": ["Informe nº 11/2026"] * 3,
        "dados_ate": ["2026-11-03"] * 3,
    })
    reference.to_csv(reference_dir / "dive_sc_dengue_mensal.csv", index=False)

    class Repository:
        def query(self, _query):
            return pd.DataFrame({
                "ano": [2026, 2026],
                "mes": [1, 2],
                "casos_painel": [12, 24],
                "notificacoes_painel": [110, 220],
            })

    monkeypatch.setattr(app_data, "ROOT", tmp_path)
    monkeypatch.setattr(app_data, "require_repository", Repository)
    app_data.official_comparison.clear()
    try:
        comparison = app_data.official_comparison()
    finally:
        app_data.official_comparison.clear()

    assert comparison.loc[0, "meses"] == 2
    assert comparison.loc[0, "casos_dive"] == 30
    assert comparison.loc[0, "casos_painel"] == 36
