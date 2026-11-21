"""Componentes visuais reutilizados entre páginas."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ui import charts, fmt


def monthly_cases_metric(series: pd.DataFrame, label: str, delta_description: str, key: str,
                         help: str | None = None) -> None:
    """Cartão com os casos do último mês e um gráfico rotulado dos últimos 12 meses.

    ``series`` precisa das colunas ``ano_mes`` e ``casos``, em ordem cronológica.
    """
    last, previous = series.iloc[-1], series.iloc[-2]
    window = series.tail(12)
    with st.container(border=True, gap="xsmall"):
        st.metric(
            label, fmt.num(last["casos"]),
            fmt.metric_delta(last["casos"], previous["casos"]), delta_color="inverse",
            delta_description=delta_description, help=help,
        )
        st.plotly_chart(
            charts.mini_month_bars(window), config={"displayModeBar": False}, key=key,
            alt=f"Casos por mês de {fmt.month_year(window['ano_mes'].iat[0])} a {fmt.month_year(window['ano_mes'].iat[-1])}",
        )
        st.caption("Casos por mês no último ano. A barra mais escura é o mês acima.")


PRESETS = ["Últimos 12 meses", "Este ano", "Ano passado", "Toda a série", "Personalizado"]


def period_selector(periods: list[pd.Timestamp], key: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Escolha de um intervalo de meses: atalhos comuns ou intervalo personalizado."""
    first, last = periods[0], periods[-1]
    with st.container(border=True):
        preset = st.segmented_control(
            "Período analisado", PRESETS, default=PRESETS[0], required=True, key=f"{key}_atalho",
            bind="query-params",
            help="Todos os números, o mapa, o ranking e o gráfico desta página usam o mesmo período.",
        )
        if preset == "Este ano":
            start, end = pd.Timestamp(year=last.year, month=1, day=1), last
        elif preset == "Ano passado":
            start, end = pd.Timestamp(year=last.year - 1, month=1, day=1), pd.Timestamp(year=last.year - 1, month=12, day=1)
        elif preset == "Toda a série":
            start, end = first, last
        elif preset == "Personalizado":
            start, end = st.select_slider(
                "Intervalo de meses", options=periods, value=(periods[max(0, len(periods) - 12)], last),
                format_func=lambda value: fmt.month_year(value, short=True), key=f"{key}_intervalo",
            )
        else:
            start, end = periods[max(0, len(periods) - 12)], last
        start, end = max(start, first), min(end, last)
        months = (end.year - start.year) * 12 + end.month - start.month + 1
        st.caption(f":material/date_range: De **{fmt.month_year(start)}** a **{fmt.month_year(end)}** "
                   f"({months} {'mês' if months == 1 else 'meses'}).")
    return start, end


def previous_window(start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Período imediatamente anterior, com o mesmo número de meses."""
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    return start - pd.DateOffset(months=months), start - pd.DateOffset(months=1)


def period_cases_metric(series: pd.DataFrame, previous_total: float | None, label: str, key: str,
                        delta_description: str, help: str | None = None) -> None:
    """Cartão com o total de casos no período e as barras mês a mês (ou ano a ano, em períodos longos)."""
    total = series["casos"].sum()
    with st.container(border=True, gap="xsmall", height="stretch"):
        st.metric(label, fmt.num(total), fmt.metric_delta(total, previous_total), delta_color="inverse",
                  delta_description=delta_description if previous_total else None, help=help)
        if len(series) > 24:
            yearly = series.groupby(series["ano_mes"].dt.year, as_index=False)["casos"].sum()
            yearly["ano_mes"] = pd.to_datetime(yearly["ano_mes"].astype(str) + "-01-01")
            figure, caption = charts.mini_year_bars(yearly), "Casos por ano no período."
        else:
            figure, caption = charts.mini_month_bars(series, highlight_last=False), "Casos por mês no período."
        st.plotly_chart(figure, config={"displayModeBar": False}, key=key,
                        alt=f"Casos de {fmt.month_year(series['ano_mes'].iat[0])} a {fmt.month_year(series['ano_mes'].iat[-1])}")
        st.caption(caption)
