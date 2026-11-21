"""Acesso aos dados com cache compartilhado entre sessões."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.application.use_cases.predict_risk import PredictRiskUseCase
from src.domain.entities import DengueRiskInput
from src.infrastructure.data.app_data_builder import AppDataPaths
from src.infrastructure.data.duckdb_repository import AppDataUnavailableError, DuckDbAnalyticsRepository
from src.infrastructure.ml.predictor import SklearnPredictor

ROOT = Path(__file__).resolve().parents[2]


@st.cache_resource(show_spinner=False)
def repository() -> DuckDbAnalyticsRepository:
    return DuckDbAnalyticsRepository(ROOT)


def repository_available() -> bool:
    try:
        repository()
        return True
    except AppDataUnavailableError:
        return False


MAINTAINER_HINT = (
    "Para quem mantém o sistema: execute os notebooks em `notebooks/` (primeiro o de dados, depois o de "
    "modelagem) ou os scripts equivalentes em `scripts/`."
)


def model_available() -> bool:
    return AppDataPaths(ROOT).model.exists()


def require_repository() -> DuckDbAnalyticsRepository:
    """Repositório pronto ou mensagem amigável e interrupção da página."""
    try:
        return repository()
    except AppDataUnavailableError:
        message = "Os dados do painel não estão disponíveis no momento."
        if model_available():
            message += " O simulador continua funcionando no modo avançado."
        st.error(message, icon=":material/error:")
        st.caption(MAINTAINER_HINT)
        st.stop()


def require_predictor() -> SklearnPredictor:
    """Modelo carregado ou mensagem amigável e interrupção da página."""
    if not model_available():
        st.error("O modelo de risco ainda não foi treinado, por isso o simulador está indisponível no momento.",
                 icon=":material/error:")
        st.caption(MAINTAINER_HINT)
        st.stop()
    return predictor()


@st.cache_resource(show_spinner="Carregando o modelo...")
def predictor() -> SklearnPredictor:
    return SklearnPredictor(str(AppDataPaths(ROOT).model))


def risk_use_case() -> PredictRiskUseCase:
    return PredictRiskUseCase(predictor())


@st.cache_data(max_entries=2048, show_spinner=False)
def predict(inputs: DengueRiskInput) -> tuple[str, float]:
    output = risk_use_case().execute(inputs)
    return output.risk_level.value, output.probability


@st.cache_data(max_entries=256, show_spinner=False)
def predict_many(inputs: tuple[DengueRiskInput, ...]) -> list[float]:
    return [output.probability for output in risk_use_case().execute_batch(list(inputs))]


@st.cache_data(show_spinner=False)
def metadata() -> dict:
    return require_repository().metadata()


@st.cache_data(show_spinner=False)
def periods() -> list[pd.Timestamp]:
    return require_repository().periods()


@st.cache_data(show_spinner=False)
def scenario_periods() -> list[pd.Timestamp]:
    return require_repository().scenario_periods()


@st.cache_data(show_spinner=False)
def municipalities() -> pd.DataFrame:
    return require_repository().municipalities()


@st.cache_resource(show_spinner=False)
def geojson() -> dict:
    """Somente leitura: compartilhado sem cópia entre sessões."""
    return require_repository().geojson()


@st.cache_data(show_spinner=False)
def state_monthly() -> pd.DataFrame:
    return require_repository().state_monthly()


@st.cache_data(max_entries=200, show_spinner=False)
def map_snapshot(period: pd.Timestamp) -> pd.DataFrame:
    return require_repository().map_snapshot(period)


@st.cache_data(max_entries=400, show_spinner=False)
def municipality_monthly(codigo_ibge: int) -> pd.DataFrame:
    return require_repository().monthly(codigo_ibge=codigo_ibge)


@st.cache_data(max_entries=400, show_spinner=False)
def calendar_profile(codigo_ibge: int | None = None) -> pd.DataFrame:
    return require_repository().calendar_profile(codigo_ibge)


@st.cache_data(max_entries=400, show_spinner=False)
def month_year_matrix(codigo_ibge: int | None = None) -> pd.DataFrame:
    return require_repository().month_year_matrix(codigo_ibge)


@st.cache_data(max_entries=100, show_spinner=False)
def ranking(start: pd.Timestamp | None, end: pd.Timestamp | None, limit: int = 10) -> pd.DataFrame:
    return require_repository().ranking(start, end, limit)


@st.cache_data(max_entries=400, show_spinner=False)
def scenario_rows(codigo_ibge: int) -> pd.DataFrame:
    return require_repository().query(
        "SELECT * FROM cenarios WHERE codigo_ibge = ? ORDER BY ano_mes", [int(codigo_ibge)]
    )


@st.cache_data(show_spinner="Preparando o arquivo...")
def monthly_csv() -> bytes:
    frame = require_repository().monthly()
    return frame.to_csv(index=False).encode("utf-8")


@st.cache_data(max_entries=100, show_spinner=False)
def region_summary(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Casos e incidência por mesorregião no intervalo (população média do intervalo)."""
    return require_repository().query("""
        WITH por_municipio AS (
            SELECT codigo_ibge, SUM(casos) AS casos, AVG(populacao) AS populacao
            FROM mensal WHERE ano_mes BETWEEN ? AND ? GROUP BY codigo_ibge
        )
        SELECT u.mesorregiao, SUM(p.casos)::BIGINT AS casos,
               SUM(p.casos) * 1e5 / NULLIF(SUM(p.populacao), 0) AS incidencia_100k,
               COUNT(*) AS municipios
        FROM por_municipio p JOIN municipios u USING (codigo_ibge)
        GROUP BY u.mesorregiao ORDER BY incidencia_100k DESC""", [pd.Timestamp(start), pd.Timestamp(end)])


