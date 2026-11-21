import math

import numpy as np
import streamlit as st

from app.ui import charts, data, fmt
from src.domain.validation import MODEL_FIELDS, OPTIONAL_FIELDS, REQUIRED_FIELDS, build_risk_input, parse_field

model = data.require_predictor()
decision = model.threshold
epidemic = model.high_incidence_threshold or 300.0

st.title("Simulador: e se...?", icon=":material/tune:")
st.markdown("Mude as condições de um mês e veja como o modelo classifica o risco de a dengue chegar ao nível "
            f"epidêmico ({fmt.num(epidemic)} casos prováveis ou mais por 100 mil habitantes no mês).")
mode = st.segmented_control("Modo", ["Simples", "Avançado"], default="Simples", required=True, key="sim_modo",
                            help="O modo simples parte dos valores típicos do município e mostra só o que mais pesa. "
                                 "O avançado permite editar todas as informações usadas pelo modelo.")


def show_result(probability: float, explanation: str, key: str) -> None:
    high = probability >= decision
    st.plotly_chart(charts.risk_gauge(probability, decision), config=charts.PLOTLY_CONFIG, key=key,
                    alt=f"Pontuação de risco: {fmt.pct(probability)}")
    if high:
        st.error(f"**Risco alto.** {explanation}", icon=":material/warning:")
    else:
        st.success(f"**Risco baixo.** {explanation}", icon=":material/check_circle:")
    st.caption(f"A pontuação vai de 0% a 100%. A partir de {fmt.pct(decision)} (traço preto) o modelo classifica "
               "como risco alto. Ela indica semelhança com meses epidêmicos do passado; não é uma previsão de casos.")


def typical_values(code: int, month: int) -> tuple[dict, list[str]]:
    """Atributos típicos do município no mês; completa obrigatórios ausentes com a média do estado."""
    profile = data.typical_profile(code)
    state = data.state_typical_profile()
    row = profile.loc[month] if month in profile.index else state.loc[month]
    values, used_state = {}, []
    for field in MODEL_FIELDS:
        if field == "mes":
            continue
        value = row.get(field, math.nan)
        if fmt.is_missing(value) and MODEL_FIELDS[field].required:
            value = state.at[month, field]
            used_state.append(fmt.FEATURE_LABELS.get(field, field).lower())
        values[field] = float(value) if not fmt.is_missing(value) else math.nan
    values["mes"] = month
    values["populacao"] = float(row.get("populacao", math.nan))
    return values, used_state


def with_cases(values: dict, cases: float, population: float) -> dict:
    """Atualiza os atributos que dependem dos casos do mês anterior, mantendo o resto."""
    updated = dict(values)
    incidence = cases * 1e5 / population
    updated["casos_lag1"] = cases
    updated["incidencia_lag1"] = incidence
    lag2, lag3 = values.get("incidencia_lag2", math.nan), values.get("incidencia_lag3", math.nan)
    updated["crescimento"] = math.log1p(incidence) - math.log1p(lag2) if not math.isnan(lag2) else math.nan
    updated["incidencia_media3"] = (incidence + lag2 + lag3) / 3 if not (math.isnan(lag2) or math.isnan(lag3)) else math.nan
    return updated


