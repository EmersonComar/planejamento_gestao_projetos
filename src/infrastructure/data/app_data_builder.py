"""Lê as fontes (CSV, modelo, malha) e grava os Parquet pré-calculados do app."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from src.application.use_cases.build_analytics_data import (
    HIGH_INCIDENCE_THRESHOLD,
    build_monthly,
    build_municipalities,
    build_scenarios,
    build_typical_profile,
    geometry_centroid,
)
from src.application.use_cases.features import neighbor_table
from src.application.use_cases.predict_risk import PredictRiskUseCase
from src.infrastructure.ml.predictor import SklearnPredictor

SCHEMA_VERSION = 2
TABLES = ("mensal", "cenarios", "municipios", "perfil_tipico")


@dataclass(frozen=True)
class AppDataPaths:
    root: Path

    @property
    def csv(self) -> Path:
        return self.root / "data" / "processed" / "base_analitica_sc.csv"

    @property
    def model(self) -> Path:
        return self.root / "models" / "modelo_risco_dengue.pkl"

    @property
    def geojson(self) -> Path:
        return self.root / "data" / "geo" / "sc_municipios.geojson"

    @property
    def regions(self) -> Path:
        return self.root / "data" / "geo" / "municipios_sc.csv"

    @property
    def output_dir(self) -> Path:
        return self.root / "data" / "app"

    @property
    def metadata(self) -> Path:
        return self.output_dir / "metadados.json"

    def table(self, name: str) -> Path:
        return self.output_dir / f"{name}.parquet"

    def source_hashes(self) -> dict[str, str]:
        return {
            "csv_sha256": file_sha256(self.csv),
            "modelo_sha256": file_sha256(self.model),
            "malha_sha256": file_sha256(self.geojson),
            "regioes_sha256": file_sha256(self.regions),
        }


def file_sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def read_csv_generation_time(csv_path: Path) -> pd.Timestamp | None:
    """Data de geração gravada pelo notebook, aceita só se o hash corresponder ao CSV."""
    metadata_path = csv_path.with_suffix(".metadata.json")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict) or metadata.get("csv_sha256") != file_sha256(csv_path):
            return None
        generated_at = pd.Timestamp(metadata["generated_at"])
        if pd.isna(generated_at) or generated_at.tzinfo is None:
            return None
        return generated_at.tz_convert("America/Sao_Paulo")
    except (OSError, ValueError, TypeError, KeyError):
        return None


def build_app_data(root: Path) -> dict:
    paths = AppDataPaths(Path(root))
    base = pd.read_csv(paths.csv, parse_dates=["ano_mes"])
    predictor = SklearnPredictor(str(paths.model))
    use_case = PredictRiskUseCase(predictor)
    geojson = json.loads(paths.geojson.read_text(encoding="utf-8"))
    regions = pd.read_csv(paths.regions)

    incidence_threshold = predictor.high_incidence_threshold or HIGH_INCIDENCE_THRESHOLD
    centroids = pd.DataFrame([
        {"codigo_ibge": int(f["properties"]["codigo_ibge"]), **dict(zip(("lat", "lon"), geometry_centroid(f["geometry"])))}
        for f in geojson["features"]
    ])
    neighbors = neighbor_table(centroids)
    monthly = build_monthly(base, use_case, neighbors, incidence_threshold)
    scenarios = build_scenarios(base, use_case, neighbors)
    municipalities = build_municipalities(monthly, regions, geojson)
    municipalities["vizinhos"] = municipalities["codigo_ibge"].map(lambda code: neighbors.get(int(code), []))
    profile = build_typical_profile(monthly)

    paths.output_dir.mkdir(parents=True, exist_ok=True)
    tables = {"mensal": monthly, "cenarios": scenarios, "municipios": municipalities, "perfil_tipico": profile}
    for name, frame in tables.items():
        frame.to_parquet(paths.table(name), index=False, compression="zstd")

    csv_generated_at = read_csv_generation_time(paths.csv)
    metadata = {
        "versao_esquema": SCHEMA_VERSION,
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        **paths.source_hashes(),
        "csv_gerado_em": csv_generated_at.isoformat() if csv_generated_at is not None else None,
        "registros": int(len(monthly)),
        "definicao_casos": "casos prováveis (confirmados, suspeitos e inconclusivos), InfoDengue casprov",
        "registros_classificados": int(monthly["entradas_validas"].sum()),
        "municipios": int(monthly["codigo_ibge"].nunique()),
        "municipios_com_geometria": int(municipalities["possui_geometria"].sum()),
        "periodo_inicio": monthly["ano_mes"].min().strftime("%Y-%m"),
        "periodo_fim": monthly["ano_mes"].max().strftime("%Y-%m"),
        "cenarios": int(len(scenarios)),
        "cenarios_classificados": int(scenarios["entradas_validas"].sum()),
        "modelo": {
            "nome": predictor.model_name,
            "atributos": predictor.features,
            "limiar_decisao": predictor.threshold,
            "limiar_incidencia_alta": incidence_threshold,
            "importancia_global": predictor.get_global_feature_importance(),
            "metricas": predictor.metrics,
        },
    }
    paths.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata
