import os
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

from src.application.use_cases.dashboard_analytics import DashboardAnalyticsUseCase
from src.application.use_cases.predict_risk import PredictRiskUseCase
from src.domain.entities import DengueRiskInput
from src.infrastructure.data.csv_repository import CsvDataRepository
from src.infrastructure.ml.predictor import SklearnPredictor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIMULATOR_FIELD_MAP = {
    "temperatura_media": "temperatura_media",
    "umidade_media": "umidade_media",
    "precipitacao_total": "precipitacao_total",
    "densidade_demografica": "densidade_demografica",
    "mes": "mes",
    "casos_lag1": "casos_lag1",
    "incidencia_lag1": "incidencia_lag1",
}

st.set_page_config(page_title="Predicao de Risco de Dengue - SC", layout="wide")


@st.cache_resource
def get_use_case():
    model_path = os.path.join(BASE_DIR, "..", "models", "modelo_baseline_risco_dengue.pkl")
    predictor = SklearnPredictor(model_path)
    return PredictRiskUseCase(predictor)


@st.cache_resource
def get_data_repository():
    csv_path = os.path.join(BASE_DIR, "..", "data", "processed", "base_analitica_sc.csv")
    return CsvDataRepository(csv_path)


@st.cache_resource
def get_dashboard_use_case():
    repo = get_data_repository()
    return DashboardAnalyticsUseCase(repo)


def _as_float(value, default=0.0):
    try:
        if value is None or value == "":
            return float(default)
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def row_to_input(row):
    return DengueRiskInput(
        temperatura_media=_as_float(row.get("temperatura_media", 25.0)),
        umidade_media=_as_float(row.get("umidade_media", 70.0)),
        precipitacao_total=_as_float(row.get("precipitacao_total", 100.0)),
        densidade_demografica=_as_float(row.get("densidade_demografica", 100.0)),
        mes=int(row.get("mes", 1) or 1),
        casos_lag1=_as_float(row.get("casos_lag1", 0.0)),
        incidencia_lag1=_as_float(row.get("incidencia_lag1", 0.0)),
    )


def evaluate_risk_for_row(row, use_case: PredictRiskUseCase | None = None):
    if use_case is None:
        use_case = get_use_case()

    result = use_case.execute(row_to_input(row))
    return result.risk_level.value, float(result.probability)


def build_simulator_url(row):
    params = {
        "simulador": 1,
        "temperatura_media": _as_float(row.get("temperatura_media", 25.0)),
        "umidade_media": _as_float(row.get("umidade_media", 70.0)),
        "precipitacao_total": _as_float(row.get("precipitacao_total", 100.0)),
        "densidade_demografica": _as_float(row.get("densidade_demografica", 100.0)),
        "mes": int(row.get("mes", 1) or 1),
        "casos_lag1": _as_float(row.get("casos_lag1", 0.0)),
        "incidencia_lag1": _as_float(row.get("incidencia_lag1", 0.0)),
    }
    return "?" + urlencode(params)


def get_form_defaults_from_query_params():
    params = st.query_params
    defaults = {
        "temperatura_media": 25.0,
        "umidade_media": 70.0,
        "precipitacao_total": 100.0,
        "densidade_demografica": 100.0,
        "mes": 1,
        "casos_lag1": 0.0,
        "incidencia_lag1": 0.0,
    }

    for key, default in defaults.items():
        if key in params:
            value = params[key]
            if key == "mes":
                defaults[key] = int(value)
            else:
                defaults[key] = float(value)
    if "simulador" in params:
        defaults["temperatura_media"] = float(params.get("temperatura_media", defaults["temperatura_media"]))
        defaults["umidade_media"] = float(params.get("umidade_media", defaults["umidade_media"]))
        defaults["precipitacao_total"] = float(params.get("precipitacao_total", defaults["precipitacao_total"]))
        defaults["densidade_demografica"] = float(params.get("densidade_demografica", defaults["densidade_demografica"]))
        defaults["mes"] = int(params.get("mes", defaults["mes"]))
        defaults["casos_lag1"] = float(params.get("casos_lag1", defaults["casos_lag1"]))
        defaults["incidencia_lag1"] = float(params.get("incidencia_lag1", defaults["incidencia_lag1"]))
    return defaults