# ----------------------------------------------------------------- modo simples
if mode == "Simples":
    municipalities = data.municipalities()
    names = municipalities["nome_municipio"].tolist()
    future = data.scenario_periods()
    if "sim_mes" not in st.session_state:
        st.session_state["sim_mes"] = future[0].month
    if "sim_municipio" not in st.session_state:
        st.session_state["sim_municipio"] = "Florianópolis" if "Florianópolis" in names else names[0]

    with st.container(horizontal=True):
        name = st.selectbox("Município", names, placeholder="Digite o nome do município", key="sim_municipio")
        month = st.selectbox("Mês", list(range(1, 13)), key="sim_mes", format_func=lambda m: fmt.MONTHS[m - 1].capitalize())

    if name is None:
        st.info("Escolha um município para começar. Os valores típicos do mês serão preenchidos automaticamente.",
                icon=":material/touch_app:")
        st.stop()

    info = municipalities.loc[municipalities["nome_municipio"] == name].iloc[0]
    code = int(info["codigo_ibge"])
    population = float(info["populacao"])
    previous_month = 12 if month == 1 else month - 1
    typical, used_state = typical_values(code, month)
    typical = with_cases(typical, float(round(typical["casos_lag1"])), population)
    # mesmos passos dos controles: sem mexer em nada, simulação e "valores típicos" coincidem
    for field in ("temperatura_media", "temperatura_media_lag1"):
        if not fmt.is_missing(typical[field]):
            typical[field] = round(typical[field] * 2) / 2
    typical["precipitacao_total"] = float(min(600, round(typical["precipitacao_total"] / 5) * 5))
    typical["umidade_media"] = float(min(100, max(40, round(typical["umidade_media"]))))
    for field in ("temperatura_media", "temperatura_media_lag1"):
        if not fmt.is_missing(typical[field]):
            typical[field] = min(35.0, max(5.0, typical[field]))
    if fmt.is_missing(typical["densidade_demografica"]):
        st.warning("Este município não tem densidade demográfica registrada; não é possível simular.")
        st.stop()
    monthly = data.municipality_monthly(code)
    last = monthly.iloc[-1]

    suffix = f"{code}_{month}"
    sliders = ("temperatura_media", "temperatura_media_lag1", "precipitacao_total", "umidade_media", "casos_lag1")
    keys = {field: f"sim_{field}_{suffix}" for field in sliders}

    def reset() -> None:
        for key in keys.values():
            st.session_state.pop(key, None)

    def build(values: dict):
        return build_risk_input(values)

    controls, result = st.columns([1, 1], gap="large")
    with controls:
        with st.container(border=True):
            st.markdown(f"**Condições de {fmt.MONTHS[month - 1]} em {name}**")
            st.caption("Começam com os valores típicos (média dos anos anteriores). Mova para simular; as demais "
                       "informações do modelo ficam nos valores típicos.")
            temperature = st.slider("Temperatura média do mês (°C)", 5.0, 35.0, typical["temperatura_media"],
                                    step=0.5, format="%.1f", key=keys["temperatura_media"])
            previous_temperature = typical["temperatura_media_lag1"]
            if not fmt.is_missing(previous_temperature):
                previous_temperature = st.slider(
                    f"Temperatura média de {fmt.MONTHS[previous_month - 1]} (°C)", 5.0, 35.0,
                    previous_temperature, step=0.5, format="%.1f", key=keys["temperatura_media_lag1"],
                    help="O calor do mês anterior acelera a reprodução do mosquito e pesa bastante no modelo.")
            rain = st.slider("Chuva no mês (mm)", 0, 600, int(typical["precipitacao_total"]), step=5,
                             key=keys["precipitacao_total"])
            humidity = st.slider("Umidade do ar (%)", 40, 100, int(typical["umidade_media"]), key=keys["umidade_media"])
            cases = st.number_input(
                f"Casos prováveis em {fmt.MONTHS[previous_month - 1]}", min_value=0, max_value=1_000_000,
                value=int(typical["casos_lag1"]), step=1, key=keys["casos_lag1"],
                help="É a informação que mais pesa no modelo: a dengue se espalha a partir de quem já está doente.",
            )
            st.caption(f"Típico para {fmt.MONTHS[previous_month - 1]}: {fmt.num(typical['casos_lag1'])} casos. "
                       f"Último dado real: {fmt.num(last['casos'])} casos em {fmt.month_year(last['ano_mes'])}.")
            if used_state:
                st.caption(f"Sem histórico de {', '.join(used_state)} neste município; usamos a média do estado.")
            st.button("Voltar aos valores típicos", icon=":material/restart_alt:", on_click=reset)

    values = with_cases({**typical, "temperatura_media": float(temperature), "precipitacao_total": float(rain),
                         "umidade_media": float(humidity), "temperatura_media_lag1": float(previous_temperature)},
                        float(cases), population)
    _, probability = data.predict(build(values))
    _, typical_probability = data.predict(build(typical))
    cases_for_epidemic = epidemic * population / 1e5

    with result:
        with st.container(border=True):
            st.markdown(f"**Resultado para {name} em {fmt.MONTHS[month - 1]}**")
            verb = "indica" if probability >= decision else "não indica"
            show_result(
                probability,
                f"Com essas condições, o modelo {verb} chance de {name} chegar ao nível epidêmico: cerca de "
                f"**{fmt.num(cases_for_epidemic)} casos prováveis ou mais** no mês, para {fmt.num(population)} habitantes.",
                key="sim_gauge",
            )
            difference = probability - typical_probability
            st.metric("Com os valores típicos, a pontuação seria", fmt.pct(typical_probability),
                      delta=f"{'+' if difference > 0 else '-'}{fmt.num(abs(difference) * 100)} pontos"
                      if abs(difference) >= 0.005 else None,
                      delta_color="inverse", delta_description="na sua simulação" if abs(difference) >= 0.005 else None)

    with st.container(border=True):
        st.subheader("O que mais muda o resultado?")
        options = {"casos_lag1": "Casos no mês anterior", "temperatura_media_lag1": "Temperatura do mês anterior",
                   "temperatura_media": "Temperatura do mês", "precipitacao_total": "Chuva"}
        if fmt.is_missing(values["temperatura_media_lag1"]):
            options.pop("temperatura_media_lag1")
        factor = st.segmented_control("Variar", list(options), default="casos_lag1", required=True,
                                      format_func=options.get, key="sim_fator")
        if factor == "casos_lag1":
            top = max(cases_for_epidemic * 1.5, cases * 2, typical["casos_lag1"] * 3, 20)
            grid = np.unique(np.linspace(0, top, 60).round()).tolist()
            axis, unit, decimals = f"Casos em {fmt.MONTHS[previous_month - 1]}", "casos", 0
            variants = [with_cases(values, float(v), population) for v in grid]
        else:
            if factor in ("temperatura_media", "temperatura_media_lag1"):
                grid = np.arange(5.0, 35.5, 0.5).tolist()
                axis = "Temperatura média do mês anterior (°C)" if factor == "temperatura_media_lag1" else "Temperatura média (°C)"
                unit, decimals = "°C", 1
            else:
                grid = list(range(0, 605, 10))
                axis, unit, decimals = "Chuva no mês (mm)", "mm", 0
            variants = [{**values, factor: float(v)} for v in grid]
        probabilities = data.predict_many(tuple(build(v) for v in variants))
        st.plotly_chart(charts.sensitivity_line(grid, probabilities, values[factor], decision, axis, unit, decimals),
                        config=charts.PLOTLY_CONFIG, key="sim_sensibilidade",
                        alt=f"Pontuação de risco conforme {axis.lower()}")
        crossing = next((v for v, p in zip(grid, probabilities) if p >= decision), None)
        others = "mantendo as outras condições como estão"
        if crossing is None:
            st.caption(f"Nessa faixa, {others}, o modelo não chega a indicar risco alto.")
        elif crossing == grid[0]:
            st.caption(f"Nessa faixa, {others}, o modelo indica risco alto em todos os valores.")
        else:
            st.caption(f"{others.capitalize()}, o risco passa a ser alto a partir de cerca de "
                       f"**{fmt.num(crossing, decimals)} {unit}**.")

