import streamlit as st

from app.ui import charts, components, data, fmt, nav

meta = data.metadata()
threshold = meta["modelo"]["limiar_incidencia_alta"]
municipalities = data.municipalities()
names = municipalities["nome_municipio"].tolist()


def pick(name: str) -> None:
    st.session_state["municipio"] = name


st.title("Meu município", icon=":material/location_city:")
name = st.selectbox(
    "Escolha o município", names, placeholder="Digite o nome do município",
    key="municipio", bind="query-params", **({} if "municipio" in st.session_state else {"index": None}),
)

if name is None:
    st.markdown("Veja quantos casos de dengue houve, em que época do ano eles aparecem e como o município "
                "se compara ao restante do estado.")
    st.caption("Sugestões: os municípios mais populosos.")
    with st.container(horizontal=True):
        for suggestion in municipalities.nlargest(8, "populacao")["nome_municipio"]:
            st.button(suggestion, on_click=pick, args=(suggestion,), key=f"sugestao_{suggestion}")
    st.stop()

info = municipalities.loc[municipalities["nome_municipio"] == name].iloc[0]
code = int(info["codigo_ibge"])
monthly = data.municipality_monthly(code)
state = data.state_monthly()
last, previous = monthly.iloc[-1], monthly.iloc[-2]
last12, prior12 = monthly.tail(12), monthly.iloc[-24:-12]
peak = monthly.loc[monthly["casos"].idxmax()]
epidemic_months = int(monthly["incidencia_alta_observada"].sum())
scenarios = data.scenario_rows(code)
cases_for_epidemic = threshold * info["populacao"] / 1e5

with st.container(horizontal=True, vertical_alignment="center"):
    st.badge(info["mesorregiao"], icon=":material/landscape:", color="blue")
    st.badge(f"Região de {info['regiao_imediata']}", icon=":material/near_me:", color="gray")
    st.badge(f"{fmt.num(info['populacao'])} habitantes", icon=":material/groups:", color="gray")

cards = st.columns([1.4, 1, 1, 1])
with cards[0]:
    components.monthly_cases_metric(
        monthly, f"Casos em {fmt.month_year(last['ano_mes'])}", delta_description="em relação ao mês anterior", key="municipio_mini",
    )
with cards[1]:
    st.metric(
        "Casos nos últimos 12 meses", fmt.num(last12["casos"].sum()),
        fmt.metric_delta(last12["casos"].sum(), prior12["casos"].sum()), delta_color="inverse",
        delta_description="em relação ao ano anterior", border=True, height="stretch",
        help="Soma dos casos nos 12 meses mais recentes, comparada com os 12 meses antes deles.",
    )
with cards[2]:
    st.metric("Maior surto", fmt.month_year(peak["ano_mes"], short=True), border=True, height="stretch",
              help=f"Mês com mais casos desde {fmt.month_year(monthly['ano_mes'].iat[0])}: {fmt.num(peak['casos'])} casos.")
with cards[3]:
    st.metric("Meses em nível epidêmico", fmt.num(epidemic_months), border=True, height="stretch",
              help=f"Meses com {fmt.num(threshold)} casos ou mais por 100 mil habitantes — para {name}, "
                   f"cerca de {fmt.num(cases_for_epidemic)} casos no mês.")

if len(scenarios):
    upcoming = scenarios.iloc[0]
    label = fmt.risk_label(upcoming["risco"])
    message = (f"**Cenário para {fmt.month_year(upcoming['ano_mes'])}: {label.lower()}.** "
               f"Simulação com o clima típico do mês e os casos de {fmt.month_year(upcoming['periodo_referencia'])}.")
    if upcoming["risco"] == "Alto":
        st.error(message, icon=":material/warning:")
    elif upcoming["risco"] == "Baixo":
        st.success(message, icon=":material/check_circle:")
    else:
        st.info(f"Não há dados suficientes para simular {fmt.month_year(upcoming['ano_mes'])}: "
                f"{upcoming['campos_pendentes']}.", icon=":material/info:")

with st.container(horizontal=True):
    st.button("Simular cenários para este município", icon=":material/tune:",
              on_click=nav.open_simulator, args=(name,), key="municipio_simular")
    st.page_link(nav.MAP, label="Ver no mapa", icon=":material/map:")

