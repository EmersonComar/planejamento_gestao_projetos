import os
import math
from textwrap import wrap
from urllib.parse import urlencode

import altair as alt
import pandas as pd
import streamlit as st

from src.application.use_cases.dashboard_analytics import DashboardAnalyticsUseCase
from src.application.use_cases.predict_risk import PredictRiskUseCase
from src.domain.entities import DengueRiskInput
from src.infrastructure.data.csv_repository import CsvDataRepository
from src.infrastructure.ml.predictor import SklearnPredictor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHART_LABELS = {
    "ano_mes": "Mês e ano",
    "nome_municipio": "Município",
    "casos": "Casos de dengue no mês",
    "casos_total": "Total de casos de dengue",
    "incidencia_100k": "Casos por 100 mil habitantes",
    "incidencia_media": "Média municipal de casos por 100 mil habitantes",
    "temperatura_media": "Temperatura média (°C)",
    "umidade_media": "Umidade média do ar (%)",
    "precipitacao_total": "Chuva acumulada no mês (mm)",
    "precipitacao_total_lag1": "Chuva acumulada no mês anterior (mm)",
    "densidade_demografica": "Habitantes por km²",
    "casos_lag1": "Casos de dengue no mês anterior",
    "incidencia_lag1": "Casos por 100 mil habitantes no mês anterior",
    "remocao_dbo_media": "Remoção média de matéria orgânica no esgoto — DBO (%)",
    "mes": "Mês do ano",
    "Mes": "Mês do ano",
    "Casos": "Total de casos de dengue",
    "Variavel": "Variável do modelo",
    "Peso": "Importância no modelo",
}
MONTH_NAMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]
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
st.html("""
<style>
/* Let chart hover cards show full labels, including units, on narrow screens. */
#vg-tooltip-element {
    max-width: min(560px, calc(100vw - 24px)) !important;
}
#vg-tooltip-element table {
    width: 100%;
    table-layout: fixed;
}
#vg-tooltip-element table tr td.key,
#vg-tooltip-element table tr td.value {
    white-space: normal !important;
    overflow-wrap: anywhere;
    overflow: visible !important;
    text-overflow: clip !important;
    max-width: none !important;
    max-height: none !important;
    display: table-cell !important;
    -webkit-line-clamp: unset !important;
}
#vg-tooltip-element table tr td.key {
    width: 68%;
    text-align: left !important;
    padding-right: 12px !important;
}
</style>
""")


def render_labeled_chart(frame, x, y, kind, *, y_title=None):
    """Use readable names and units in both axes and hover cards."""
    frame = frame.copy()
    x_type = "temporal" if x == "ano_mes" else "nominal" if x in {"nome_municipio", "Variavel", "Mes"} else "quantitative"
    if x == "Mes":
        frame[x] = frame[x].map(dict(enumerate(MONTH_NAMES, start=1)))
    x_label = CHART_LABELS.get(x, x)
    y_label = y_title or CHART_LABELS.get(y, y)
    x_options = {"sort": MONTH_NAMES} if x == "Mes" else {"sort": None} if x_type == "nominal" else {}
    tooltips = [
        alt.Tooltip(x, type=x_type, title=x_label, **({"format": "%m/%Y"} if x_type == "temporal" else {"format": ",.2f"} if x_type == "quantitative" else {})),
        alt.Tooltip(y, type="quantitative", title=y_label, format=",.2f"),
    ]
    for field in ("nome_municipio", "ano_mes"):
        if field in frame.columns and field != x:
            tooltips.insert(0, alt.Tooltip(field, type="temporal" if field == "ano_mes" else "nominal", title=CHART_LABELS[field], **({"format": "%m/%Y"} if field == "ano_mes" else {})))
    chart = alt.Chart(frame)
    if kind == "scatter":
        chart = chart.mark_circle(size=45, opacity=0.6)
    elif kind == "bar":
        chart = chart.mark_bar()
    elif kind == "area":
        chart = chart.mark_area(point=True)
    else:
        chart = chart.mark_line(point=True)
    chart = chart.encode(
        x=alt.X(x, type=x_type, title=wrap(x_label, width=32), **x_options),
        y=alt.Y(y, type="quantitative", title=wrap(y_label, width=32)),
        tooltip=tooltips,
    ).properties(height=320)
    if kind == "bar" and x in {"nome_municipio", "Variavel"}:
        # Give long names their own row instead of truncating vertical labels.
        chart = alt.Chart(frame).mark_bar().encode(
            x=alt.X(y, type="quantitative", title=wrap(y_label, width=48)),
            y=alt.Y(x, type="nominal", title=x_label, sort=None,
                      axis=alt.Axis(labelLimit=0, labelFontSize=12)),
            tooltip=tooltips,
        ).properties(height=max(280, len(frame) * 30))
    st.altair_chart(chart, width="stretch")


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


