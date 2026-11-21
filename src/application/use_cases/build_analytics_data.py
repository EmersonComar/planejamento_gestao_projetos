"""Gera as tabelas pré-calculadas consumidas pelo app (histórico, cenários, perfil típico e municípios)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.application.use_cases.features import add_model_features
from src.application.use_cases.predict_risk import PredictRiskUseCase
from src.domain.entities import DengueRiskInput
from src.domain.validation import MODEL_FIELDS

HIGH_INCIDENCE_THRESHOLD = 300.0
SCENARIO_HORIZON_MONTHS = 3
CLIMATE_FIELDS = ("temperatura_media", "umidade_media", "precipitacao_total")
FEATURE_FIELDS = list(MODEL_FIELDS)
# Atributos derivados dos casos: no cenário futuro ficam fixos no último mês observado.
CASE_FEATURES = ["casos_lag1", "incidencia_lag1", "incidencia_lag2", "incidencia_lag3", "crescimento",
                 "incidencia_media3", "incidencia_historica", "incidencia_estado_lag1", "incidencia_vizinhos_lag1"]

MONTHLY_COLUMNS = list(dict.fromkeys([
    "codigo_ibge", "nome_municipio", "ano_mes", "ano", "mes",
    "casos", "notificacoes", "populacao", "incidencia_100k",
    "temperatura_media", "temperatura_min", "temperatura_max",
    "umidade_media", "umidade_min", "umidade_max",
    "precipitacao_total", "area_km2", "densidade_demografica",
    "qtd_ete_ativas", "remocao_dbo_media",
    *FEATURE_FIELDS,
    "incidencia_alta_observada", "entradas_validas", "campos_pendentes",
    "prob_alto", "risco",
]))


def validate_model_inputs(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Versão vetorizada de ``parse_field``: retorna (linhas válidas, campos pendentes).

    Campos obrigatórios precisam existir e ser válidos; opcionais podem faltar, mas se
    informados precisam ser válidos.
    """
    valid = pd.Series(True, index=frame.index)
    pending_parts = []
    for key, rule in MODEL_FIELDS.items():
        raw = frame[key] if key in frame.columns else pd.Series(np.nan, index=frame.index)
        blank = raw.map(lambda value: isinstance(value, str) and not value.strip())
        absent = (raw.isna() | blank).astype(bool)
        numeric = pd.to_numeric(raw, errors="coerce").astype("float64")
        ok = np.isfinite(numeric)
        if rule.integer:
            ok &= numeric.mod(1).eq(0)
        if rule.minimum is not None:
            ok &= numeric.ge(rule.minimum)
        if rule.maximum is not None:
            ok &= numeric.le(rule.maximum)
        ok = ok.fillna(False).astype(bool)
        if not rule.required:
            ok |= absent
        valid &= ok
        status = np.where(ok, "", np.where(absent, f"{rule.label} (ausente)", f"{rule.label} (inválido)"))
        pending_parts.append(pd.Series(status, index=frame.index))
    pending = pd.concat(pending_parts, axis=1).apply(
        lambda row: "; ".join(part for part in row if part) or "Nenhum", axis=1
    )
    return valid, pending.astype("string")


def _inputs_from_frame(frame: pd.DataFrame) -> list[DengueRiskInput]:
    records = frame[FEATURE_FIELDS].apply(pd.to_numeric, errors="coerce").astype("float64").to_dict("records")
    for record in records:
        record["mes"] = int(record["mes"])
    return [DengueRiskInput(**record) for record in records]


def predict_frame(frame: pd.DataFrame, use_case: PredictRiskUseCase) -> pd.DataFrame:
    """Prediz linhas válidas; linhas inválidas recebem probabilidade e risco nulos."""
    valid, pending = validate_model_inputs(frame)
    result = frame.copy()
    result["entradas_validas"] = valid
    result["campos_pendentes"] = pending
    result["prob_alto"] = pd.Series(np.nan, index=frame.index, dtype="float64")
    result["risco"] = pd.Series(pd.NA, index=frame.index, dtype="string")
    if valid.any():
        outputs = use_case.execute_batch(_inputs_from_frame(frame.loc[valid]))
        result.loc[valid, "prob_alto"] = [output.probability for output in outputs]
        result.loc[valid, "risco"] = [output.risk_level.value for output in outputs]
    return result