with st.container(border=True):
    st.subheader("Casos mês a mês")
    st.plotly_chart(charts.cases_bars(monthly), config=charts.PLOTLY_CONFIG,
                    alt=f"Casos de dengue por mês em {name}", key="municipio_casos")

with st.container(border=True):
    st.subheader(f"{name} comparado ao estado")
    st.caption("Para comparar cidades de tamanhos diferentes, usamos casos para cada 100 mil habitantes. "
               "Acima da linha tracejada, a situação é considerada epidêmica.")
    st.plotly_chart(charts.incidence_lines(monthly, state, name, threshold), config=charts.PLOTLY_CONFIG,
                    alt=f"Casos por 100 mil habitantes em {name} e em Santa Catarina", key="municipio_comparacao")

profile = data.calendar_profile(code)
left, right = st.columns(2, gap="medium")
with left:
    with st.container(border=True, height="stretch"):
        st.subheader("Em que época a dengue aparece")
        top_months = sorted(profile.nlargest(3, "casos_medios")["mes"].tolist())
        if profile["casos_medios"].sum() > 0:
            st.markdown("Os meses com mais casos costumam ser **" +
                        ", ".join(fmt.MONTHS[m - 1] for m in top_months[:-1]) + f"** e **{fmt.MONTHS[top_months[-1] - 1]}**.")
        st.plotly_chart(charts.calendar_bars(profile), config=charts.PLOTLY_CONFIG,
                        alt=f"Média de casos por mês do ano em {name}", key="municipio_calendario")
with right:
    with st.container(border=True, height="stretch"):
        st.subheader("Ano a ano")
        st.caption("Cada quadrado é um mês. Quanto mais escuro, mais casos.")
        st.plotly_chart(charts.month_year_heatmap(data.month_year_matrix(code)), config=charts.PLOTLY_CONFIG,
                        alt=f"Mapa de calor de casos por mês e ano em {name}", key="municipio_calor")

with st.container(border=True):
    st.subheader("Clima e casos ao longo do ano")
    climate = st.segmented_control(
        "Comparar com", ["temperatura_media", "precipitacao_total", "umidade_media"], default="temperatura_media",
        required=True, key="municipio_clima",
        format_func={"temperatura_media": "Temperatura", "precipitacao_total": "Chuva", "umidade_media": "Umidade"}.get,
    )
    st.plotly_chart(charts.climate_vs_cases(profile, climate), config=charts.PLOTLY_CONFIG,
                    alt=f"Casos médios e clima por mês do ano em {name}", key="municipio_clima_grafico")
    st.caption("Médias de todos os anos disponíveis. Os casos costumam subir algumas semanas depois do calor e da chuva.")

details = st.expander("Ver os dados mês a mês", icon=":material/table:", on_change="rerun", key="municipio_dados")
if details.open:
    with details:
        table = monthly.assign(previsao=monthly["risco"].map(fmt.risk_label)).sort_values("ano_mes", ascending=False)
        st.dataframe(
            table[["ano_mes", "casos", "incidencia_100k", "temperatura_media", "precipitacao_total", "umidade_media",
                   "previsao", "prob_alto"]].round({"incidencia_100k": 1, "temperatura_media": 1, "umidade_media": 0}),
            hide_index=True, height=400,
            column_config={
                "ano_mes": st.column_config.DateColumn("Mês", format="MM/YYYY", pinned=True),
                "casos": st.column_config.NumberColumn("Casos", format="localized"),
                "incidencia_100k": st.column_config.NumberColumn("Por 100 mil hab.", format="localized"),
                "temperatura_media": st.column_config.NumberColumn("Temperatura (°C)", format="localized"),
                "precipitacao_total": st.column_config.NumberColumn("Chuva (mm)", format="localized"),
                "umidade_media": st.column_config.NumberColumn("Umidade (%)", format="localized"),
                "previsao": st.column_config.TextColumn("Previsão do modelo"),
                "prob_alto": st.column_config.ProgressColumn("Pontuação de risco", format="percent",
                                                             min_value=0, max_value=1, color="#c92a2a"),
            },
            alt=f"Dados mensais de {name}",
        )
