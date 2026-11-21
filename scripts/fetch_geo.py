"""Baixa a malha municipal e as regiões de SC do IBGE para data/geo/ (também feito pelo notebook de dados).

    uv run python scripts/fetch_geo.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.infrastructure import pipeline  # noqa: E402

if __name__ == "__main__":
    municipalities, mesh = pipeline.collect_geography(pipeline.Paths(ROOT))
    print(f"{len(mesh['features'])} municípios gravados em {ROOT / 'data' / 'geo'}")
