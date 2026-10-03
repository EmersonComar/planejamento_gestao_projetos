from abc import ABC, abstractmethod
from typing import List
from src.domain.entities import DengueRiskInput, DengueRiskOutput

class IModelPredictor(ABC):
    @abstractmethod
    def predict(self, data: DengueRiskInput) -> DengueRiskOutput:
        pass

    @abstractmethod
    def predict_batch(self, data_list: List[DengueRiskInput]) -> List[DengueRiskOutput]:
        pass
