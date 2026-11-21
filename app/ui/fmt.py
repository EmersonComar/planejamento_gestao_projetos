"""Formatação em português do Brasil e vocabulário para o público leigo."""
from __future__ import annotations

import math

import pandas as pd

MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
MONTHS_SHORT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

FEATURE_LABELS = {
    "temperatura_media": "Temperatura média do mês",
    "umidade_media": "Umidade do ar",
    "precipitacao_total": "Chuva no mês",
    "densidade_demografica": "Pessoas por km² (densidade)",
    "mes": "Época do ano (mês)",
    "casos_lag1": "Casos no mês anterior",
    "incidencia_lag1": "Casos por 100 mil hab. no mês anterior",
    "incidencia_lag2": "Casos por 100 mil hab. há 2 meses",
    "incidencia_lag3": "Casos por 100 mil hab. há 3 meses",
    "incidencia_lag12": "Casos por 100 mil hab. no mesmo mês do ano anterior",
    "crescimento": "Tendência dos casos",
    "incidencia_media3": "Média dos últimos 3 meses",
    "temperatura_media_lag1": "Temperatura do mês anterior",
    "precipitacao_total_lag1": "Chuva no mês anterior",
    "precipitacao_total_lag2": "Chuva há 2 meses",
    "umidade_media_lag1": "Umidade no mês anterior",
    "incidencia_historica": "Histórico de casos do município",
    "incidencia_estado_lag1": "Casos no estado no mês anterior",
    "incidencia_vizinhos_lag1": "Casos nos municípios vizinhos",
    "log_populacao": "Tamanho da população",
}
# Grupos em linguagem simples para explicar o modelo a leigos.
FEATURE_GROUPS = {
    "Casos recentes no município": ["casos_lag1", "incidencia_lag1", "incidencia_lag2", "incidencia_lag3",
                                    "crescimento", "incidencia_media3"],
    "Temperatura": ["temperatura_media", "temperatura_media_lag1"],
    "Época do ano": ["mes"],
    "Histórico do município": ["incidencia_historica", "incidencia_lag12"],
    "Casos nos vizinhos e no estado": ["incidencia_vizinhos_lag1", "incidencia_estado_lag1"],
    "Chuva e umidade": ["precipitacao_total", "precipitacao_total_lag1", "precipitacao_total_lag2",
                        "umidade_media", "umidade_media_lag1"],
    "Tamanho e densidade da população": ["densidade_demografica", "log_populacao"],
}


def grouped_importance(importances: dict[str, float]) -> dict[str, float]:
    return {group: sum(importances.get(key, 0.0) for key in keys) for group, keys in FEATURE_GROUPS.items()}

RISK_HIGH = "Risco alto"
RISK_LOW = "Risco baixo"
RISK_UNKNOWN = "Sem dados suficientes"
RISK_LABELS = {"Alto": RISK_HIGH, "Baixo": RISK_LOW}
RISK_COLORS = {RISK_HIGH: "#c92a2a", RISK_LOW: "#2f9e44", RISK_UNKNOWN: "#ced4da"}
RISK_ORDER = [RISK_HIGH, RISK_LOW, RISK_UNKNOWN]

INCIDENCE_BINS = [
    ("Nenhum caso", "#f1f3f5"),
    ("Até 100 por 100 mil", "#ffe8a1"),
    ("100 a 300 por 100 mil", "#fd9a4b"),
    ("300 ou mais (nível epidêmico)", "#c92a2a"),
]
# Incidência acumulada em um período (vários meses somados)
PERIOD_INCIDENCE_BINS = [
    ("Nenhum caso", "#f1f3f5"),
    ("Até 100 por 100 mil", "#ffe8a1"),
    ("100 a 300 por 100 mil", "#fdc16b"),
    ("300 a 1.000 por 100 mil", "#f76707"),
    ("Mais de 1.000 por 100 mil", "#a61e1e"),
]
CASES_BINS = [
    ("Nenhum caso", "#f1f3f5"),
    ("1 a 10", "#ffe8a1"),
    ("11 a 100", "#fdc16b"),
    ("101 a 1.000", "#f76707"),
    ("Mais de 1.000", "#a61e1e"),
]


def is_missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA or value is pd.NaT


def num(value, decimals: int = 0) -> str:
    """1234567.8 -> '1.234.568' (ou '1.234.567,8' com decimals=1)."""
    if is_missing(value):
        return "—"
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def pct(fraction, decimals: int = 0) -> str:
    return "—" if is_missing(fraction) else f"{num(float(fraction) * 100, decimals)}%"


def month_year(value, short: bool = False) -> str:
    ts = pd.Timestamp(value)
    if short:
        return f"{MONTHS_SHORT[ts.month - 1]}/{ts.year % 100:02d}"
    return f"{MONTHS[ts.month - 1]} de {ts.year}"


def change(current, previous) -> float | None:
    """Variação relativa; None quando a base é zero ou ausente."""
    if is_missing(current) or is_missing(previous) or float(previous) == 0:
        return None
    return float(current) / float(previous) - 1


def metric_delta(current, previous) -> str | int | None:
    """Delta para st.metric: '+12%' / '-30%' / 0 (estável) / None (sem base de comparação)."""
    variation = change(current, previous)
    if variation is None:
        return None
    if abs(variation) < 0.005:
        return 0
    return f"{'+' if variation > 0 else '-'}{pct(abs(variation))}"


def risk_label(risk) -> str:
    return RISK_LABELS.get(risk, RISK_UNKNOWN) if not is_missing(risk) else RISK_UNKNOWN


def incidence_bin(value) -> str:
    if is_missing(value):
        return RISK_UNKNOWN
    if value <= 0:
        return INCIDENCE_BINS[0][0]
    if value < 100:
        return INCIDENCE_BINS[1][0]
    if value < 300:
        return INCIDENCE_BINS[2][0]
    return INCIDENCE_BINS[3][0]


def period_incidence_bin(value) -> str:
    if is_missing(value):
        return RISK_UNKNOWN
    if value <= 0:
        return PERIOD_INCIDENCE_BINS[0][0]
    if value < 100:
        return PERIOD_INCIDENCE_BINS[1][0]
    if value < 300:
        return PERIOD_INCIDENCE_BINS[2][0]
    if value < 1000:
        return PERIOD_INCIDENCE_BINS[3][0]
    return PERIOD_INCIDENCE_BINS[4][0]


def period_text(start, end) -> str:
    """'nov/25 a out/26' ou 'outubro de 2026' quando é um único mês."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start == end:
        return month_year(start)
    return f"{month_year(start, short=True)} a {month_year(end, short=True)}"


def cases_bin(value) -> str:
    if is_missing(value):
        return RISK_UNKNOWN
    if value <= 0:
        return CASES_BINS[0][0]
    if value <= 10:
        return CASES_BINS[1][0]
    if value <= 100:
        return CASES_BINS[2][0]
    if value <= 1000:
        return CASES_BINS[3][0]
    return CASES_BINS[4][0]


def times_text(ratio: float) -> str:
    """Razão em linguagem simples: 2.3 -> '2,3 vezes'."""
    return f"{num(ratio, 1)} vezes"
