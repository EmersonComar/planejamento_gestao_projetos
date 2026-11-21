"""Regras de validação das entradas do modelo, compartilhadas por app e build de dados."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from src.domain.entities import DengueRiskInput


@dataclass(frozen=True)
class FieldRule:
    label: str
    minimum: float | None = None
    maximum: float | None = None
    integer: bool = False
    required: bool = True


MODEL_FIELDS: dict[str, FieldRule] = {
    "temperatura_media": FieldRule("Temperatura média (°C)"),
    "umidade_media": FieldRule("Umidade média do ar (%)", 0.0, 100.0),
    "precipitacao_total": FieldRule("Chuva acumulada no mês (mm)", 0.0, required=False),
    "densidade_demografica": FieldRule("Habitantes por km²", 0.0),
    "mes": FieldRule("Mês do ano", 1, 12, integer=True),
    "casos_lag1": FieldRule("Casos de dengue no mês anterior", 0.0),
    "incidencia_lag1": FieldRule("Casos por 100 mil habitantes no mês anterior", 0.0),
    # Opcionais: o modelo aceita ausência (NaN); se informados, precisam ser válidos.
    "incidencia_lag2": FieldRule("Casos por 100 mil habitantes há 2 meses", 0.0, required=False),
    "incidencia_lag3": FieldRule("Casos por 100 mil habitantes há 3 meses", 0.0, required=False),
    "incidencia_lag12": FieldRule("Casos por 100 mil habitantes no mesmo mês do ano anterior", 0.0, required=False),
    "crescimento": FieldRule("Tendência dos casos (variação entre os dois meses anteriores)", required=False),
    "incidencia_media3": FieldRule("Média de casos por 100 mil nos 3 meses anteriores", 0.0, required=False),
    "temperatura_media_lag1": FieldRule("Temperatura média do mês anterior (°C)", required=False),
    "precipitacao_total_lag1": FieldRule("Chuva no mês anterior (mm)", 0.0, required=False),
    "precipitacao_total_lag2": FieldRule("Chuva há 2 meses (mm)", 0.0, required=False),
    "umidade_media_lag1": FieldRule("Umidade do ar no mês anterior (%)", 0.0, 100.0, required=False),
    "incidencia_historica": FieldRule("Média histórica de casos por 100 mil no município", 0.0, required=False),
    "incidencia_estado_lag1": FieldRule("Casos por 100 mil no estado no mês anterior", 0.0, required=False),
    "incidencia_vizinhos_lag1": FieldRule("Casos por 100 mil nos municípios vizinhos no mês anterior", 0.0, required=False),
    "log_populacao": FieldRule("Logaritmo da população", 0.0, required=False),
}
REQUIRED_FIELDS = [key for key, rule in MODEL_FIELDS.items() if rule.required]
OPTIONAL_FIELDS = [key for key, rule in MODEL_FIELDS.items() if not rule.required]


def _is_absent(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def parse_field(key: str, raw_value: Any) -> float | int:
    """Converte e valida um valor; levanta ValueError com mensagem para o usuário.

    Campos opcionais ausentes viram NaN.
    """
    rule = MODEL_FIELDS[key]
    if not rule.required and _is_absent(raw_value):
        return math.nan
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        raise ValueError(f"{rule.label}: preencha um número válido.") from None
    if not math.isfinite(value):
        raise ValueError(f"{rule.label}: entradas não finitas não são permitidas.")
    if rule.integer and not value.is_integer():
        raise ValueError(f"{rule.label}: informe um número inteiro.")
    if rule.minimum is not None and value < rule.minimum:
        raise ValueError(f"{rule.label}: o valor deve ser igual ou maior que {rule.minimum:g}.")
    if rule.maximum is not None and value > rule.maximum:
        raise ValueError(f"{rule.label}: o valor deve ser igual ou menor que {rule.maximum:g}.")
    return int(value) if rule.integer else value


def build_risk_input(values: Any) -> DengueRiskInput:
    """Monta a entrada do modelo a partir de um mapeamento (dict, Series...)."""
    return DengueRiskInput(**{key: parse_field(key, values.get(key)) for key in MODEL_FIELDS})
