"""DIVE/SC — fonte oficial dos totais estaduais mensais de dengue, mantidos como referência.

A tabela "Casos notificados de dengue, segundo classificação final" traz, por mês de início dos
sintomas, as colunas Dengue, Dengue com sinais de alarme, Dengue grave, Descartado, Inconclusivo e
Suspeito. Casos prováveis = todas menos Descartado. Essa série estadual é comparada, mas não
substitui nem alimenta a série municipal do InfoDengue usada no modelo.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.infrastructure.sources.http import download

BASE_URL = ("https://dive.saude.sc.gov.br/index.php/component/phocadownload/category/"
            "21-doencas-e-agravos/29-dengue?download={id}&Itemid=101")
# Último informe com o ano completo (ou o mais recente do ano corrente). Página de referência:
# https://dive.saude.sc.gov.br/index.php/doencas-e-agravos/dengue (aba Informes/Boletins)
BULLETINS = [
    {"ano": 2024, "id": 2508, "documento": "Informe Epidemiológico nº 34/2024", "dados_ate": "2025-03-24"},
    {"ano": 2025, "id": 2802, "documento": "Informe Epidemiológico nº 17/2025", "dados_ate": "2025-12-01"},
    {"ano": 2026, "id": 3050, "documento": "Informe Epidemiológico nº 11/2026", "dados_ate": "2026-11-03"},
]
_ROW = re.compile(r"^\s*(\d{1,2})\s{2,}(.*)$")
_VALUE = re.compile(r"([\d.]+)\s*\(")


def download_bulletin(bulletin: dict, raw_dir: Path, force: bool = False) -> Path:
    return download(BASE_URL.format(id=bulletin["id"]), Path(raw_dir) / "dive" / f"informe_{bulletin['id']}.pdf",
                    force=force, validate=lambda p: p.read_bytes()[:4] == b"%PDF")


def pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text(extraction_mode="layout") for page in PdfReader(str(path)).pages)


def parse_monthly_table(text: str) -> pd.DataFrame:
    """Linhas "mês  N (x%) ..." da tabela por classificação final (meses 1 a 12)."""
    rows = []
    for line in text.splitlines():
        match = _ROW.match(line)
        if not match:
            continue
        values = [int(v.replace(".", "")) for v in _VALUE.findall(match.group(2))]
        if len(values) != 6:
            continue
        dengue, alarm, severe, discarded, inconclusive, suspect = values
        rows.append({"mes": int(match.group(1)), "casos_provaveis": dengue + alarm + severe + inconclusive + suspect,
                     "notificacoes": sum(values), "descartados": discarded})
    table = pd.DataFrame(rows, columns=["mes", "casos_provaveis", "notificacoes", "descartados"])
    if table["mes"].duplicated().any():
        raise ValueError("Tabela mensal do informe com meses repetidos.")
    return table


def monthly_reference(raw_dir: Path, force: bool = False) -> pd.DataFrame:
    frames = []
    for bulletin in BULLETINS:
        table = parse_monthly_table(pdf_text(download_bulletin(bulletin, raw_dir, force)))
        frames.append(table.assign(ano=bulletin["ano"], documento=bulletin["documento"],
                                   dados_ate=bulletin["dados_ate"], fonte=BASE_URL.format(id=bulletin["id"])))
    columns = ["ano", "mes", "casos_provaveis", "notificacoes", "descartados", "documento", "dados_ate", "fonte"]
    return pd.concat(frames, ignore_index=True)[columns]
