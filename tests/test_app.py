import math
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from app.ui import fmt
from src.application.use_cases.predict_risk import PredictRiskUseCase
from src.domain.validation import MODEL_FIELDS, build_risk_input
from src.infrastructure.data.duckdb_repository import AppDataUnavailableError, DuckDbAnalyticsRepository
from src.infrastructure.ml.predictor import SklearnPredictor

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = str(ROOT / "app" / "main.py")
PAGES = ["app_pages/inicio.py", "app_pages/mapa.py", "app_pages/municipio.py",
         "app_pages/fatores.py", "app_pages/simulador.py", "app_pages/sobre.py"]


@pytest.fixture(autouse=True)
def clear_streamlit_caches():
    st.cache_data.clear()
    st.cache_resource.clear()
    yield
    st.cache_data.clear()
    st.cache_resource.clear()


@pytest.fixture(scope="module")
def repo():
    return DuckDbAnalyticsRepository(ROOT)


@pytest.fixture(scope="module")
def use_case():
    return PredictRiskUseCase(SklearnPredictor(str(ROOT / "models" / "modelo_risco_dengue.pkl")))


def open_app(page: str | None = None) -> AppTest:
    at = AppTest.from_file(ENTRYPOINT, default_timeout=60).run()
    if page:
        at.switch_page(page).run()
    return at


def metric(at: AppTest, label: str) -> str:
    return next(m.value for m in at.metric if m.label == label)


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders_without_errors(page):
    at = open_app(page)
    assert not at.exception
    assert at.title


def test_home_metrics_follow_selected_period(repo):
    at = open_app()
    state = repo.state_monthly()
    assert metric(at, "Casos no período") == fmt.num(state.tail(12)["casos"].sum())

    at.segmented_control(key="inicio_atalho").set_value("Toda a série").run()
    assert not at.exception
    assert metric(at, "Casos no período") == fmt.num(state["casos"].sum())
    top = repo.ranking(limit=10_000)
    assert metric(at, "Municípios em nível epidêmico") == fmt.num((top["meses_incidencia_alta"] > 0).sum())

    at.segmented_control(key="inicio_atalho").set_value("Personalizado").run()
    start, end = pd.Timestamp("2024-01-01"), pd.Timestamp("2024-06-01")
    at.select_slider(key="inicio_intervalo").set_value((start, end)).run()
    assert not at.exception
    window = state.loc[state["ano_mes"].between(start, end)]
    assert metric(at, "Casos no período") == fmt.num(window["casos"].sum())
    peak = window.loc[window["casos"].idxmax(), "ano_mes"]
    assert metric(at, "Mês com mais casos") == fmt.month_year(peak, short=True)


def test_map_scenario_is_labeled_as_simulation(repo):
    at = open_app("app_pages/mapa.py")
    at.segmented_control(key="mapa_visao").set_value("Próximos meses").run()
    assert not at.exception
    assert any("simulação" in warning.value for warning in at.warning)
    first = repo.scenario_periods()[0]
    expected = (repo.map_snapshot(first)["risco"] == "Alto").sum()
    assert metric(at, "Municípios com risco alto previsto") == fmt.num(expected)


def test_map_history_and_selection(repo):
    at = open_app("app_pages/mapa.py")
    period = pd.Timestamp("2024-03-01")
    at.select_slider(key="mapa_mes").set_value(period).run()
    snapshot = repo.map_snapshot(period)
    assert metric(at, "Municípios em nível epidêmico") == fmt.num(snapshot["incidencia_alta_observada"].sum())
    code = int(snapshot.loc[snapshot["nome_municipio"] == "Blumenau", "codigo_ibge"].iat[0])
    at.selectbox(key="mapa_busca_None").set_value(code).run()
    assert not at.exception
    assert "Blumenau" in [md.value.strip("# ") for md in at.markdown]


def test_municipality_page(repo):
    at = open_app("app_pages/municipio.py")
    assert at.button(key="sugestao_Joinville")
    at.selectbox(key="municipio").set_value("Joinville").run()
    assert not at.exception
    monthly = repo.monthly(codigo_ibge=4209102)
    assert metric(at, "Casos nos últimos 12 meses") == fmt.num(monthly.tail(12)["casos"].sum())
    assert metric(at, "Meses em nível epidêmico") == fmt.num(monthly["incidencia_alta_observada"].sum())


def _typical_inputs(repo, name: str, month: int) -> dict:
    """Reproduz, de forma independente, os valores iniciais do simulador simples."""
    info = repo.municipalities().set_index("nome_municipio").loc[name]
    row = repo.query("SELECT * FROM perfil_tipico WHERE codigo_ibge = ? AND mes = ?",
                     [int(info["codigo_ibge"]), month]).iloc[0]
    values = {field: row[field] for field in row.index if field in MODEL_FIELDS}
    values["mes"] = month
    population = float(info["populacao"])
    cases = float(round(row["casos_lag1"]))
    incidence = cases * 1e5 / population
    values.update({
        "casos_lag1": cases, "incidencia_lag1": incidence,
        "crescimento": math.log1p(incidence) - math.log1p(row["incidencia_lag2"]),
        "incidencia_media3": (incidence + row["incidencia_lag2"] + row["incidencia_lag3"]) / 3,
        "temperatura_media": round(row["temperatura_media"] * 2) / 2,
        "temperatura_media_lag1": round(row["temperatura_media_lag1"] * 2) / 2,
        "precipitacao_total": float(round(row["precipitacao_total"] / 5) * 5),
        "umidade_media": float(round(row["umidade_media"])),
    })
    return values


