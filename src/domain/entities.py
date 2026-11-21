import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

NAN = math.nan


class RiskLevel(Enum):
    LOW = "Baixo"
    HIGH = "Alto"


@dataclass
class DengueRiskInput:
    """Entradas do modelo. Chuva e os atributos após ``incidencia_lag1`` aceitam NaN (ausente)."""

    temperatura_media: float
    umidade_media: float
    precipitacao_total: float
    densidade_demografica: float
    mes: int
    casos_lag1: float
    incidencia_lag1: float
    incidencia_lag2: float = NAN
    incidencia_lag3: float = NAN
    incidencia_lag12: float = NAN
    crescimento: float = NAN
    incidencia_media3: float = NAN
    temperatura_media_lag1: float = NAN
    precipitacao_total_lag1: float = NAN
    precipitacao_total_lag2: float = NAN
    umidade_media_lag1: float = NAN
    incidencia_historica: float = NAN
    incidencia_estado_lag1: float = NAN
    incidencia_vizinhos_lag1: float = NAN
    log_populacao: float = NAN


@dataclass
class DengueRiskOutput:
    risk_level: RiskLevel
    probability: float
    feature_importances: Optional[Dict[str, float]] = None
