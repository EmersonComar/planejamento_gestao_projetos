"""Treina e avalia o modelo de risco de dengue (mesmo código do notebook de modelagem).

    uv run python scripts/train_model.py avaliar   # compara as configurações candidatas
    uv run python scripts/train_model.py treinar   # treina o baseline e o modelo final e grava em models/
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.application.use_cases import model_training  # noqa: E402
from src.infrastructure import pipeline  # noqa: E402

if __name__ == "__main__":
    step = sys.argv[1] if len(sys.argv) > 1 else ""
    paths = pipeline.Paths(ROOT)
    data = pipeline.load_training_data(paths)
    print(f"Base: {len(data)} registros, {data['alvo'].sum()} meses epidêmicos ({data['alvo'].mean():.2%})")
    if step == "avaliar":
        rows = []
        for name in model_training.CANDIDATES:
            rows += model_training.evaluate(name, data)
        pd.set_option("display.width", 220)
        print(pd.DataFrame(rows).round(3).to_string(index=False))
        print(model_training.summarize(rows).round(3))
    elif step == "treinar":
        baseline, final = pipeline.train_models(paths, data)
        for artifact in (baseline, final):
            metrics = artifact["metricas"]
            print(metrics["configuracao"], "limiar", metrics["limiar_decisao"],
                  {k: round(v, 3) for k, v in metrics["media"].items()})
    else:
        raise SystemExit(__doc__)