def _risk_message(at) -> str:
    return next(m.value for m in [*at.error, *at.success] if m.value.startswith("**Risco"))


def test_simple_simulator_matches_model_with_typical_values(repo, use_case):
    at = open_app("app_pages/simulador.py")
    assert at.selectbox(key="sim_municipio").value == "Florianópolis"
    at.selectbox(key="sim_mes").set_value(4).run()
    assert not at.exception

    inputs = _typical_inputs(repo, "Florianópolis", 4)
    expected = use_case.execute(build_risk_input(inputs))
    label = "Risco alto." if expected.risk_level.value == "Alto" else "Risco baixo."
    assert _risk_message(at).startswith(f"**{label}**")
    assert metric(at, "Com os valores típicos, a pontuação seria") == fmt.pct(expected.probability)

    temperature_key = next(s.key for s in at.slider if s.key.startswith("sim_temperatura_media_lag1_"))
    at.slider(key=temperature_key).set_value(15.0).run()
    assert not at.exception
    changed = use_case.execute(build_risk_input({**inputs, "temperatura_media_lag1": 15.0}))
    label = "Risco alto." if changed.risk_level.value == "Alto" else "Risco baixo."
    assert _risk_message(at).startswith(f"**{label}**")


def test_advanced_simulator_predicts_like_model(use_case):
    at = open_app("app_pages/simulador.py")
    at.segmented_control(key="sim_modo").set_value("Avançado").run()
    # Limites (ex.: chuva >= 0) são aplicados pelo próprio campo; a validação do domínio é testada à parte.
    at.number_input(key="adv_precipitacao_total_").set_value(250.0)
    at.number_input(key="adv_casos_lag1_").set_value(500.0)
    at.number_input(key="adv_incidencia_lag1_").set_value(400.0)
    at.number_input(key="adv_incidencia_vizinhos_lag1_").set_value(350.0)
    at.selectbox(key="adv_mes_").set_value(3)
    at.button[0].click().run()
    assert not at.exception and not at.warning
    expected = use_case.execute(build_risk_input({
        "temperatura_media": 25.0, "umidade_media": 70.0, "precipitacao_total": 250.0,
        "densidade_demografica": 100.0, "mes": 3, "casos_lag1": 500.0, "incidencia_lag1": 400.0,
        "incidencia_vizinhos_lag1": 350.0,
    }))
    label = "Risco alto." if expected.risk_level.value == "Alto" else "Risco baixo."
    assert _risk_message(at).startswith(f"**{label}**")


def test_advanced_simulator_can_start_from_municipality(repo):
    at = open_app("app_pages/simulador.py")
    at.segmented_control(key="sim_modo").set_value("Avançado").run()
    at.selectbox(key="adv_municipio").set_value("Blumenau").run()
    code = int(repo.municipalities().set_index("nome_municipio").loc["Blumenau", "codigo_ibge"])
    assert at.number_input(key=f"adv_temperatura_media_{code}_1").value is not None
    at.button[0].click().run()
    assert not at.exception
    assert _risk_message(at)


def test_navigation_shortcut_opens_simulator_for_municipality():
    at = open_app("app_pages/municipio.py")
    at.selectbox(key="municipio").set_value("Blumenau").run()
    at.button(key="municipio_simular").click().run()
    assert not at.exception
    assert at.selectbox(key="sim_municipio").value == "Blumenau"


def test_missing_app_data_shows_message_and_keeps_advanced_simulator(monkeypatch):
    def unavailable(self, root, **kwargs):
        raise AppDataUnavailableError("Base do app não encontrada")

    monkeypatch.setattr(DuckDbAnalyticsRepository, "__init__", unavailable)
    at = open_app()
    assert not at.exception
    assert "não estão disponíveis" in at.error[0].value
    at.switch_page("app_pages/simulador.py").run()
    at.segmented_control(key="sim_modo").set_value("Avançado").run()
    at.button[0].click().run()
    assert not at.exception
    assert at.success or at.error


def test_about_page_points_to_project_materials():
    from app.ui import links

    at = open_app("app_pages/sobre.py")
    assert not at.exception
    urls = {button.proto.url for button in at.get("link_button")}
    assert {links.REPO_URL, links.NOTEBOOK_DATA_URL, links.NOTEBOOK_MODEL_URL} <= urls
    assert any(links.REPO_URL in caption.value for caption in at.caption)  # rodapé


def test_simulator_without_trained_model_shows_message(monkeypatch):
    from app.ui import data

    monkeypatch.setattr(data, "model_available", lambda: False)
    at = open_app("app_pages/simulador.py")
    assert not at.exception
    assert "ainda não foi treinado" in at.error[0].value
    assert not at.slider and not at.button


def test_home_lists_epidemic_municipalities(repo):
    at = open_app()
    at.segmented_control(key="inicio_atalho").set_value("Toda a série").run()
    assert not at.exception
    expected = repo.ranking(limit=10_000).query("meses_incidencia_alta > 0")
    listed = next(df.value for df in at.dataframe if "meses_incidencia_alta" in df.value.columns)
    assert set(listed["nome_municipio"]) == set(expected["nome_municipio"])
    assert listed["meses_incidencia_alta"].is_monotonic_decreasing
    assert (listed["incidencia_pico_mensal"] >= 300).all()  # o pico mensal é o que se compara com o limiar
