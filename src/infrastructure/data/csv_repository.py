import pandas as pd
import hashlib
import json
from pathlib import Path
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

    def get_generation_time(self) -> pd.Timestamp | None:
        """Only display a recorded generation time belonging to this exact CSV."""
        csv_path = Path(self._file_path)
        metadata_path = csv_path.with_suffix(".metadata.json")
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(metadata, dict):
                return None
            with csv_path.open("rb") as csv_file:
                checksum = hashlib.file_digest(csv_file, "sha256").hexdigest()
            if metadata.get("csv_sha256") != checksum:
                return None
            generated_at = pd.Timestamp(metadata["generated_at"])
            if pd.isna(generated_at) or generated_at.tzinfo is None:
                return None
            return generated_at.tz_convert("America/Sao_Paulo")
        except (OSError, ValueError, TypeError, KeyError):
            return None

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
