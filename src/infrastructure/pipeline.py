"""Etapas do pipeline de dados e modelo, compartilhadas pelos notebooks e pelos scripts.

Ordem: coleta das fontes → precipitação por estação → associação estação-município →
base analítica → treino do modelo → base do painel. Cada etapa grava seus arquivos em `data/` ou
`models/` e pode ser executada isoladamente (as anteriores leem do disco).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd

from src.application.use_cases import base_analitica, model_training
from src.application.use_cases.build_analytics_data import centroids_from_geojson
from src.infrastructure.sources import ana, dive, ibge, infodengue, inmet

FIRST_YEAR = 2015


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def raw(self) -> Path: return self.root / "data" / "raw"
    @property
    def processed(self) -> Path: return self.root / "data" / "processed"
    @property
    def geo(self) -> Path: return self.root / "data" / "geo"
    @property
    def reference(self) -> Path: return self.root / "data" / "referencia" / "dive_sc_dengue_mensal.csv"
    @property
    def models(self) -> Path: return self.root / "models"
    @property
    def municipalities(self) -> Path: return self.geo / "municipios_sc.csv"
    @property
    def mesh(self) -> Path: return self.geo / "sc_municipios.geojson"
    @property
    def station_mapping(self) -> Path: return self.geo / "estacoes_inmet_municipios.csv"
    @property
    def infodengue(self) -> Path: return self.raw / "infodengue_sc.csv"
    @property
    def population(self) -> Path: return self.processed / "populacao_sc.csv"
    @property
    def area(self) -> Path: return self.processed / "area_sc.csv"
    @property
    def sanitation(self) -> Path: return self.processed / "saneamento_sc.csv"
    @property
    def station_monthly(self) -> Path: return self.processed / "precipitacao_estacoes_mensal.csv"
    @property
    def stations(self) -> Path: return self.processed / "estacoes_inmet.csv"
    @property
    def base(self) -> Path: return self.processed / "base_analitica_sc.csv"
    @property
    def model(self) -> Path: return self.models / "modelo_risco_dengue.pkl"
    @property
    def baseline_model(self) -> Path: return self.models / "modelo_baseline_risco_dengue.pkl"
    @property
    def metrics(self) -> Path: return self.models / "metricas_modelo.json"


def today() -> pd.Timestamp:
    return pd.Timestamp.now(tz="America/Sao_Paulo").tz_localize(None).normalize()


def last_complete_month() -> pd.Period:
    return pd.Period(today(), freq="M") - 1


# ------------------------------------------------------------------ coleta

def collect_geography(paths: Paths) -> tuple[pd.DataFrame, dict]:
    """IBGE: municípios com regiões e malha municipal."""
    paths.geo.mkdir(parents=True, exist_ok=True)
    municipalities = ibge.municipalities()
    municipalities.to_csv(paths.municipalities, index=False)
    mesh = ibge.mesh(dict(zip(municipalities["codigo_ibge"], municipalities["nome"])))
    paths.mesh.write_text(json.dumps(mesh, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (paths.geo / "fonte.json").write_text(json.dumps({
        "baixado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "malha": ibge.MESH_URL, "localidades": ibge.LOCALITIES_URL,
        "orgao": "IBGE — API de Malhas Geográficas v3 e API de Localidades v1",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return municipalities, mesh


def collect_infodengue(paths: Paths, refresh: bool = False, progress=print) -> pd.DataFrame:
    """Série semanal 2015–ano atual. Reaproveita a coleta salva, a menos que ``refresh``."""
    if paths.infodengue.exists() and not refresh:
        return pd.read_csv(paths.infodengue, low_memory=False)
    weekly = infodengue.fetch_weekly(pd.read_csv(paths.municipalities), FIRST_YEAR, today().year, progress=progress)
    paths.raw.mkdir(parents=True, exist_ok=True)
    weekly.to_csv(paths.infodengue, index=False)
    return weekly


def collect_ibge_tables(paths: Paths) -> tuple[pd.DataFrame, pd.DataFrame]:
    paths.processed.mkdir(parents=True, exist_ok=True)
    population = ibge.population(FIRST_YEAR, today().year)
    population.to_csv(paths.population, index=False)
    area = ibge.area()
    area.to_csv(paths.area, index=False)
    return population, area


def collect_sanitation(paths: Paths) -> pd.DataFrame:
    paths.processed.mkdir(parents=True, exist_ok=True)
    sanitation = ana.sanitation()
    sanitation.to_csv(paths.sanitation, index=False)
    return sanitation


def collect_inmet(paths: Paths, refresh_current_year: bool = True, progress=print) -> list[Path]:
    """Zips anuais do INMET (~100 MB cada). O do ano corrente é parcial: rebaixado por padrão."""
    files = []
    for year in range(FIRST_YEAR, today().year + 1):
        force = refresh_current_year and year == today().year
        files.append(inmet.download_year(year, paths.raw, force=force))
        if progress:
            progress(f"  INMET {year}: ok")
    return files


def collect_dive_reference(paths: Paths, refresh: bool = False) -> pd.DataFrame:
    reference = dive.monthly_reference(paths.raw, force=refresh)
    paths.reference.parent.mkdir(parents=True, exist_ok=True)
    reference.to_csv(paths.reference, index=False)
    return reference


# ------------------------------------------------------------------ processamento

def process_inmet(paths: Paths) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Precipitação mensal por estação e metadados das estações, a partir dos zips em data/raw."""
    monthly, stations = [], []
    for year in range(FIRST_YEAR, today().year + 1):
        month, station = inmet.read_year(paths.raw / f"{year}.zip")
        monthly.append(month)
        stations.append(station)
    station_monthly = pd.concat(monthly, ignore_index=True).drop_duplicates(["codigo_estacao", "ano_mes"], keep="last")
    stations = base_analitica.latest_station_coordinates(pd.concat(stations, ignore_index=True))
    station_monthly.to_csv(paths.station_monthly, index=False)
    stations.to_csv(paths.stations, index=False)
    return station_monthly, stations


