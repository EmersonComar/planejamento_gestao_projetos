import pandas as pd
from typing import List
from src.domain.ports import IDataRepository


class CsvDataRepository(IDataRepository):
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._df: pd.DataFrame | None = None

    def load(self) -> pd.DataFrame:
        if self._df is None:
            self._df = pd.read_csv(self._file_path, parse_dates=["ano_mes"])
        return self._df

    def get_municipalities(self) -> List[str]:
        df = self.load()
        return sorted(df["nome_municipio"].unique().tolist())

    def filter_by_municipality(self, name: str) -> pd.DataFrame:
        df = self.load()
        return df[df["nome_municipio"] == name].copy()

    def get_state_summary_by_period(self) -> pd.DataFrame:
        df = self.load()
        return (
            df.groupby("ano_mes", as_index=False)
            .agg(
                casos_total=("casos", "sum"),
                incidencia_media=("incidencia_100k", "mean"),
                temperatura_media=("temperatura_media", "mean"),
                umidade_media=("umidade_media", "mean"),
                precipitacao_total=("precipitacao_total", "mean"),
            )
            .sort_values("ano_mes")
        )
