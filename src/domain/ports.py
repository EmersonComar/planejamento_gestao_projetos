from abc import ABC, abstractmethod
from typing import List, Dict, Optional
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


class IDataRepository(ABC):
    @abstractmethod
    def load(self) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_municipalities(self) -> List[str]:
        pass

    @abstractmethod
    def filter_by_municipality(self, name: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_state_summary_by_period(self) -> pd.DataFrame:
        pass
