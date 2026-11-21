import streamlit as st

from app.ui import charts, data, fmt, nav

meta = data.metadata()
threshold = meta["modelo"]["limiar_incidencia_alta"]
history = data.periods()
future = data.scenario_periods()

st.title("Mapa do risco de dengue", icon=":material/map:")
st.markdown("Escolha um mês para ver como cada município estava. Passe o mouse sobre o mapa para ver os números "
            "ou **clique em um município** para abrir o resumo dele.")

with st.container(horizontal=True, vertical_alignment="bottom"):
    view = st.segmented_control(
        "Período", ["Meses passados", "Próximos meses"], default="Meses passados", required=True, key="mapa_visao",
    )
    if view == "Meses passados":
        mode = st.segmented_control(
            "Colorir o mapa por", list(charts.MAP_MODES), format_func=charts.MAP_MODES.get,
            default="incidencia", required=True, key="mapa_modo",
        )
    else:
        mode = "risco"

if view == "Meses passados":
    period = st.select_slider(
        "Mês", options=history, value=history[-1], format_func=lambda value: fmt.month_year(value, short=True),
        key="mapa_mes",
    )
else:
    period = st.segmented_control(
        "Mês", future, default=future[0], required=True, format_func=fmt.month_year, key="mapa_mes_futuro",
    )
    st.warning(
        f"**Isto é uma simulação, não um dado real.** Para {fmt.month_year(period)}, o modelo usou o clima típico desse mês "
        f"em cada município e os casos de {fmt.month_year(history[-1])}, o último mês com dados. Ele não prevê quantos "
        "casos vão acontecer — só indica se as condições lembram meses de risco alto. Quanto mais distante o mês, "
        "menor a confiança.",
        icon=":material/science:",
    )

snapshot = data.map_snapshot(period)
historic = view == "Meses passados"

with st.container(horizontal=True):
    if historic:
        st.metric(f"Casos em {fmt.month_year(period)}", fmt.num(snapshot["casos"].sum()), border=True)
        st.metric("Municípios em nível epidêmico", fmt.num(snapshot["incidencia_alta_observada"].sum()), border=True,
                  help=f"Com {fmt.num(threshold)} casos ou mais por 100 mil habitantes no mês.")
    st.metric("Municípios com risco alto previsto", fmt.num((snapshot["risco"] == "Alto").sum()), border=True,
              help="Classificação do modelo para este mês.")
    st.metric("Sem dados suficientes para prever", fmt.num(snapshot["risco"].isna().sum()), border=True,
              help="Faltam informações como chuva ou casos do mês anterior. Aparecem em cinza no mapa.")

selected_code = st.session_state.get("mapa_codigo")
map_slot, detail_slot = st.columns([3, 1], gap="medium")
with map_slot:
    event = st.plotly_chart(
        charts.choropleth(snapshot, data.geojson(), mode, selected=selected_code),
        on_select="rerun", selection_mode="points", key="mapa_grafico", config=charts.PLOTLY_CONFIG,
        alt=f"Mapa dos municípios de Santa Catarina: {charts.MAP_MODES[mode].lower()} em {fmt.month_year(period)}",
    )
    points = (event or {}).get("selection", {}).get("points", []) if event else []
    if points:
        point = points[0]
        clicked = point.get("location") or (point.get("customdata") or [None, None])[1]
        # A seleção do gráfico persiste entre execuções: só um clique novo muda o município.
        if clicked is not None and int(clicked) != st.session_state.get("mapa_ultimo_clique"):
            st.session_state["mapa_ultimo_clique"] = int(clicked)
            st.session_state["mapa_codigo"] = int(clicked)
            st.rerun()

with detail_slot:
    names = snapshot.sort_values("nome_municipio")
    options = names["codigo_ibge"].tolist()
    labels = dict(zip(names["codigo_ibge"], names["nome_municipio"]))
    code = st.selectbox(
        "Município selecionado", options, index=options.index(selected_code) if selected_code in options else None,
        format_func=labels.get, placeholder="Clique no mapa ou digite", key=f"mapa_busca_{selected_code}",
    )
    if code is not None and code != selected_code:
        st.session_state["mapa_codigo"] = code
        st.rerun()
    if code is None:
        st.caption("Nenhum município selecionado.")
    else:
        row = snapshot.loc[snapshot["codigo_ibge"] == code].iloc[0]
        with st.container(border=True):
            st.markdown(f"#### {row['nome_municipio']}")
            st.caption(row["mesorregiao"] or "")
            label = fmt.risk_label(row["risco"])
            st.badge(label, color={"Risco alto": "red", "Risco baixo": "green"}.get(label, "gray"))
            if historic:
                st.metric("Casos no mês", fmt.num(row["casos"]))
                st.metric("Por 100 mil habitantes", fmt.num(row["incidencia_100k"], 1))
            else:
                st.metric(f"Casos em {fmt.month_year(row['periodo_referencia'], short=True)} (referência)",
                          fmt.num(row["casos_lag1"]))
            if not fmt.is_missing(row["prob_alto"]):
                st.metric("Pontuação de risco do modelo", fmt.pct(row["prob_alto"]),
                          help=f"A partir de {fmt.pct(meta['modelo']['limiar_decisao'])} o modelo classifica como risco alto.")
            else:
                st.caption(f"Faltam dados: {row['campos_pendentes']}.")
            st.button("Ver detalhes", icon=":material/location_city:", width="stretch",
                      on_click=nav.open_municipality, args=(row["nome_municipio"],), key="mapa_ir_municipio")
            st.button("Simular cenários", icon=":material/tune:", width="stretch",
                      on_click=nav.open_simulator, args=(row["nome_municipio"], int(period.month)), key="mapa_ir_simulador")

if historic:
    agreement = snapshot.loc[snapshot["risco"].notna()]
    if len(agreement):
        hits = ((agreement["risco"] == "Alto") == agreement["incidencia_alta_observada"]).mean()
        st.caption(
            f":material/fact_check: Neste mês, a previsão do modelo coincidiu com o que de fato aconteceu "
            f"(passar ou não de {fmt.num(threshold)} casos por 100 mil) em **{fmt.pct(hits)}** dos "
            f"{fmt.num(len(agreement))} municípios com dados completos."
        )

table_box = st.expander("Ver todos os municípios em tabela", icon=":material/table:", on_change="rerun", key="mapa_tabela")
if table_box.open:
    with table_box:
        table = snapshot.assign(previsao=snapshot["risco"].map(fmt.risk_label))
        columns = ["nome_municipio", "mesorregiao", "previsao", "prob_alto"]
        if historic:
            columns[2:2] = ["casos", "incidencia_100k"]
        st.dataframe(
            table[columns].round({"incidencia_100k": 1}).sort_values("prob_alto", ascending=False, na_position="last"),
            hide_index=True, height=420,
            column_config={
                "nome_municipio": st.column_config.TextColumn("Município", pinned=True),
                "mesorregiao": st.column_config.TextColumn("Região"),
                "casos": st.column_config.NumberColumn("Casos", format="localized"),
                "incidencia_100k": st.column_config.NumberColumn("Por 100 mil hab.", format="localized"),
                "previsao": st.column_config.TextColumn("Previsão"),
                "prob_alto": st.column_config.ProgressColumn(
                    "Pontuação de risco", format="percent", min_value=0, max_value=1, color="#c92a2a"),
            },
            alt=f"Tabela de municípios em {fmt.month_year(period)}",
        )