def render_prediction_tab(use_case: PredictRiskUseCase):
    defaults = get_form_defaults_from_query_params()
    for key, value in defaults.items():
        if key in st.query_params:
            st.session_state[key] = value
        else:
            st.session_state.setdefault(key, value)

    with st.form("predict_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            if "temperatura_media" not in st.session_state:
                st.session_state["temperatura_media"] = defaults["temperatura_media"]
            temperatura = st.number_input(
                "Temperatura Media (C)",
                key="temperatura_media",
                help="Media da temperatura em graus Celsius no municipio",
            )

            if "umidade_media" not in st.session_state:
                st.session_state["umidade_media"] = defaults["umidade_media"]
            umidade = st.number_input(
                "Umidade Media (%)",
                key="umidade_media",
                help="Percentual medio de umidade relativa do ar no municipio",
            )

            if "precipitacao_total" not in st.session_state:
                st.session_state["precipitacao_total"] = defaults["precipitacao_total"]
            precipitacao = st.number_input(
                "Precipitacao Total (mm)",
                key="precipitacao_total",
                help="Total de precipitacao mensal em milimetros",
            )

        with col2:
            if "densidade_demografica" not in st.session_state:
                st.session_state["densidade_demografica"] = defaults["densidade_demografica"]
            densidade = st.number_input(
                "Densidade Demografica",
                key="densidade_demografica",
                help="Densidade demografica (hab/km2) do municipio",
            )

            if "mes" not in st.session_state:
                st.session_state["mes"] = defaults["mes"]
            mes = st.selectbox(
                "Mes",
                options=list(range(1, 13)),
                index=int(st.session_state.get("mes", defaults["mes"])) - 1,
                key="mes",
                help="Mes do ano (1=Janeiro, 12=Dezembro) para o qual a predicao sera feita",
            )

        with col3:
            if "casos_lag1" not in st.session_state:
                st.session_state["casos_lag1"] = defaults["casos_lag1"]
            casos_lag1 = st.number_input(
                "Casos (Mes Anterior)",
                min_value=0.0,
                key="casos_lag1",
                help="Numero de casos notificados no mes anterior",
            )

            if "incidencia_lag1" not in st.session_state:
                st.session_state["incidencia_lag1"] = defaults["incidencia_lag1"]
            incidencia_lag1 = st.number_input(
                "Incidencia (Mes Anterior)",
                min_value=0.0,
                key="incidencia_lag1",
                help="Taxa de incidencia por 100 mil habitantes no mes anterior",
            )

        submitted = st.form_submit_button("Analisar Risco")

    if submitted:
        input_data = DengueRiskInput(
            temperatura_media=temperatura,
            umidade_media=umidade,
            precipitacao_total=precipitacao,
            densidade_demografica=densidade,
            mes=mes,
            casos_lag1=casos_lag1,
            incidencia_lag1=incidencia_lag1,
        )

        try:
            result = use_case.execute(input_data)

            st.subheader("Resultado da Analise")

            if result.risk_level.name == "HIGH":
                st.error(f"Risco: {result.risk_level.value} (Probabilidade: {result.probability:.2%})")
            else:
                st.success(f"Risco: {result.risk_level.value} (Probabilidade: {result.probability:.2%})")

            if result.feature_importances:
                st.subheader("Fatores de Maior Peso no Modelo")
                df_imp = pd.DataFrame(
                    list(result.feature_importances.items()),
                    columns=["Variavel", "Peso"],
                ).sort_values("Peso", ascending=False)
                st.bar_chart(data=df_imp.set_index("Variavel"))

        except Exception as e:
            st.error(f"Erro ao processar predicao: {str(e)}")


def render_dashboard_tab(repo: CsvDataRepository):
    analytics = get_dashboard_use_case().build_dashboard_snapshot()
    df_full = analytics["df_full"]
    summary = analytics["summary"]
    top_mun = analytics["top_mun"]

    st.subheader("Visao Geral do Estado de Santa Catarina")

    col_metric1, col_metric2, col_metric3 = st.columns(3)
    with col_metric1:
        st.metric("Total de Casos (2015-2025)", f"{int(df_full['casos'].sum()):,}".replace(",", "."))
    with col_metric2:
        st.metric("Municipios Monitorados", f"{df_full['codigo_ibge'].nunique()}")
    with col_metric3:
        st.metric("Periodo", f"{df_full['ano_mes'].min().strftime('%Y-%m')} a {df_full['ano_mes'].max().strftime('%Y-%m')}")

    st.subheader("Evolucao Temporal de Casos em SC")
    st.line_chart(data=summary.set_index("ano_mes")[["casos_total"]])

    st.subheader("Incidencia Media (por 100 mil hab.) ao Longo do Tempo")
    st.area_chart(data=summary.set_index("ano_mes")[["incidencia_media"]])

    st.subheader("Variaveis Climaticas ao Longo do Tempo")
    climate_cols = ["temperatura_media", "umidade_media", "precipitacao_total"]
    st.line_chart(data=summary.set_index("ano_mes")[climate_cols])

    st.subheader("Top 15 municipios com maior incidencia acumulada")
    top_mun = top_mun.reset_index(drop=True)
    st.bar_chart(data=top_mun.set_index("nome_municipio")["incidencia_100k"])

    st.divider()
    st.subheader("Analise por Municipio")
    municipalities = ["Todos"] + repo.get_municipalities()
    selected = st.selectbox("Selecione um municipio", options=municipalities, index=0)

    if selected == "Todos":
        filtered_df = df_full.copy()
        filtered_df["mes"] = filtered_df["ano_mes"].dt.month
        filtered_df["casos_lag1"] = filtered_df.groupby("codigo_ibge")["casos"].shift(1).fillna(0.0)
        filtered_df["incidencia_lag1"] = filtered_df.groupby("codigo_ibge")["incidencia_100k"].shift(1).fillna(0.0)
        selected_label = "Todos os municipios"
    else:
        filtered_df = repo.filter_by_municipality(selected).sort_values("ano_mes").copy()
        filtered_df["mes"] = filtered_df["ano_mes"].dt.month
        filtered_df["casos_lag1"] = filtered_df["casos"].shift(1).fillna(0.0)
        filtered_df["incidencia_lag1"] = filtered_df["incidencia_100k"].shift(1).fillna(0.0)
        selected_label = selected

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Total de Casos", f"{int(filtered_df['casos'].sum()):,}".replace(",", "."))
    with col_m2:
        if selected == "Todos":
            pop_total = int(filtered_df['populacao'].sum())
        else:
            pop_total = int(filtered_df['populacao'].iloc[-1]) if not filtered_df.empty else 0
        st.metric("Populacao", f"{pop_total:,}".replace(",", "."))

    st.write(f"#### Filtro ativo: {selected_label}")

    st.divider()
    st.subheader("Todas as hipoteses testadas")

    hypothesis_text = {
        "H1 — Sazonalidade": "Compara a quantidade de casos por mes para identificar padroes sazonais e periodos de maior intensidade da dengue.",
        "H2 — Temperatura": "Avalia a relacao entre temperatura media e incidencia para verificar se calor mais elevado acompanha aumento da transmissao.",
        "H3 — Precipitacao defasada": "Testa se chuvas anteriores influenciam a incidencia depois um intervalo de tempo, refletindo o ciclo ambiental da doenca.",
        "H4 — Umidade": "Verifica se a umidade relativa do ar se associa com a incidencia, pois influencia a sobrevivencia e atividade do mosquito.",
        "H5 — Densidade demografica": "Explora se municipios mais densamente povoados apresentam maior propagacao da dengue devido a maior proximidade entre pessoas.",
        "H6 — Saneamento": "Analisa se indicadores de saneamento e remocao de DBO estao relacionados com diferencas na incidencia entre municipios.",
        "H7 — Dependencia temporal": "Investiga se os casos do mes anterior ajudam a explicar a incidencia atual, indicando autocorrelacao no comportamento da doenca.",
    }

    if selected == "Todos":
        chart_df = df_full.copy()
        season_df = (
            chart_df.assign(mes=chart_df["ano_mes"].dt.month)
            .groupby("mes", as_index=False)["casos"]
            .sum()
            .rename(columns={"mes": "Mes", "casos": "Casos"})
        )
        temp_df = chart_df[["temperatura_media", "incidencia_100k"]].dropna().copy()
        precip_df = (
            chart_df[["precipitacao_total", "incidencia_100k"]]
            .dropna()
            .copy()
            .assign(precipitacao_total_lag1=lambda frame: frame["precipitacao_total"].shift(1).fillna(0))
        )
        umid_df = chart_df[["umidade_media", "incidencia_100k"]].dropna().copy()
        dens_df = chart_df[["densidade_demografica", "incidencia_100k"]].dropna().copy()
        saneamento_df = chart_df[["remocao_dbo_media", "incidencia_100k"]].dropna().copy() if "remocao_dbo_media" in chart_df.columns else None
        lag_df = (
            chart_df.sort_values(["codigo_ibge", "ano_mes"]).copy()
            .assign(casos_lag1=lambda frame: frame.groupby("codigo_ibge")["casos"].transform(lambda series: series.shift(1).fillna(0)))
            [["casos", "casos_lag1"]]
            .dropna()
            .copy()
        )
    else:
        chart_df = filtered_df.copy()
        season_df = (
            chart_df.assign(mes=chart_df["ano_mes"].dt.month)
            .groupby("mes", as_index=False)["casos"]
            .sum()
            .rename(columns={"mes": "Mes", "casos": "Casos"})
        )
        temp_df = chart_df[["temperatura_media", "incidencia_100k"]].dropna().copy()
        precip_df = chart_df[["precipitacao_total", "incidencia_100k"]].dropna().copy()
        umid_df = chart_df[["umidade_media", "incidencia_100k"]].dropna().copy()
        dens_df = chart_df[["densidade_demografica", "incidencia_100k"]].dropna().copy()
        saneamento_df = chart_df[["remocao_dbo_media", "incidencia_100k"]].dropna().copy() if "remocao_dbo_media" in chart_df.columns else None
        lag_df = chart_df[["casos", "casos_lag1"]].dropna().copy()

    charts = [
        ("H1 — Sazonalidade", hypothesis_text["H1 — Sazonalidade"], season_df.set_index("Mes")["Casos"], "bar"),
        ("H2 — Temperatura", hypothesis_text["H2 — Temperatura"], temp_df, "scatter"),
        ("H3 — Precipitacao defasada", hypothesis_text["H3 — Precipitacao defasada"], precip_df[["precipitacao_total", "incidencia_100k"]].copy(), "scatter"),
        ("H4 — Umidade", hypothesis_text["H4 — Umidade"], umid_df, "scatter"),
        ("H5 — Densidade demografica", hypothesis_text["H5 — Densidade demografica"], dens_df, "scatter"),
        ("H6 — Saneamento", hypothesis_text["H6 — Saneamento"], saneamento_df, "scatter"),
        ("H7 — Dependencia temporal", hypothesis_text["H7 — Dependencia temporal"], lag_df, "scatter"),
    ]

    for title, explanation, data, chart_type in charts:
        with st.expander(title, expanded=False, on_change="rerun") as hypothesis_expander:
            if not hypothesis_expander.open:
                continue
            st.write(explanation)
            if data is None:
                st.info("Dados nao disponiveis para esta hipotese no conjunto atual.")
                continue
            if chart_type == "bar":
                st.bar_chart(data)
            else:
                if title == "H3 — Precipitacao defasada":
                    st.scatter_chart(data=data, x="precipitacao_total", y="incidencia_100k")
                elif title == "H7 — Dependencia temporal":
                    st.scatter_chart(data=data, x="casos_lag1", y="casos")
                else:
                    st.scatter_chart(data=data, x=data.columns[0], y=data.columns[1])

    st.divider()
    st.subheader("Detalhamento dos fatores por periodo")

    if selected == "Todos":
        detail_df = (
            df_full[["ano_mes", "casos", "incidencia_100k", "temperatura_media", "umidade_media", "precipitacao_total", "densidade_demografica", "populacao"]]
            .copy()
            .rename(columns={
                "ano_mes": "Periodo",
                "casos": "Casos",
                "incidencia_100k": "Incidencia (100k hab.)",
                "temperatura_media": "Temperatura Media (C)",
                "umidade_media": "Umidade Media (%)",
                "precipitacao_total": "Precipitacao Total (mm)",
                "densidade_demografica": "Densidade Demografica",
                "populacao": "Populacao",
            })
        )
    else:
        detail_df = filtered_df[["ano_mes", "casos", "incidencia_100k", "temperatura_media", "umidade_media", "precipitacao_total", "densidade_demografica", "populacao"]].copy().rename(columns={
            "ano_mes": "Periodo",
            "casos": "Casos",
            "incidencia_100k": "Incidencia (100k hab.)",
            "temperatura_media": "Temperatura Media (C)",
            "umidade_media": "Umidade Media (%)",
            "precipitacao_total": "Precipitacao Total (mm)",
            "densidade_demografica": "Densidade Demografica",
            "populacao": "Populacao",
        })

    with st.expander("Detalhamento dos fatores por período", expanded=False, on_change="rerun") as details_expander:
        if details_expander.open:
            risk_source = filtered_df[[
                "ano_mes",
                "temperatura_media",
                "umidade_media",
                "precipitacao_total",
                "densidade_demografica",
                "mes",
                "casos_lag1",
                "incidencia_lag1",
            ]].copy()
            risk_inputs = [row_to_input(row) for _, row in risk_source.iterrows()]
            risk_results = get_use_case().execute_batch(risk_inputs)
            detail_table = detail_df.copy()
            detail_table["Risco"] = [result.risk_level.value for result in risk_results]
            detail_table["Probabilidade"] = [f"{result.probability:.2%}" for result in risk_results]
            detail_table["Simulador"] = risk_source.apply(build_simulator_url, axis=1)
            st.dataframe(detail_table.sort_values("Periodo", ascending=False), width="stretch", hide_index=True, height=400, column_config={
                "Simulador": st.column_config.LinkColumn("Simulador", display_text="Abrir no simulador", max_chars=80)
            })


def main():
    st.title("Sistema de Classificacao de Risco de Dengue")

    use_case = get_use_case()
    repo = get_data_repository()

    tab_predicao, tab_dashboard = st.tabs(["Simulador de Risco", "Painel Analitico"])

    with tab_predicao:
        render_prediction_tab(use_case)

    with tab_dashboard:
        render_dashboard_tab(repo)


if __name__ == "__main__":
    main()