def map_stations(paths: Paths) -> pd.DataFrame:
    centroids = centroids_from_geojson(json.loads(paths.mesh.read_text(encoding="utf-8")))
    mapping = base_analitica.station_mapping(pd.read_csv(paths.stations), centroids)
    mapping.to_csv(paths.station_mapping, index=False)
    return mapping


def assemble_base(paths: Paths, month: pd.Period | None = None) -> pd.DataFrame:
    station_monthly = pd.read_csv(paths.station_monthly)
    station_monthly["ano_mes"] = pd.PeriodIndex(station_monthly["ano_mes"], freq="M")
    weekly = pd.read_csv(paths.infodengue, low_memory=False)
    precipitation = base_analitica.precipitation_by_municipality(station_monthly, pd.read_csv(paths.station_mapping))
    base = base_analitica.build_base(
        weekly, pd.read_csv(paths.population), pd.read_csv(paths.area), precipitation,
        pd.read_csv(paths.sanitation), month or last_complete_month(),
    )
    write_base(paths, base)
    return base


def write_base(paths: Paths, base: pd.DataFrame) -> None:
    base.to_csv(paths.base, index=False)
    with paths.base.open("rb") as file:
        checksum = hashlib.file_digest(file, "sha256").hexdigest()
    paths.base.with_suffix(".metadata.json").write_text(json.dumps({
        "generated_at": datetime.now(UTC).isoformat(),
        "csv_sha256": checksum,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ modelo

def load_training_data(paths: Paths) -> pd.DataFrame:
    base = pd.read_csv(paths.base, parse_dates=["ano_mes"])
    centroids = centroids_from_geojson(json.loads(paths.mesh.read_text(encoding="utf-8")))
    return model_training.prepare_dataset(base, centroids)


def train_models(paths: Paths, data: pd.DataFrame | None = None,
                 evaluations: dict[str, tuple[list[dict], list[pd.DataFrame]]] | None = None) -> tuple[dict, dict]:
    """Treina o modelo baseline e o modelo final; grava os dois artefatos e as métricas.

    ``evaluations``: avaliações já calculadas por nome de candidato (evita recalcular).
    """
    data = load_training_data(paths) if data is None else data
    evaluations = evaluations or {}
    baseline = model_training.train("baseline", data, evaluation=evaluations.get("baseline"))
    final = model_training.train(model_training.CHOSEN, data, baseline_rows=baseline["metricas"]["avaliacao_por_ano"],
                                 evaluation=evaluations.get(model_training.CHOSEN))
    paths.models.mkdir(parents=True, exist_ok=True)
    joblib.dump(baseline, paths.baseline_model, compress=3)
    joblib.dump(final, paths.model, compress=3)
    paths.metrics.write_text(json.dumps(final["metricas"], ensure_ascii=False, indent=2, default=float), encoding="utf-8")
    return baseline, final
