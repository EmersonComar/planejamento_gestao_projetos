"""INMET — Dados Históricos: precipitação horária das estações automáticas de SC."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from src.infrastructure.sources.http import download

URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
UF = "SC"
PRECIPITATION = "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)"


def download_year(year: int, raw_dir: Path, force: bool = False) -> Path:
    """Zip anual (todas as estações do país). O do ano corrente é parcial e deve ser rebaixado."""
    return download(URL.format(year=year), Path(raw_dir) / f"{year}.zip", force=force, validate=zipfile.is_zipfile)


def _number(text: str) -> float:
    return float(str(text).strip().replace(",", "."))


def _meta_value(meta: dict, prefix: str) -> str:
    # O cabeçalho varia entre anos ("ESTAÇÃO:", "ESTACAO:", acentos perdidos); compara pelo início.
    for key, value in meta.items():
        normalized = key.upper().replace("Ç", "C").replace("Ã", "A").replace("?", "")
        if normalized.startswith(prefix):
            return value.strip()
    return ""


def read_year(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (precipitação mensal por estação, metadados das estações) de um zip anual."""
    monthly, stations = [], []
    with zipfile.ZipFile(path) as archive:
        for name in (n for n in archive.namelist() if f"_{UF}_" in n):
            lines = archive.read(name).decode("latin-1").splitlines()
            meta = dict(line.split(";", 1) for line in lines[:8] if ";" in line)
            code = _meta_value(meta, "CODIGO") or name.split("_")[3]
            frame = pd.read_csv(io.StringIO("\n".join(lines[8:])), sep=";", decimal=",",
                                na_values=["-9999", ""], encoding="latin-1", usecols=lambda c: True)
            date_column = next(c for c in frame.columns if c.upper().startswith("DATA"))
            frame["ano_mes"] = pd.to_datetime(frame[date_column], format="mixed", errors="coerce").dt.to_period("M")
            month = (frame.groupby("ano_mes")[PRECIPITATION]
                     .agg(precipitacao_total="sum", horas_medidas="count").reset_index())
            month["codigo_estacao"] = code
            monthly.append(month)
            stations.append({"codigo_estacao": code, "nome_estacao": _meta_value(meta, "ESTACAO") or name.split("_")[4],
                             "lat": _number(_meta_value(meta, "LATITUDE")), "lon": _number(_meta_value(meta, "LONGITUDE")),
                             "ano": int(Path(path).stem)})
    return pd.concat(monthly, ignore_index=True), pd.DataFrame(stations)
