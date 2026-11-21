import plotly.graph_objects as go
import streamlit as st

from app.ui import charts, data, fmt

meta = data.metadata()
state = data.state_monthly()
profile = data.calendar_profile()
threshold = meta["modelo"]["limiar_incidencia_alta"]

st.title("Entenda a dengue em SC", icon=":material/query_stats:")
st.markdown("A dengue é transmitida pelo mosquito *Aedes aegypti*. Calor, chuva e a circulação de pessoas ajudam o "
            "mosquito a se multiplicar e o vírus a se espalhar. Veja o que os dados de Santa Catarina mostram.")

# 1. Sazonalidade
with st.container(border=True):
    st.subheader("1. A dengue tem época", icon=":material/calendar_month:")
    top = sorted(profile.nlargest(3, "casos_medios")["mes"].tolist())
    share = profile.loc[profile["mes"].isin(top), "casos_medios"].sum() / profile["casos_medios"].sum()
    st.markdown(
        f"Em média, **{fmt.pct(share)} dos casos do ano** acontecem em apenas três meses: "
        f"**{fmt.MONTHS[top[0] - 1]}, {fmt.MONTHS[top[1] - 1]} e {fmt.MONTHS[top[2] - 1]}** — o fim do verão e o outono, "
        "depois de semanas de calor e chuva."
    )
    st.plotly_chart(charts.month_year_heatmap(data.month_year_matrix(), height=420), config=charts.PLOTLY_CONFIG,
                    alt="Casos de dengue por mês e ano em Santa Catarina", key="fatores_calor")
    st.caption("Cada quadrado é um mês. Quanto mais escuro, mais casos no estado.")

# 2. Clima
with st.container(border=True):
    st.subheader("2. Calor e chuva preparam o terreno", icon=":material/thermostat:")
    st.markdown("O mosquito se desenvolve mais rápido no calor, e a chuva cria criadouros com água parada. "
                "Repare como os casos sobem **depois** dos meses mais quentes e chuvosos.")
    climate = st.segmented_control(
        "Comparar casos com", ["temperatura_media", "precipitacao_total", "umidade_media"], default="temperatura_media",
        required=True, key="fatores_clima",
        format_func={"temperatura_media": "Temperatura", "precipitacao_total": "Chuva", "umidade_media": "Umidade"}.get,
    )
    st.plotly_chart(charts.climate_vs_cases(profile, climate), config=charts.PLOTLY_CONFIG,
                    alt="Casos médios e clima por mês do ano em Santa Catarina", key="fatores_clima_grafico")
    st.caption("Clima: média dos municípios. Casos: média de cada mês do calendário em todos os anos.")

# 3. Tendência
with st.container(border=True):
    st.subheader("3. Os últimos anos foram os piores", icon=":material/trending_up:")
    yearly = state.groupby(state["ano_mes"].dt.year).agg(casos=("casos", "sum"), meses=("casos", "size")).reset_index()
    full = yearly.loc[yearly["meses"] == 12]
    worst = full.loc[full["casos"].idxmax()]
    early = full.loc[full["ano_mes"] <= full["ano_mes"].min() + 4, "casos"].mean()
    st.markdown(
        f"Em **{int(worst['ano_mes'])}**, Santa Catarina teve **{fmt.num(worst['casos'])} casos** — "
        f"cerca de **{fmt.times_text(worst['casos'] / early)}** a média de {int(full['ano_mes'].min())} a "
        f"{int(full['ano_mes'].min()) + 4}."
    )
    spread = data.municipalities_with_cases_by_year().set_index("ano")["municipios"]
    first_year = int(spread.index.min())
    st.markdown(
        f"A doença também se espalhou: em {first_year}, **{fmt.num(spread[first_year])} municípios** registraram "
        f"algum caso; em {int(worst['ano_mes'])}, foram **{fmt.num(spread[int(worst['ano_mes'])])}** de "
        f"{fmt.num(meta['municipios'])}."
    )
    fig = go.Figure(go.Bar(
        x=yearly["ano_mes"], y=yearly["casos"], marker_color=charts.CASES_COLOR,
        text=yearly["casos"].map(fmt.num), textposition="outside",
        hovertemplate="%{x}: <b>%{text}</b> casos<extra></extra>",
    ))
    fig.update_yaxes(title="Casos no ano", range=[0, yearly["casos"].max() * 1.15])
    fig.update_xaxes(dtick=1, tickformat="d")
    st.plotly_chart(charts.style(fig, height=320, legend=False), config=charts.PLOTLY_CONFIG,
                    alt="Total de casos de dengue por ano em Santa Catarina", key="fatores_anos")

# 4. Regiões
with st.container(border=True):
    st.subheader("4. Algumas regiões são mais atingidas", icon=":material/landscape:")
    end = state["ano_mes"].iat[-1]
    start = state["ano_mes"].iat[-12]
    regions = data.region_summary(start, end)
    st.markdown(f"Casos para cada 100 mil habitantes de {fmt.month_year(start)} a {fmt.month_year(end)}. "
                f"A região mais afetada foi **{regions['mesorregiao'].iat[0]}**.")
    fig = go.Figure(go.Bar(
        x=regions["incidencia_100k"], y=regions["mesorregiao"], orientation="h", marker_color=charts.CASES_COLOR,
        text=regions["incidencia_100k"].map(fmt.num), textposition="outside",
        customdata=regions["casos"].map(fmt.num),
        hovertemplate="%{y}<br><b>%{text}</b> por 100 mil hab. (%{customdata} casos)<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Casos por 100 mil habitantes", range=[0, regions["incidencia_100k"].max() * 1.2])
    st.plotly_chart(charts.style(fig, height=320, legend=False), config=charts.PLOTLY_CONFIG,
                    alt="Casos por 100 mil habitantes por região de Santa Catarina", key="fatores_regioes")

# 5. Modelo
with st.container(border=True):
    st.subheader("5. O que o modelo leva em conta", icon=":material/psychology:")
    groups = fmt.grouped_importance(meta["modelo"]["importancia_global"])
    ranked = sorted(groups, key=groups.get, reverse=True)
    st.markdown(
        "O sistema usa um modelo de aprendizado de máquina que aprendeu com os anos anteriores quando um município "
        f"costuma passar de **{fmt.num(threshold)} casos prováveis por 100 mil habitantes** no mês — o nível "
        f"considerado epidêmico. O que mais pesa é **{ranked[0].lower()}** "
        f"({fmt.pct(groups[ranked[0]])} do peso): a dengue se espalha a partir de quem já está doente. "
        f"Em seguida vêm **{ranked[1].lower()}** ({fmt.pct(groups[ranked[1]])}) e "
        f"**{ranked[2].lower()}** ({fmt.pct(groups[ranked[2]])})."
    )
    st.plotly_chart(charts.importance_bars(groups, {}), config=charts.PLOTLY_CONFIG,
                    alt="Peso de cada grupo de informações nas decisões do modelo", key="fatores_modelo")
    st.caption("Quanto a qualidade do modelo cai quando cada grupo de informações é embaralhado. Mostra associação, não prova causa. A lista completa está em Sobre os dados.")
