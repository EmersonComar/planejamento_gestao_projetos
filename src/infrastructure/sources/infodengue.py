"""InfoDengue (Fiocruz): série semanal por município (casos prováveis, notificações, clima, população)."""
from __future__ import annotations

import time

import pandas as pd

from src.infrastructure.sources.http import get_json

URL = "https://info.dengue.mat.br/api/alertcity"


def fetch_weekly(municipalities: pd.DataFrame, first_year: int, last_year: int, pause: float = 0.1,
                 progress=print) -> pd.DataFrame:
    """Uma consulta por município cobre todo o intervalo; inclui a semana epidemiológica 53."""
    records = []
    started = time.time()
    for index, row in enumerate(municipalities.itertuples(), start=1):
        weeks = get_json(URL, params={
            "geocode": row.codigo_ibge, "disease": "dengue", "format": "json",
            "ew_start": 1, "ew_end": 53, "ey_start": first_year, "ey_end": last_year,
        })
        for week in weeks:
            week["codigo_ibge"] = int(row.codigo_ibge)
            week["nome_municipio"] = row.nome
        records.extend(weeks)
        if progress and (index % 50 == 0 or index == len(municipalities)):
            progress(f"  InfoDengue: {index}/{len(municipalities)} municípios ({time.time() - started:.0f}s)")
        time.sleep(pause)
    return pd.DataFrame(records)