@st.cache_data(show_spinner=False)
def missing_inputs() -> pd.DataFrame:
    """Quantos registros não têm cada entrada do modelo."""
    return require_repository().query("""
        SELECT COUNT(*) FILTER (WHERE temperatura_media IS NULL) AS temperatura_media,
               COUNT(*) FILTER (WHERE umidade_media IS NULL) AS umidade_media,
               COUNT(*) FILTER (WHERE precipitacao_total IS NULL) AS precipitacao_total,
               COUNT(*) FILTER (WHERE densidade_demografica IS NULL) AS densidade_demografica,
               COUNT(*) FILTER (WHERE casos_lag1 IS NULL) AS casos_lag1,
               COUNT(*) AS total
        FROM mensal""")


@st.cache_data(show_spinner=False)
def municipalities_with_cases_by_year() -> pd.DataFrame:
    return require_repository().query("""
        SELECT ano, COUNT(DISTINCT codigo_ibge) FILTER (WHERE casos > 0) AS municipios
        FROM mensal GROUP BY ano ORDER BY ano""")


@st.cache_data(max_entries=400, show_spinner=False)
def typical_profile(codigo_ibge: int) -> pd.DataFrame:
    """Valores típicos de cada atributo do modelo por mês do calendário, para um município."""
    return require_repository().query(
        "SELECT * FROM perfil_tipico WHERE codigo_ibge = ? ORDER BY mes", [int(codigo_ibge)]
    ).set_index("mes")


@st.cache_data(show_spinner=False)
def state_typical_profile() -> pd.DataFrame:
    """Média dos perfis típicos dos municípios (usada quando falta um dado no município)."""
    return require_repository().query(
        "SELECT * EXCLUDE (codigo_ibge) FROM perfil_tipico"
    ).groupby("mes").mean(numeric_only=True)


@st.cache_data(show_spinner=False)
def official_comparison() -> pd.DataFrame:
    """Casos prováveis e notificações: boletins da DIVE/SC × base do painel, por ano."""
    reference = pd.read_csv(ROOT / "data" / "referencia" / "dive_sc_dengue_mensal.csv")
    ours = require_repository().query("""
        SELECT ano, mes, SUM(casos)::BIGINT AS casos_painel, SUM(notificacoes)::BIGINT AS notificacoes_painel
        FROM mensal GROUP BY ano, mes""")
    merged = reference.merge(ours, on=["ano", "mes"], how="inner")
    # o último mês de cada boletim ainda está incompleto: fica fora da comparação
    merged = merged.loc[merged["mes"] < merged.groupby("ano")["mes"].transform("max")]
    summary = merged.groupby(["ano", "documento", "dados_ate"], as_index=False).agg(
        meses=("mes", "count"), casos_dive=("casos_provaveis", "sum"), casos_painel=("casos_painel", "sum"),
        notificacoes_dive=("notificacoes", "sum"), notificacoes_painel=("notificacoes_painel", "sum"),
    )
    summary["diferenca_casos"] = summary["casos_painel"] / summary["casos_dive"] - 1
    summary["diferenca_notificacoes"] = summary["notificacoes_painel"] / summary["notificacoes_dive"] - 1
    return summary


@st.cache_data(max_entries=100, show_spinner=False)
def period_by_municipality(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Casos, incidência acumulada e meses epidêmicos de cada município no intervalo."""
    return require_repository().ranking(start, end, limit=10_000)
