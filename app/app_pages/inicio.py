import streamlit as st

from app.ui import charts, components, data, fmt, nav

meta = data.metadata()
state = data.state_monthly()
threshold = meta["modelo"]["limiar_incidencia_alta"]
periods = state["ano_mes"].tolist()

st.title("Dengue em Santa Catarina", icon=":material/pest_control:")
st.markdown(
    f"Acompanhe os casos de dengue nos **{meta['municipios']} municípios** do estado e veja onde o risco é maior. "
    f"Os dados vão de {fmt.month_year(periods[0])} até **{fmt.month_year(periods[-1])}**."
)

start, end = components.period_selector(periods, key="inicio")
label = fmt.period_text(start, end)
window = state.loc[state["ano_mes"].between(start, end)]
previous_start, previous_end = components.previous_window(start, end)
previous = state.loc[state["ano_mes"].between(previous_start, previous_end)]
has_previous = previous_start >= periods[0]
previous_total = previous["casos"].sum() if has_previous else None
comparison = f"em relação a {fmt.period_text(previous_start, previous_end)}"
by_municipality = data.period_by_municipality(start, end)
period_incidence = window["casos"].sum() * 1e5 / window["populacao"].mean()
previous_incidence = previous["casos"].sum() * 1e5 / previous["populacao"].mean() if has_previous else None
epidemic_municipalities = int((by_municipality["meses_incidencia_alta"] > 0).sum())
peak = window.loc[window["casos"].idxmax()]

cards = st.columns([1.4, 1, 1, 1])
with cards[0]:
    components.period_cases_metric(
        window, previous_total, "Casos no período", key="inicio_mini", delta_description=comparison,
        help="Casos prováveis (confirmados, suspeitos e inconclusivos, sem os descartados), somando todos os municípios.",
    )
with cards[1]:
    st.metric(
        "Casos por 100 mil habitantes", fmt.num(period_incidence),
        fmt.metric_delta(period_incidence, previous_incidence), delta_color="inverse",
        delta_description=comparison if has_previous else None, border=True, height="stretch",
        help="Casos do período para cada 100 mil moradores do estado. Permite comparar períodos com populações diferentes.",
    )
with cards[2]:
    with st.container(border=True, height="stretch", gap="small"):
        st.metric(
            "Municípios em nível epidêmico", fmt.num(epidemic_municipalities),
            help=f"Municípios que, em pelo menos um mês do período, tiveram {fmt.num(threshold)} casos ou mais para "
                 f"cada 100 mil habitantes (de {meta['municipios']} municípios).",
        )
        if epidemic_municipalities:
            epidemic = (by_municipality.loc[by_municipality["meses_incidencia_alta"] > 0,
                                            ["nome_municipio", "meses_incidencia_alta", "incidencia_pico_mensal",
                                             "casos", "populacao"]]
                        .sort_values(["meses_incidencia_alta", "incidencia_pico_mensal"], ascending=False))
            noun = "município" if epidemic_municipalities == 1 else "municípios"
            example = epidemic.iloc[0]
            with st.popover("Ver municípios", icon=":material/list:", width="stretch"):
                st.markdown(f"**{fmt.num(epidemic_municipalities)} {noun} em nível epidêmico** ({label})")
                st.caption(
                    f"O critério é ter, em algum mês, {fmt.num(threshold)} casos ou mais **para cada 100 mil habitantes**, "
                    f"e não {fmt.num(threshold)} casos. Em {example['nome_municipio']}, com {fmt.num(example['populacao'])} "
                    f"habitantes, isso equivale a cerca de {fmt.num(threshold * example['populacao'] / 1e5)} casos num mês."
                )
                st.dataframe(
                    epidemic.drop(columns="populacao").round({"incidencia_pico_mensal": 0}),
                    hide_index=True, height=min(420, 38 + 35 * len(epidemic)),
                    column_config={
                        "nome_municipio": st.column_config.TextColumn("Município"),
                        "meses_incidencia_alta": st.column_config.NumberColumn(
                            "Meses", format="localized", width="small",
                            help=f"Meses com {fmt.num(threshold)} casos ou mais por 100 mil habitantes."),
                        "incidencia_pico_mensal": st.column_config.NumberColumn(
                            "Pico por 100 mil", format="localized",
                            help="Maior número de casos por 100 mil habitantes em um único mês do período."),
                        "casos": st.column_config.NumberColumn(
                            "Casos", format="localized", width="small", help="Total de casos prováveis no período."),
                    },
                    alt=f"Municípios em nível epidêmico de {label}",
                )
        else:
            st.caption("Nenhum município chegou ao nível epidêmico no período.")
