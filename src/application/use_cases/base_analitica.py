"""Montagem da base analítica mensal (município × mês) a partir das fontes já baixadas.

Definições:
- `casos`: casos prováveis de dengue (confirmados, suspeitos e inconclusivos; sem descartados),
  conceito adotado pela DIVE/SC. Origem: campo `casprov` do InfoDengue, somado por mês.
- `notificacoes`: todas as notificações, inclusive descartadas (campo `casos` do InfoDengue).
- `incidencia_100k`: casos prováveis do mês / população do ano × 100 mil.
- População: IBGE (estimativas anuais e Censo 2022). Área: Censo 2022.
- Temperatura e umidade: InfoDengue. Chuva: estação automática do INMET mais próxima do município.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MAX_STATION_KM = 60.0
MIN_HOURS_COVERAGE = 0.7  # mês com menos de 70% das horas medidas fica sem chuva

BASE_COLUMNS = [
    "codigo_ibge", "nome_municipio", "ano_mes", "casos", "notificacoes", "populacao", "incidencia_100k",
    "temperatura_media", "temperatura_min", "temperatura_max", "umidade_media", "umidade_min", "umidade_max",
    "ano", "area_km2", "densidade_demografica", "precipitacao_total", "qtd_ete_ativas", "remocao_dbo_media",
]


def monthly_from_weekly(weekly: pd.DataFrame, last_complete_month: pd.Period) -> pd.DataFrame:
    """Agrega a série semanal do InfoDengue por mês (semana atribuída ao mês do seu início)."""
    weekly = weekly.copy()
    weekly["data_semana"] = pd.to_datetime(weekly["data_iniSE"], unit="ms")
    weekly["ano_mes"] = weekly["data_semana"].dt.to_period("M")
    weekly = weekly.loc[weekly["ano_mes"] <= last_complete_month].drop_duplicates(["codigo_ibge", "data_semana"])
    for column in ("casos", "casprov", "tempmin", "tempmed", "tempmax", "umidmin", "umidmed", "umidmax"):
        weekly[column] = pd.to_numeric(weekly[column], errors="coerce")
    monthly = (
        weekly.groupby(["codigo_ibge", "nome_municipio", "ano_mes"])
        .agg(casos=("casprov", "sum"), notificacoes=("casos", "sum"),
             temperatura_media=("tempmed", "mean"), temperatura_min=("tempmin", "mean"),
             temperatura_max=("tempmax", "mean"), umidade_media=("umidmed", "mean"),
             umidade_min=("umidmin", "mean"), umidade_max=("umidmax", "mean"))
        .reset_index()
    )
    monthly["casos"] = monthly["casos"].round().astype("int64")
    monthly["notificacoes"] = monthly["notificacoes"].round().astype("int64")
    return monthly


def _distance_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


def station_mapping(stations: pd.DataFrame, centroids: pd.DataFrame, max_km: float = MAX_STATION_KM) -> pd.DataFrame:
    """Estações do INMET a até ``max_km`` do centro de cada município, da mais próxima para a mais distante.

    ``stations``: codigo_estacao, nome_estacao, lat, lon (uma linha por estação).
    ``centroids``: codigo_ibge, nome, lat, lon. A coluna ``ordem`` (1 = mais próxima) define a
    preferência: em cada mês vale a estação mais próxima que tenha medido aquele mês.
    """
    distance = _distance_km(centroids["lat"].to_numpy()[:, None], centroids["lon"].to_numpy()[:, None],
                            stations["lat"].to_numpy()[None, :], stations["lon"].to_numpy()[None, :])
    long = pd.DataFrame({
        "codigo_ibge": np.repeat(centroids["codigo_ibge"].to_numpy(), len(stations)),
        "nome_municipio": np.repeat(centroids["nome"].to_numpy(), len(stations)),
        "codigo_estacao": np.tile(stations["codigo_estacao"].to_numpy(), len(centroids)),
        "nome_estacao": np.tile(stations["nome_estacao"].to_numpy(), len(centroids)),
        "distancia_km": distance.ravel().round(1),
    })
    long = long.loc[long["distancia_km"] <= max_km].sort_values(["nome_municipio", "distancia_km"])
    long["ordem"] = long.groupby("codigo_ibge").cumcount() + 1
    return long.reset_index(drop=True)


def latest_station_coordinates(stations_by_year: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por estação, com nome e coordenadas do ano mais recente (o cabeçalho tem erros em anos antigos)."""
    return (stations_by_year.sort_values("ano").groupby("codigo_estacao").tail(1)
            [["codigo_estacao", "nome_estacao", "lat", "lon"]].reset_index(drop=True))


def precipitation_by_municipality(station_monthly: pd.DataFrame, mapping: pd.DataFrame,
                                  min_coverage: float = MIN_HOURS_COVERAGE) -> pd.DataFrame:
    """Chuva mensal de cada município: estação mais próxima que mediu o mês (>= ``min_coverage`` das horas).

    Meses com poucas horas medidas não entram: somar horas sem medição como zero subestimaria a chuva.
    """
    frame = station_monthly.copy()
    hours_in_month = frame["ano_mes"].dt.days_in_month * 24
    valid = frame.loc[frame["horas_medidas"] >= min_coverage * hours_in_month,
                      ["codigo_estacao", "ano_mes", "precipitacao_total"]]
    candidates = mapping[["codigo_ibge", "codigo_estacao", "ordem"]].merge(valid, on="codigo_estacao")
    best = candidates.sort_values("ordem").drop_duplicates(["codigo_ibge", "ano_mes"])
    return best[["codigo_ibge", "ano_mes", "precipitacao_total"]].reset_index(drop=True)


def build_base(weekly: pd.DataFrame, population: pd.DataFrame, area: pd.DataFrame,
               precipitation: pd.DataFrame, sanitation: pd.DataFrame,
               last_complete_month: pd.Period) -> pd.DataFrame:
    base = monthly_from_weekly(weekly, last_complete_month)
    base["ano"] = base["ano_mes"].dt.year
    base = base.merge(population[["codigo_ibge", "ano", "populacao"]], on=["codigo_ibge", "ano"], how="left",
                      validate="many_to_one")
    if base["populacao"].isna().any():
        missing = base.loc[base["populacao"].isna(), "nome_municipio"].unique()[:5]
        raise ValueError(f"Municípios sem população do IBGE: {list(missing)}")
    base["incidencia_100k"] = base["casos"] * 1e5 / base["populacao"]
    base = base.merge(area, on="codigo_ibge", how="left", validate="many_to_one")
    base["densidade_demografica"] = base["populacao"] / base["area_km2"]
    base = base.merge(precipitation, on=["codigo_ibge", "ano_mes"], how="left", validate="one_to_one")
    base = base.merge(sanitation, on="codigo_ibge", how="left", validate="many_to_one")
    if base.duplicated(["codigo_ibge", "ano_mes"]).any():
        raise ValueError("Base com município e mês duplicados.")
    base["ano_mes"] = base["ano_mes"].dt.to_timestamp()
    return base[BASE_COLUMNS].sort_values(["codigo_ibge", "ano_mes"]).reset_index(drop=True)
