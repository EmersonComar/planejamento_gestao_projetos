"""Baixa as fontes e monta a base analítica (mesmo código do notebook de dados).

    uv run python scripts/update_base.py coletar   # baixa todas as fontes (rede; InfoDengue ~10 min)
    uv run python scripts/update_base.py montar    # processa o INMET e monta a base mensal (sem rede)

Depois: `uv run python scripts/train_model.py treinar` e `uv run python scripts/build_data.py`.
Definições das colunas em `src/application/use_cases/base_analitica.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.infrastructure import pipeline  # noqa: E402


def collect(paths: pipeline.Paths) -> None:
    municipalities, _ = pipeline.collect_geography(paths)
    print(f"IBGE: {len(municipalities)} municípios e malha")
    population, area = pipeline.collect_ibge_tables(paths)
    print(f"IBGE: população {population['ano'].min()}–{population['ano'].max()}, área de {len(area)} municípios")
    print(f"ANA: {len(pipeline.collect_sanitation(paths))} municípios com ETE ativa")
    print(f"DIVE/SC: {len(pipeline.collect_dive_reference(paths))} meses de referência")
    pipeline.collect_inmet(paths)
    weekly = pipeline.collect_infodengue(paths, refresh=True)
    print(f"InfoDengue: {len(weekly)} semanas")


def assemble(paths: pipeline.Paths) -> None:
    station_monthly, stations = pipeline.process_inmet(paths)
    mapping = pipeline.map_stations(paths)
    base = pipeline.assemble_base(paths)
    print(f"INMET: {len(stations)} estações; {mapping['codigo_ibge'].nunique()} municípios com estação a até 60 km")
    print(f"Base: {len(base)} linhas, {base['ano_mes'].min():%Y-%m} a {base['ano_mes'].max():%Y-%m}; "
          f"chuva em {base['precipitacao_total'].notna().mean():.0%} das linhas")


if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    paths = pipeline.Paths(ROOT)
    if step == "coletar":
        collect(paths)
    elif step == "montar":
        assemble(paths)
    else:
        raise SystemExit(__doc__)
