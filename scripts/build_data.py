"""Gera os arquivos Parquet pré-calculados que o app consulta via DuckDB.

Rode sempre que a base analítica, o modelo ou a malha mudarem:

    uv run python scripts/build_data.py

O teste ``tests/test_app_data.py`` falha se os arquivos estiverem desatualizados.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.infrastructure.data.app_data_builder import build_app_data  # noqa: E402

if __name__ == "__main__":
    metadata = build_app_data(ROOT)
    print(
        f"Base gerada: {metadata['registros']} registros, {metadata['municipios']} municípios, "
        f"{metadata['periodo_inicio']} a {metadata['periodo_fim']}, {metadata['cenarios']} cenários."
    )
