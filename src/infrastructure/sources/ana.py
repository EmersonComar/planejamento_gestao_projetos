"""ANA — Atlas Esgotos (ETEs 2020): tratamento de esgoto por município."""
from __future__ import annotations

import io

import pandas as pd

from src.infrastructure.sources.http import get

URL = "https://dadosabertos.ana.gov.br/api/download/v1/items/0ac689335d1641d2b88a32312d22c9ac/csv?layers=0"
UF_CODE = "42"


def sanitation() -> pd.DataFrame:
    """Quantidade de ETEs ativas e remoção média de DBO (%) por município de SC."""
    frame = pd.read_csv(io.StringIO(get(URL, timeout=120).text))
    frame["ETE_MUN_CD_IBGE"] = frame["ETE_MUN_CD_IBGE"].astype(str)
    active = frame[frame["ETE_MUN_CD_IBGE"].str.startswith(UF_CODE) & (frame["ETE_DS_STATUS"] == "Ativa")].copy()
    active["ETE_PC_REMOCAODBO"] = pd.to_numeric(active["ETE_PC_REMOCAODBO"], errors="coerce")
    result = (active.groupby("ETE_MUN_CD_IBGE")
              .agg(qtd_ete_ativas=("ETE_CD", "count"), remocao_dbo_media=("ETE_PC_REMOCAODBO", "mean"))
              .reset_index().rename(columns={"ETE_MUN_CD_IBGE": "codigo_ibge"}))
    result["codigo_ibge"] = result["codigo_ibge"].astype(int)
    return result