def build_monthly(
    base: pd.DataFrame,
    use_case: PredictRiskUseCase,
    neighbors: dict[int, list[int]],
    high_incidence_threshold: float = HIGH_INCIDENCE_THRESHOLD,
) -> pd.DataFrame:
    frame = add_model_features(base, neighbors)
    frame["ano"] = frame["ano_mes"].dt.year
    frame["incidencia_alta_observada"] = frame["incidencia_100k"].ge(high_incidence_threshold)
    frame = predict_frame(frame, use_case)
    for column in MONTHLY_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
    return frame[MONTHLY_COLUMNS].sort_values(["codigo_ibge", "ano_mes"]).reset_index(drop=True)


def build_scenarios(
    base: pd.DataFrame,
    use_case: PredictRiskUseCase,
    neighbors: dict[int, list[int]],
    horizon: int = SCENARIO_HORIZON_MONTHS,
) -> pd.DataFrame:
    """Cenário simulado para os meses seguintes ao último período da base.

    Clima do mês: média do mesmo mês do calendário no histórico do município (e o mesmo para
    os meses anteriores ainda não observados). Atributos derivados dos casos: calculados para o
    mês seguinte ao último observado e mantidos fixos nos meses seguintes (o classificador não
    prevê casos). A incidência de 12 meses antes é sempre observada.
    """
    base = base.sort_values(["codigo_ibge", "ano_mes"])
    last_period = base["ano_mes"].max()
    periods = pd.date_range(last_period + pd.offsets.MonthBegin(1), periods=horizon, freq="MS")
    climate = (base.assign(mes=base["ano_mes"].dt.month)
               .groupby(["codigo_ibge", "mes"])[list(CLIMATE_FIELDS)].mean().reset_index())
    latest = base.groupby("codigo_ibge").tail(1).reindex(columns=["codigo_ibge", "nome_municipio", "populacao", "area_km2"])
    density = base.dropna(subset=["densidade_demografica"]).groupby("codigo_ibge")["densidade_demografica"].last()

    future = latest.merge(pd.DataFrame({"ano_mes": periods}), how="cross")
    future["mes"] = future["ano_mes"].dt.month
    future["densidade_demografica"] = future["codigo_ibge"].map(density)
    future = future.merge(climate, on=["codigo_ibge", "mes"], how="left", validate="many_to_one").drop(columns="mes")
    extended = pd.concat([base, future], ignore_index=True)

    grid = add_model_features(extended, neighbors)
    grid = grid.loc[grid["ano_mes"] > last_period].copy()
    first = grid.loc[grid["ano_mes"] == periods[0]].set_index("codigo_ibge")
    for column in CASE_FEATURES:
        grid[column] = grid["codigo_ibge"].map(first[column])
    grid["ano"] = grid["ano_mes"].dt.year
    grid["periodo_referencia"] = last_period
    grid = predict_frame(grid, use_case)
    columns = ["codigo_ibge", "nome_municipio", "ano_mes", "ano", "mes", "periodo_referencia",
               *FEATURE_FIELDS, "entradas_validas", "campos_pendentes", "prob_alto", "risco"]
    columns = list(dict.fromkeys(columns))
    return grid[columns].sort_values(["codigo_ibge", "ano_mes"]).reset_index(drop=True)