def parse_simulator_value(key, raw_value):
    label = CHART_LABELS[key]
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{label}: preencha um número válido.") from None
    if not math.isfinite(value):
        raise ValueError(f"{label}: entradas não finitas não são permitidas.")
    if key == "mes" and value not in range(1, 13):
        raise ValueError("O mês deve ser um inteiro entre 1 e 12.")
    if key == "umidade_media" and not 0 <= value <= 100:
        raise ValueError("A umidade média deve estar entre 0% e 100%.")
    if key in {"precipitacao_total", "densidade_demografica", "casos_lag1", "incidencia_lag1"} and value < 0:
        raise ValueError(f"{label}: o valor deve ser igual ou maior que zero.")
    return int(value) if key == "mes" else value


def is_valid_simulator_value(key, value):
    try:
        parse_simulator_value(key, value)
        return True
    except ValueError:
        return False


def row_to_input(row):
    values = {key: parse_simulator_value(key, row.get(key)) for key in SIMULATOR_FIELD_MAP}
    return DengueRiskInput(**values)


def evaluate_risk_for_row(row, use_case: PredictRiskUseCase | None = None):
    if use_case is None:
        use_case = get_use_case()

    result = use_case.execute(row_to_input(row))
    return result.risk_level.value, float(result.probability)


def build_simulator_url(row):
    params = {"simulador": 1}
    for key in SIMULATOR_FIELD_MAP:
        try:
            params[key] = parse_simulator_value(key, row.get(key))
        except ValueError:
            params[key] = ""
    if row.get("nome_municipio"):
        params["municipio"] = row["nome_municipio"]
    if pd.notna(row.get("ano_mes")):
        params["periodo"] = pd.Timestamp(row["ano_mes"]).strftime("%m/%Y")
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

    for key in defaults:
        if key in params or "simulador" in params:
            try:
                defaults[key] = parse_simulator_value(key, params.get(key, ""))
            except ValueError:
                defaults[key] = None
    return defaults