# --------------------------------------------------------------- modo avançado
else:
    st.caption("Edite as informações usadas pelo modelo. As sete principais são obrigatórias; as demais podem "
               "ficar em branco (o modelo sabe lidar com a ausência delas).")
    defaults = {"temperatura_media": 25.0, "umidade_media": 70.0, "precipitacao_total": 100.0,
                "densidade_demografica": 100.0, "mes": 1, "casos_lag1": 0.0, "incidencia_lag1": 0.0}
    origin = ""
    if data.repository_available():
        municipalities = data.municipalities()
        with st.container(horizontal=True, vertical_alignment="bottom"):
            base_name = st.selectbox("Partir dos valores típicos de", municipalities["nome_municipio"].tolist(),
                                     index=None, placeholder="Nenhum (valores em branco)", key="adv_municipio")
            base_month = st.selectbox("Mês", list(range(1, 13)), key="adv_mes_base",
                                      format_func=lambda m: fmt.MONTHS[m - 1].capitalize())
        if base_name:
            info = municipalities.loc[municipalities["nome_municipio"] == base_name].iloc[0]
            typical, _ = typical_values(int(info["codigo_ibge"]), base_month)
            defaults = with_cases(typical, float(round(typical["casos_lag1"])), float(info["populacao"]))
            origin = f"{int(info['codigo_ibge'])}_{base_month}"

    def field_input(field: str) -> object:
        rule = MODEL_FIELDS[field]
        key = f"adv_{field}_{origin}"
        if field == "mes":
            return st.selectbox(rule.label, list(range(1, 13)), index=int(defaults.get("mes", 1)) - 1, key=key,
                                format_func=lambda m: fmt.MONTHS[m - 1].capitalize())
        value = defaults.get(field)
        value = None if fmt.is_missing(value) else round(float(value), 2)
        return st.number_input(rule.label, value=value, key=key, placeholder="Em branco",
                               min_value=rule.minimum, max_value=rule.maximum)

    with st.form("sim_avancado"):
        raw = {}
        st.markdown("**Informações principais**")
        cols = st.columns(3)
        for index, field in enumerate(REQUIRED_FIELDS):
            with cols[index % 3]:
                raw[field] = field_input(field)
        with st.expander("Outras informações (opcionais)", icon=":material/tune:"):
            cols = st.columns(3)
            for index, field in enumerate(OPTIONAL_FIELDS):
                with cols[index % 3]:
                    raw[field] = field_input(field)
        submitted = st.form_submit_button("Calcular risco", icon=":material/calculate:", type="primary")

    if submitted:
        missing = [MODEL_FIELDS[key].label for key in REQUIRED_FIELDS if raw.get(key) is None]
        errors = []
        for key, value in raw.items():
            if value is None:
                continue
            try:
                parse_field(key, value)
            except ValueError as error:
                errors.append(str(error))
        if missing:
            st.warning("Preencha os campos: " + "; ".join(missing) + ".", icon=":material/edit:")
        elif errors:
            st.error(" ".join(errors), icon=":material/error:")
        else:
            _, probability = data.predict(build_risk_input(raw))
            with st.container(border=True, width=520):
                verb = "indica" if probability >= decision else "não indica"
                show_result(probability, f"Com esses valores, o modelo {verb} condições de nível epidêmico.",
                            key="adv_gauge")
