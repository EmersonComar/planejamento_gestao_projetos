from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd
from src.domain.entities import DengueRiskInput, DengueRiskOutput


class IModelPredictor(ABC):
    @abstractmethod
    def predict(self, data: DengueRiskInput) -> DengueRiskOutput:
        pass

    @abstractmethod
    def predict_batch(self, data_list: List[DengueRiskInput]) -> List[DengueRiskOutput]:
        pass

    @abstractmethod
    def get_global_feature_importance(self) -> Optional[Dict[str, float]]:
        pass


class IAnalyticsRepository(ABC):
    """Consultas analíticas sobre a base pré-calculada (histórico, cenários, geografia)."""

    @abstractmethod
    def metadata(self) -> dict: ...

    @abstractmethod
    def periods(self) -> list[pd.Timestamp]: ...

    @abstractmethod
    def scenario_periods(self) -> list[pd.Timestamp]: ...

    @abstractmethod
    def municipalities(self) -> pd.DataFrame: ...

    @abstractmethod
    def geojson(self) -> dict: ...

    @abstractmethod
    def monthly(self, codigo_ibge: Optional[int] = None, start=None, end=None) -> pd.DataFrame: ...

    @abstractmethod
    def state_monthly(self, start=None, end=None) -> pd.DataFrame: ...

    @abstractmethod
    def map_snapshot(self, period) -> pd.DataFrame: ...

    @abstractmethod
    def ranking(self, start=None, end=None, limit: int = 10) -> pd.DataFrame: ...

    @abstractmethod
    def calendar_profile(self, codigo_ibge: Optional[int] = None) -> pd.DataFrame: ...

    @abstractmethod
    def month_year_matrix(self, codigo_ibge: Optional[int] = None) -> pd.DataFrame: ...
