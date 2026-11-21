"""Figuras Plotly padronizadas (pt-BR, rótulos simples, cores de risco)."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from app.ui import fmt

SC_CENTER = {"lat": -27.6, "lon": -51.05}
CASES_COLOR = "#e8590c"
STATE_COLOR = "#868e96"
TEMP_COLOR = "#f08c00"
RAIN_COLOR = "#1c7ed6"
PLOTLY_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["select2d", "lasso2d", "toImage"]}


def style(fig: go.Figure, height: int = 340, legend: bool = True) -> go.Figure:
    fig.update_layout(
        separators=",.",
        height=height,
        margin={"l": 8, "r": 8, "t": 24, "b": 8},
        showlegend=legend,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0, "title": None},
        hoverlabel={"font_size": 14},
        dragmode=False,
    )
    fig.update_yaxes(tickformat=",.0f")
    return fig


# ----- mapa -----

MAP_MODES = {
    "risco": "Risco previsto",
    "incidencia": "Casos por 100 mil habitantes",
    "casos": "Número de casos",
}


def _hover_details(row: pd.Series) -> str:
    lines = []
    if row["tipo"] == "historico":
        lines.append(f"Casos no mês: {fmt.num(row['casos'])}")
        lines.append(f"Por 100 mil habitantes: {fmt.num(row['incidencia_100k'], 1)}")
    else:
        lines.append(f"Casos em {fmt.month_year(row['periodo_referencia'], short=True)} (referência): {fmt.num(row['casos_lag1'])}")
    lines.append(f"Previsão do modelo: <b>{fmt.risk_label(row['risco'])}</b>")
    if not fmt.is_missing(row["prob_alto"]):
        lines.append(f"Pontuação de risco: {fmt.pct(row['prob_alto'])}")
    else:
        lines.append("Faltam dados para prever")
    return "<br>".join(lines)


def choropleth(snapshot: pd.DataFrame, geojson: dict, mode: str, selected: int | None = None) -> go.Figure:
    frame = snapshot.copy()
    if mode == "risco":
        frame["categoria"] = frame["risco"].map(fmt.risk_label)
        order = fmt.RISK_ORDER
        colors = fmt.RISK_COLORS
    elif mode == "incidencia":
        frame["categoria"] = frame["incidencia_100k"].map(fmt.incidence_bin)
        order = [label for label, _ in fmt.INCIDENCE_BINS]
        colors = dict(fmt.INCIDENCE_BINS)
    else:
        frame["categoria"] = frame["casos"].map(fmt.cases_bin)
        order = [label for label, _ in fmt.CASES_BINS]
        colors = dict(fmt.CASES_BINS)
    colors = {fmt.RISK_UNKNOWN: fmt.RISK_COLORS[fmt.RISK_UNKNOWN], **colors}
    order = [label for label in order + [fmt.RISK_UNKNOWN] if label in set(frame["categoria"])] or order
    frame["detalhe"] = frame.apply(_hover_details, axis=1)

    fig = px.choropleth_map(
        frame,
        geojson=geojson,
        locations="codigo_ibge",
        featureidkey="properties.codigo_ibge",
        color="categoria",
        color_discrete_map=colors,
        category_orders={"categoria": order},
        hover_name="nome_municipio",
        custom_data=["detalhe", "codigo_ibge"],
        map_style="carto-positron",
        center=SC_CENTER,
        zoom=6.2,
        opacity=0.85,
    )
    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]}<extra></extra>",
        marker_line_width=0.5,
        marker_line_color="white",
    )
    if selected is not None and (frame["codigo_ibge"] == selected).any():
        fig.add_trace(go.Choroplethmap(
            geojson=geojson, featureidkey="properties.codigo_ibge",
            locations=[selected], z=[1], showscale=False,
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
            marker_line_width=3, marker_line_color="#212529", hoverinfo="skip", showlegend=False,
        ))
    style(fig, height=540)
    fig.update_layout(legend={"title": None, "y": 0.02, "yanchor": "bottom", "x": 0.01, "orientation": "v",
                              "bgcolor": "rgba(255,255,255,0.85)"})
    return fig


def period_choropleth(frame: pd.DataFrame, geojson: dict, period_label: str) -> go.Figure:
    """Mapa da incidência acumulada no período (casos prováveis do período por 100 mil habitantes)."""
    frame = frame.copy()
    frame["categoria"] = frame["incidencia_100k"].map(fmt.period_incidence_bin)
    order = [label for label, _ in fmt.PERIOD_INCIDENCE_BINS]
    colors = dict(fmt.PERIOD_INCIDENCE_BINS)
    frame["detalhe"] = frame.apply(lambda r: (
        f"{period_label}<br>Casos: {fmt.num(r['casos'])}<br>Por 100 mil habitantes: {fmt.num(r['incidencia_100k'], 1)}"
        f"<br>Meses em nível epidêmico: {fmt.num(r['meses_incidencia_alta'])}"), axis=1)
    fig = px.choropleth_map(
        frame, geojson=geojson, locations="codigo_ibge", featureidkey="properties.codigo_ibge",
        color="categoria", color_discrete_map=colors,
        category_orders={"categoria": [label for label in order if label in set(frame["categoria"])] or order},
        hover_name="nome_municipio", custom_data=["detalhe"],
        map_style="carto-positron", center=SC_CENTER, zoom=6.2, opacity=0.85,
    )
    fig.update_traces(hovertemplate="<b>%{hovertext}</b><br>%{customdata[0]}<extra></extra>",
                      marker_line_width=0.5, marker_line_color="white")
    style(fig, height=540)
    fig.update_layout(legend={"title": None, "y": 0.02, "yanchor": "bottom", "x": 0.01, "orientation": "v",
                              "bgcolor": "rgba(255,255,255,0.85)"})
    return fig


# ----- séries temporais -----

def cases_bars(frame: pd.DataFrame, title_hover: str = "Casos", color: str = CASES_COLOR, height: int = 320) -> go.Figure:
    labels = frame["ano_mes"].map(lambda value: fmt.month_year(value))
    fig = go.Figure(go.Bar(
        x=frame["ano_mes"], y=frame["casos"], marker_color=color,
        customdata=list(zip(labels, frame["casos"].map(fmt.num))),
        hovertemplate="%{customdata[0]}<br>" + title_hover + ": <b>%{customdata[1]}</b><extra></extra>",
    ))
    if len(frame) <= 36:  # períodos curtos: meses em português no eixo
        step = 1 if len(frame) <= 12 else 3
        ticks = frame["ano_mes"].iloc[::step]
        fig.update_xaxes(tickvals=ticks, ticktext=[fmt.month_year(t, short=True) for t in ticks])
    else:
        fig.update_xaxes(tickformat="%Y", dtick="M12", ticklabelmode="period")
    fig.update_yaxes(title="Casos por mês", rangemode="tozero")
    return style(fig, height=height, legend=False)


def incidence_lines(municipality: pd.DataFrame, state: pd.DataFrame, name: str, threshold: float) -> go.Figure:
    fig = go.Figure()
    for frame, label, color, width in ((state, "Santa Catarina", STATE_COLOR, 1.5), (municipality, name, CASES_COLOR, 2.5)):
        months = frame["ano_mes"].map(fmt.month_year)
        fig.add_trace(go.Scatter(
            x=frame["ano_mes"], y=frame["incidencia_100k"], name=label, mode="lines",
            line={"color": color, "width": width},
            customdata=list(zip(months, frame["incidencia_100k"].map(lambda v: fmt.num(v, 1)))),
            hovertemplate=label + " — %{customdata[0]}<br>%{customdata[1]} casos por 100 mil<extra></extra>",
        ))
    fig.add_hline(y=threshold, line_dash="dash", line_color=fmt.RISK_COLORS[fmt.RISK_HIGH],
                  annotation_text=f"Nível epidêmico ({fmt.num(threshold)} por 100 mil)", annotation_position="top left")
    fig.update_xaxes(tickformat="%Y", dtick="M12", ticklabelmode="period")
    fig.update_yaxes(title="Casos por 100 mil habitantes", rangemode="tozero")
    return style(fig, height=340)


def month_year_heatmap(matrix: pd.DataFrame, value: str = "casos", height: int = 380) -> go.Figure:
    pivot = matrix.pivot(index="ano", columns="mes", values=value).reindex(columns=range(1, 13))
    decimals = 0 if value == "casos" else 1
    text = pivot.map(lambda v: fmt.num(v, decimals))
    unit = "casos" if value == "casos" else "casos por 100 mil hab."
    fig = go.Figure(go.Heatmap(
        z=pivot.to_numpy(), x=[name.capitalize() for name in fmt.MONTHS_SHORT], y=[str(year) for year in pivot.index],
        colorscale="YlOrRd", customdata=text.to_numpy(), xgap=2, ygap=2,
        hovertemplate="%{x} de %{y}<br><b>%{customdata}</b> " + unit + "<extra></extra>",
        colorbar={"title": {"text": unit.capitalize(), "side": "right"}, "thickness": 12, "tickformat": ",.0f"},
    ))
    fig.update_yaxes(autorange="reversed", type="category")
    return style(fig, height=height, legend=False)


def calendar_bars(profile: pd.DataFrame, value: str = "casos_medios", highlight: int = 3, height: int = 300) -> go.Figure:
    values = profile.set_index("mes")[value].reindex(range(1, 13))
    top = set(values.nlargest(highlight).index)
    colors = [CASES_COLOR if month in top else "#ffd8a8" for month in values.index]
    unit = "casos por mês, em média" if value == "casos_medios" else "casos por 100 mil, em média"
    fig = go.Figure(go.Bar(
        x=[name.capitalize() for name in fmt.MONTHS_SHORT], y=values.to_numpy(), marker_color=colors,
        customdata=values.map(lambda v: fmt.num(v, 0 if value == "casos_medios" else 1)).to_numpy(),
        hovertemplate="%{x}<br><b>%{customdata}</b> " + unit + "<extra></extra>",
    ))
    fig.update_yaxes(title=unit.capitalize(), rangemode="tozero")
    return style(fig, height=height, legend=False)


def climate_vs_cases(profile: pd.DataFrame, climate: str, height: int = 320) -> go.Figure:
    labels = {"temperatura_media": ("Temperatura média (°C)", TEMP_COLOR, 1),
              "precipitacao_total": ("Chuva no mês (mm)", RAIN_COLOR, 0),
              "umidade_media": ("Umidade do ar (%)", "#0ca678", 0)}
    label, color, decimals = labels[climate]
    months = [name.capitalize() for name in fmt.MONTHS_SHORT]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=months, y=profile["casos_medios"], name="Casos (média por mês)", marker_color="#ffc078",
        customdata=profile["casos_medios"].map(fmt.num),
        hovertemplate="%{x}: <b>%{customdata}</b> casos em média<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=months, y=profile[climate], name=label, mode="lines+markers", line={"color": color, "width": 3},
        customdata=profile[climate].map(lambda v: fmt.num(v, decimals)),
        hovertemplate="%{x}: <b>%{customdata}</b> " + label.split(" (")[1].rstrip(")") + "<extra></extra>",
    ), secondary_y=True)
    fig.update_yaxes(title_text="Casos por mês (média)", secondary_y=False, rangemode="tozero")
    fig.update_yaxes(title_text=label, secondary_y=True, showgrid=False)
    return style(fig, height=height)


# ----- modelo -----

def risk_gauge(probability: float, threshold: float, height: int = 250) -> go.Figure:
    high = probability >= threshold
    color = fmt.RISK_COLORS[fmt.RISK_HIGH if high else fmt.RISK_LOW]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=probability * 100,
        number={"suffix": "%", "valueformat": ".0f", "font": {"color": color, "size": 44}},
        gauge={
            "axis": {"range": [0, 100], "ticksuffix": "%", "dtick": 25},
            "bar": {"color": color, "thickness": 0.3},
            "steps": [
                {"range": [0, threshold * 100], "color": "#ebfbee"},
                {"range": [threshold * 100, 100], "color": "#fff5f5"},
            ],
            "threshold": {"line": {"color": "#212529", "width": 3}, "thickness": 0.9, "value": threshold * 100},
        },
    ))
    return style(fig, height=height, legend=False).update_layout(margin={"l": 40, "r": 40, "t": 24, "b": 16})


def sensitivity_line(values: list[float], probabilities: list[float], current: float, threshold: float,
                     axis_title: str, unit: str, decimals: int = 0) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=values, y=[p * 100 for p in probabilities], mode="lines", line={"color": CASES_COLOR, "width": 3, "shape": "hv"},
        customdata=[[fmt.num(v, decimals), fmt.pct(p)] for v, p in zip(values, probabilities)],
        hovertemplate="%{customdata[0]} " + unit + " → pontuação <b>%{customdata[1]}</b><extra></extra>",
    ))
    fig.add_hline(y=threshold * 100, line_dash="dash", line_color=fmt.RISK_COLORS[fmt.RISK_HIGH],
                  annotation_text="A partir daqui: risco alto", annotation_position="top left")
    fig.add_vline(x=current, line_color="#495057", line_width=1,
                  annotation_text="valor escolhido", annotation_position="top right")
    fig.update_yaxes(title="Pontuação de risco (%)", range=[0, 100], ticksuffix="%")
    fig.update_xaxes(title=axis_title)
    return style(fig, height=280, legend=False)


def importance_bars(importances: dict[str, float], labels: dict[str, str], height: int = 300) -> go.Figure:
    frame = pd.DataFrame({"atributo": list(importances), "peso": list(importances.values())})
    frame["peso"] = frame["peso"] / frame["peso"].sum()
    frame["nome"] = frame["atributo"].map(lambda key: labels.get(key, key))
    frame = frame.sort_values("peso")
    fig = go.Figure(go.Bar(
        x=frame["peso"] * 100, y=frame["nome"], orientation="h", marker_color=CASES_COLOR,
        customdata=frame["peso"].map(fmt.pct), text=frame["peso"].map(fmt.pct), textposition="outside",
        hovertemplate="%{y}: <b>%{customdata}</b> do peso total<extra></extra>",
    ))
    fig.update_xaxes(title="Participação nas decisões do modelo (%)", ticksuffix="%", range=[0, frame["peso"].max() * 118])
    return style(fig, height=height, legend=False)


def mini_month_bars(frame: pd.DataFrame, height: int = 120, highlight_last: bool = True) -> go.Figure:
    """Barras compactas dos meses, com o mês no eixo (e o último mês em destaque, se pedido)."""
    labels = frame["ano_mes"].map(lambda value: fmt.month_year(value, short=True)).tolist()
    colors = ["#ffc078"] * (len(frame) - 1) + [CASES_COLOR] if highlight_last else [CASES_COLOR] * len(frame)
    fig = go.Figure(go.Bar(
        x=labels, y=frame["casos"], marker_color=colors,
        customdata=frame["casos"].map(fmt.num),
        hovertemplate="%{x}: <b>%{customdata}</b> casos<extra></extra>",
    ))
    fig.update_xaxes(tickangle=0, tickfont={"size": 10}, tickvals=labels[::3] + ([labels[-1]] if (len(labels) - 1) % 3 else []))
    fig.update_yaxes(visible=False)
    style(fig, height=height, legend=False)
    return fig.update_layout(margin={"l": 0, "r": 0, "t": 4, "b": 0}, bargap=0.25)


def mini_year_bars(frame: pd.DataFrame, height: int = 120) -> go.Figure:
    """Barras compactas por ano (para períodos longos)."""
    labels = frame["ano_mes"].dt.year.astype(str).tolist()
    fig = go.Figure(go.Bar(
        x=labels, y=frame["casos"], marker_color=CASES_COLOR,
        customdata=frame["casos"].map(fmt.num), hovertemplate="%{x}: <b>%{customdata}</b> casos<extra></extra>",
    ))
    fig.update_xaxes(tickangle=0, tickfont={"size": 10}, type="category")
    fig.update_yaxes(visible=False)
    style(fig, height=height, legend=False)
    return fig.update_layout(margin={"l": 0, "r": 0, "t": 4, "b": 0}, bargap=0.25)