def render_prediction_tab(use_case: PredictRiskUseCase):
    defaults = get_form_defaults_from_query_params()
    source = tuple(sorted(st.query_params.to_dict().items()))
    if st.session_state.get("_simulator_source") != source:
        for key, value in defaults.items():
            st.session_state[key] = value
        st.session_state["_simulator_source"] = source

    municipality = st.query_params.get("municipio")
    period = st.query_params.get("periodo")
    if municipality or period:
        st.caption("Dados carregados: " + " — ".join(value for value in (municipality, period) if value))
    missing = [key for key in SIMULATOR_FIELD_MAP if st.session_state.get(key) is None]
    if missing:
        st.warning("Preencha os dados faltantes para analisar o risco: " + "; ".join(CHART_LABELS[key] for key in missing) + ".")
        if any(st.query_params.get(key, "") and defaults[key] is None for key in missing):
            st.caption("Valores inválidos recebidos pelo link foram deixados em branco. Corrija os campos indicados antes de analisar.")

    with st.form("predict_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            if "temperatura_media" not in st.session_state:
                st.session_state["temperatura_media"] = defaults["temperatura_media"]
            temperatura = st.number_input(
                "Temperatura Media (C)",
                key="temperatura_media",
                value=None,
                placeholder="Preencha o valor",
                help="Media da temperatura em graus Celsius no municipio",
            )

            if "umidade_media" not in st.session_state:
                st.session_state["umidade_media"] = defaults["umidade_media"]
            umidade = st.number_input(
                "Umidade Media (%)",
                min_value=0.0,
                max_value=100.0,
                key="umidade_media",
                value=None,
                placeholder="Preencha o valor",
                help="Umidade relativa média do ar: de 0% a 100%.",
            )

            if "precipitacao_total" not in st.session_state:
                st.session_state["precipitacao_total"] = defaults["precipitacao_total"]
            precipitacao = st.number_input(
                "Precipitacao Total (mm)",
                min_value=0.0,
                key="precipitacao_total",
                value=None,
                placeholder="Preencha o valor",
                help="Total de precipitacao mensal em milimetros",
            )

        with col2:
            if "densidade_demografica" not in st.session_state:
                st.session_state["densidade_demografica"] = defaults["densidade_demografica"]
            densidade = st.number_input(
                "Densidade Demografica",
                min_value=0.0,
                key="densidade_demografica",
                value=None,
                placeholder="Preencha o valor",
                help="Densidade demografica (hab/km2) do municipio",
            )

            if "mes" not in st.session_state:
                st.session_state["mes"] = defaults["mes"]
            mes = st.selectbox(
                "Mes",
                options=list(range(1, 13)),
                index=None,
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
                value=None,
                placeholder="Preencha o valor",
                help="Numero de casos notificados no mes anterior",
            )

            if "incidencia_lag1" not in st.session_state:
                st.session_state["incidencia_lag1"] = defaults["incidencia_lag1"]
            incidencia_lag1 = st.number_input(
                "Incidencia (Mes Anterior)",
                min_value=0.0,
                key="incidencia_lag1",
                value=None,
                placeholder="Preencha o valor",
                help="Taxa de incidencia por 100 mil habitantes no mes anterior",
            )

        submitted = st.form_submit_button("Analisar Risco")

    if submitted:
        values = {
            "temperatura_media": temperatura,
            "umidade_media": umidade,
            "precipitacao_total": precipitacao,
            "densidade_demografica": densidade,
            "mes": mes,
            "casos_lag1": casos_lag1,
            "incidencia_lag1": incidencia_lag1,
        }
        missing = [key for key, value in values.items() if value is None]
        if missing:
            st.warning("Ainda faltam dados: " + "; ".join(CHART_LABELS[key] for key in missing) + ". Preencha esses campos para analisar o risco.")
            return

        try:
            input_data = row_to_input(values)
            result = use_case.execute(input_data)

            st.subheader("Resultado da Analise")

            if result.risk_level.name == "HIGH":
                st.error(f"Risco: {result.risk_level.value} (Probabilidade de risco alto: {result.probability:.2%})")
            else:
                st.success(f"Risco: {result.risk_level.value} (Probabilidade de risco alto: {result.probability:.2%})")

            if result.feature_importances:
                st.subheader("Importância Global das Variáveis no Modelo")
                st.caption("Pesos gerais do modelo; não explicam individualmente este resultado nem comprovam causalidade.")
                df_imp = pd.DataFrame(
                    list(result.feature_importances.items()),
                    columns=["Variavel", "Peso"],
                ).sort_values("Peso", ascending=False)
                df_imp["Variavel"] = df_imp["Variavel"].map(lambda name: CHART_LABELS.get(name, name))
                render_labeled_chart(df_imp, "Variavel", "Peso", "bar")

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
        st.metric("Total de Casos no Período", f"{int(df_full['casos'].sum()):,}".replace(",", "."))
    with col_metric2:
        st.metric("Municipios Monitorados", f"{df_full['codigo_ibge'].nunique()}")
    with col_metric3:
        st.metric("Periodo", f"{df_full['ano_mes'].min().strftime('%Y-%m')} a {df_full['ano_mes'].max().strftime('%Y-%m')}")

    st.subheader("Evolucao Temporal de Casos em SC")
    render_labeled_chart(summary, "ano_mes", "casos_total", "line")

    st.subheader("Incidencia Media (por 100 mil hab.) ao Longo do Tempo")
    render_labeled_chart(summary, "ano_mes", "incidencia_media", "area")

    st.subheader("Variaveis Climaticas ao Longo do Tempo")
    climate_cols = ["temperatura_media", "umidade_media", "precipitacao_total"]
    climate = summary.melt(id_vars="ano_mes", value_vars=climate_cols, var_name="indicador", value_name="valor")
    climate["indicador"] = climate["indicador"].map(CHART_LABELS)
    st.altair_chart(alt.Chart(climate).mark_line(point=True).encode(
        x=alt.X("ano_mes:T", title="Mês e ano"),
        y=alt.Y("valor:Q", title="Valor (unidade indicada na legenda)"),
        color=alt.Color("indicador:N", title="Indicador climático",
                        legend=alt.Legend(orient="bottom", columns=1, labelLimit=0)),
        tooltip=[
            alt.Tooltip("ano_mes:T", title="Mês e ano", format="%m/%Y"),
            alt.Tooltip("indicador:N", title="Indicador e unidade"),
            alt.Tooltip("valor:Q", title="Valor", format=",.2f"),
        ],
    ).properties(height=320), width="stretch")
    st.caption("Cada indicador tem sua própria unidade: temperatura em °C, umidade em % e chuva em mm.")

    st.subheader("Top 15 municipios com maior incidencia acumulada")
    top_mun = top_mun.reset_index(drop=True)
    render_labeled_chart(top_mun, "nome_municipio", "incidencia_100k", "bar", y_title="Soma das incidências mensais (casos por 100 mil habitantes)")

    st.divider()
    st.subheader("Analise por Municipio")
    municipalities = ["Todos"] + repo.get_municipalities()
    selected = st.selectbox("Selecione um municipio", options=municipalities, index=0)

    if selected == "Todos":
        filtered_df = df_full.copy()
        selected_label = "Todos os municipios"
    else:
        filtered_df = df_full.loc[df_full["nome_municipio"] == selected].copy()
        selected_label = selected

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.metric("Total de Casos", f"{int(filtered_df['casos'].sum()):,}".replace(",", "."))
    with col_m2:
        pop_total, pop_period = DashboardAnalyticsUseCase.population_snapshot(filtered_df)
        st.metric("Populacao", f"{int(pop_total):,}".replace(",", ".") if pd.notna(pop_total) else "Indisponível")
        st.caption(f"Municípios com dados no período {pop_period:%Y-%m}; população contada uma vez por município.")

    st.write(f"#### Filtro ativo: {selected_label}")

    st.divider()
    st.subheader("Exploração das Hipóteses")
    st.caption("Gráficos exploratórios de associação; não constituem testes estatísticos ou evidência de causalidade.")

    hypothesis_text = {
        "H1 — Sazonalidade": "Compara a quantidade de casos por mes para identificar padroes sazonais e periodos de maior intensidade da dengue.",
        "H2 — Temperatura": "Avalia a relacao entre temperatura media e incidencia para verificar se calor mais elevado acompanha aumento da transmissao.",
        "H3 — Precipitacao defasada": "Compara a chuva acumulada no mês anterior com os casos por 100 mil habitantes no mês atual, no mesmo município.",
        "H4 — Umidade": "Verifica se a umidade relativa do ar se associa com a incidencia, pois influencia a sobrevivencia e atividade do mosquito.",
        "H5 — Densidade demografica": "Explora se municipios mais densamente povoados apresentam maior propagacao da dengue devido a maior proximidade entre pessoas.",
        "H6 — Saneamento": "Compara a remoção média de matéria orgânica no tratamento de esgoto com os casos por 100 mil habitantes. DBO significa demanda bioquímica de oxigênio; o percentual indica a remoção dessa carga no tratamento.",
        "H7 — Dependencia temporal": "Compara o número de casos de dengue do mês anterior com o número de casos do mês atual, no mesmo município.",
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
            chart_df[["precipitacao_total_lag1", "incidencia_100k"]]
            .dropna()
            .copy()
        )
        umid_df = chart_df[["umidade_media", "incidencia_100k"]].dropna().copy()
        dens_df = chart_df[["densidade_demografica", "incidencia_100k"]].dropna().copy()
        saneamento_df = chart_df[["remocao_dbo_media", "incidencia_100k"]].dropna().copy() if "remocao_dbo_media" in chart_df.columns else None
        lag_df = (
            chart_df[["casos", "casos_lag1"]]
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
        precip_df = chart_df[["precipitacao_total_lag1", "incidencia_100k"]].dropna().copy()
        umid_df = chart_df[["umidade_media", "incidencia_100k"]].dropna().copy()
        dens_df = chart_df[["densidade_demografica", "incidencia_100k"]].dropna().copy()
        saneamento_df = chart_df[["remocao_dbo_media", "incidencia_100k"]].dropna().copy() if "remocao_dbo_media" in chart_df.columns else None
        lag_df = chart_df[["casos", "casos_lag1"]].dropna().copy()

    charts = [
        ("H1 — Sazonalidade", hypothesis_text["H1 — Sazonalidade"], season_df, "bar"),
        ("H2 — Temperatura", hypothesis_text["H2 — Temperatura"], temp_df, "scatter"),
        ("H3 — Precipitacao defasada", hypothesis_text["H3 — Precipitacao defasada"], precip_df, "scatter"),
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
                render_labeled_chart(data, "Mes", "Casos", "bar")
            else:
                data = data.join(chart_df[["nome_municipio", "ano_mes"]])
                if title == "H3 — Precipitacao defasada":
                    render_labeled_chart(data, "precipitacao_total_lag1", "incidencia_100k", "scatter")
                elif title == "H7 — Dependencia temporal":
                    render_labeled_chart(data, "casos_lag1", "casos", "scatter")
                else:
                    render_labeled_chart(data, data.columns[0], data.columns[1], "scatter")

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
            valid = risk_source[list(SIMULATOR_FIELD_MAP)].apply(
                lambda series: series.map(lambda value: is_valid_simulator_value(series.name, value))
            ).all(axis=1)
            risk_source = risk_source.loc[valid]
            risk_inputs = [row_to_input(row) for _, row in risk_source.iterrows()]
            risk_results = get_use_case().execute_batch(risk_inputs)
            detail_table = detail_df.copy()
            detail_table["Risco"] = "Dados insuficientes"
            detail_table["Probabilidade de risco alto"] = "Indisponível"
            detail_table["Simulador"] = filtered_df.apply(build_simulator_url, axis=1)
            if risk_results:
                detail_table.loc[valid, "Risco"] = [result.risk_level.value for result in risk_results]
                detail_table.loc[valid, "Probabilidade de risco alto"] = [f"{result.probability:.2%}" for result in risk_results]
            if not valid.all():
                st.info(f"{int((~valid).sum())} registros sem classificação: faltam entradas válidas ou dados do mês calendário anterior. Abra no simulador para preencher os dados faltantes.")
            detail_table.insert(0, "Município", filtered_df["nome_municipio"])
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
        try:
            render_dashboard_tab(repo)
        except FileNotFoundError:
            st.warning("Base analítica não encontrada. Disponibilize data/processed/base_analitica_sc.csv para consultar o painel. O simulador continua disponível.")


if __name__ == "__main__":
    main()
