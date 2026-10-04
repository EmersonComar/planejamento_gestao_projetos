from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

class RiskLevel(Enum):
    LOW = "Baixo"
    HIGH = "Alto"

@dataclass
class DengueRiskInput:
    temperatura_media: float
    umidade_media: float
    precipitacao_total: float
    densidade_demografica: float
    mes: int
    casos_lag1: float
    incidencia_lag1: float

@dataclass
class DengueRiskOutput:
    risk_level: RiskLevel
    probability: float
    feature_importances: Optional[Dict[str, float]] = None