with cards[3]:
    st.metric(
        "Mês com mais casos", fmt.month_year(peak["ano_mes"], short=True),
        f"{fmt.num(peak['casos'])} casos", delta_color="off", delta_arrow="off", border=True, height="stretch",
        help="Mês do período com o maior número de casos prováveis no estado.",
    )

left, right = st.columns([3, 2], gap="large")
with left:
    with st.container(border=True):
        st.subheader("Casos por 100 mil habitantes em cada município")
        st.caption(f"Total do período ({label}). Passe o mouse para ver os números.")
        st.plotly_chart(
            charts.period_choropleth(by_municipality, data.geojson(), label), config=charts.PLOTLY_CONFIG,
            alt=f"Mapa de Santa Catarina com casos por 100 mil habitantes de {label}", key="home_map",
        )
        st.page_link(nav.MAP, label="Ver o mapa mês a mês e o risco previsto", icon=":material/arrow_forward:")
with right:
    with st.container(border=True):
        st.subheader("Onde houve mais casos")
        st.caption(f"Período: {label}.")
        top = by_municipality.head(10)
        st.dataframe(
            top[["nome_municipio", "casos", "incidencia_100k"]].round({"incidencia_100k": 0}),
            hide_index=True,
            column_config={
                "nome_municipio": st.column_config.TextColumn("Município"),
                "casos": st.column_config.ProgressColumn(
                    "Casos", format="localized", min_value=0, max_value=max(int(top["casos"].max()), 1), color="#e8590c"),
                "incidencia_100k": st.column_config.NumberColumn(
                    "Por 100 mil hab.", format="localized", help="Casos no período para cada 100 mil moradores."),
            },
            alt=f"Dez municípios com mais casos de {label}",
        )
        st.page_link(nav.MUNICIPALITY, label="Ver um município em detalhe", icon=":material/arrow_forward:")

with st.container(border=True):
    st.subheader("Como os casos evoluíram no estado")
    summary = (f"No período, o mês com mais casos foi **{fmt.month_year(peak['ano_mes'])}**, com "
               f"**{fmt.num(peak['casos'])} casos**.")
    yearly = window.groupby(window["ano_mes"].dt.year)["casos"].sum()
    if len(yearly) > 1:
        summary += f" O ano com mais casos foi **{int(yearly.idxmax())}** ({fmt.num(yearly.max())} casos no período)."
    st.markdown(summary)
    st.plotly_chart(charts.cases_bars(window), config=charts.PLOTLY_CONFIG,
                    alt=f"Casos de dengue por mês em Santa Catarina de {label}", key="home_series")

st.subheader("Como se proteger", icon=":material/health_and_safety:")
with st.container(horizontal=True):
    with st.container(border=True):
        st.markdown("**:material/water_drop: Acabe com a água parada**")
        st.markdown("O mosquito se reproduz em água limpa e parada. Uma vez por semana, esvazie vasos, pneus, "
                    "garrafas e calhas e mantenha caixas d'água tampadas.")
    with st.container(border=True):
        st.markdown("**:material/pest_control: Evite as picadas**")
        st.markdown("Use repelente e telas nas janelas, principalmente nos meses quentes e chuvosos, "
                    "quando o mosquito está mais ativo.")
    with st.container(border=True):
        st.markdown("**:material/emergency: Procure atendimento**")
        st.markdown("Febre alta, dor no corpo, atrás dos olhos ou manchas na pele? Procure uma unidade de saúde, "
                    "beba bastante água e não tome remédios por conta própria.")