def build_typical_profile(monthly: pd.DataFrame) -> pd.DataFrame:
    """Valores típicos de cada atributo do modelo por município e mês do calendário (média dos anos).

    Ponto de partida do simulador: o usuário altera só o que quiser e o restante fica típico.
    """
    numeric = [field for field in FEATURE_FIELDS if field != "mes"]
    profile = monthly.groupby(["codigo_ibge", "mes"])[numeric + ["casos"]].mean().reset_index()
    profile = profile.rename(columns={"casos": "casos_medios"})
    latest = monthly.sort_values("ano_mes").groupby("codigo_ibge").tail(1).set_index("codigo_ibge")
    # atributos estruturais: usar o valor mais recente, não a média histórica
    for column in ("densidade_demografica", "log_populacao", "incidencia_historica"):
        profile[column] = profile["codigo_ibge"].map(latest[column])
    profile["populacao"] = profile["codigo_ibge"].map(latest["populacao"])
    profile["anos"] = profile["codigo_ibge"].map(monthly.groupby("codigo_ibge")["ano"].nunique())
    return profile.sort_values(["codigo_ibge", "mes"]).reset_index(drop=True)


def _ring_centroid(ring: list) -> tuple[float, float, float]:
    xs = np.array([point[0] for point in ring], dtype=float)
    ys = np.array([point[1] for point in ring], dtype=float)
    cross = xs[:-1] * ys[1:] - xs[1:] * ys[:-1]
    area = cross.sum() / 2
    if area == 0:
        return float(xs.mean()), float(ys.mean()), 0.0
    cx = ((xs[:-1] + xs[1:]) * cross).sum() / (6 * area)
    cy = ((ys[:-1] + ys[1:]) * cross).sum() / (6 * area)
    return float(cx), float(cy), abs(float(area))


def geometry_centroid(geometry: dict) -> tuple[float, float]:
    """Centroide do maior polígono (anel externo), suficiente para rótulos e zoom."""
    polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    cx, cy, _ = max((_ring_centroid(polygon[0]) for polygon in polygons), key=lambda item: item[2])
    return cy, cx


def build_municipalities(monthly: pd.DataFrame, regions: pd.DataFrame, geojson: dict) -> pd.DataFrame:
    ordered = monthly.sort_values("ano_mes")
    latest = ordered.groupby("codigo_ibge").tail(1).set_index("codigo_ibge")
    frame = pd.DataFrame({
        "nome_municipio": latest["nome_municipio"],
        "populacao": latest["populacao"],
        "area_km2": ordered.dropna(subset=["area_km2"]).groupby("codigo_ibge")["area_km2"].last(),
        "densidade_demografica": ordered.dropna(subset=["densidade_demografica"])
        .groupby("codigo_ibge")["densidade_demografica"].last(),
    }).rename_axis("codigo_ibge").reset_index()

    centroids = []
    for feature in geojson["features"]:
        lat, lon = geometry_centroid(feature["geometry"])
        centroids.append({"codigo_ibge": int(feature["properties"]["codigo_ibge"]), "lat": lat, "lon": lon})
    centroids = pd.DataFrame(centroids, columns=["codigo_ibge", "lat", "lon"])
    if centroids["codigo_ibge"].duplicated().any():
        raise ValueError("Malha geográfica com código de município duplicado.")
    if not (centroids["lat"].between(-30, -25).all() and centroids["lon"].between(-54, -48).all()):
        raise ValueError("Malha geográfica com coordenadas fora de Santa Catarina.")

    frame = frame.merge(regions.drop(columns="nome", errors="ignore"), on="codigo_ibge", how="left", validate="one_to_one")
    frame = frame.merge(centroids, on="codigo_ibge", how="left", validate="one_to_one")
    frame["possui_geometria"] = frame["lat"].notna()
    return frame.sort_values("nome_municipio").reset_index(drop=True)


def centroids_from_geojson(geojson: dict) -> pd.DataFrame:
    """codigo_ibge, nome, lat, lon do centroide do maior polígono de cada município."""
    rows = []
    for feature in geojson["features"]:
        lat, lon = geometry_centroid(feature["geometry"])
        rows.append({"codigo_ibge": int(feature["properties"]["codigo_ibge"]),
                     "nome": feature["properties"].get("nome", ""), "lat": lat, "lon": lon})
    return pd.DataFrame(rows, columns=["codigo_ibge", "nome", "lat", "lon"])
