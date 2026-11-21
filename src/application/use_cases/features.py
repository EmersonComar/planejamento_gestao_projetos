"""Atributos do modelo de risco, calculados de forma idêntica no treino, no build do painel e no simulador.

Todos os atributos usam apenas informação disponível até o mês anterior ao mês previsto, exceto o
clima e o mês do calendário (o modelo classifica o mês corrente a partir do clima observado ou suposto).
Lacunas ficam como NaN — nada é preenchido com zero.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

N_NEIGHBORS = 6


def _lag(frame: pd.DataFrame, column: str, months: int) -> pd.Series:
    """Valor de ``column`` do mesmo município ``months`` meses antes (mês calendário, sem deslocar lacunas)."""
    source = frame[["codigo_ibge", "_period", column]].copy()
    source["_period"] = source["_period"] + months
    merged = frame[["codigo_ibge", "_period"]].merge(source, on=["codigo_ibge", "_period"], how="left")
    return pd.Series(merged[column].to_numpy(), index=frame.index)


def neighbor_table(municipalities: pd.DataFrame, k: int = N_NEIGHBORS) -> dict[int, list[int]]:
    """k municípios mais próximos pelo centroide (distância aproximada em km)."""
    coords = municipalities.dropna(subset=["lat", "lon"])
    lat = np.radians(coords["lat"].to_numpy())
    lon = np.radians(coords["lon"].to_numpy())
    x = lon * np.cos(lat.mean())
    distance = np.hypot(x[:, None] - x[None, :], lat[:, None] - lat[None, :])
    np.fill_diagonal(distance, np.inf)
    codes = coords["codigo_ibge"].astype(int).to_numpy()
    nearest = np.argsort(distance, axis=1)[:, :k]
    return {int(codes[i]): [int(codes[j]) for j in nearest[i]] for i in range(len(codes))}


def add_model_features(frame: pd.DataFrame, neighbors: dict[int, list[int]]) -> pd.DataFrame:
    """Recebe a base mensal (casos, incidencia_100k, populacao, clima) e devolve com os atributos."""
    frame = frame.sort_values(["codigo_ibge", "ano_mes"]).copy()
    if frame.duplicated(["codigo_ibge", "ano_mes"]).any():
        raise ValueError("Há mais de um registro por município e mês na base.")
    frame["_period"] = frame["ano_mes"].dt.to_period("M")
    frame["mes"] = frame["ano_mes"].dt.month

    frame["casos_lag1"] = _lag(frame, "casos", 1)
    for months in (1, 2, 3, 12):
        frame[f"incidencia_lag{months}"] = _lag(frame, "incidencia_100k", months)
    for column in ("temperatura_media", "precipitacao_total", "umidade_media"):
        frame[f"{column}_lag1"] = _lag(frame, column, 1)
    frame["precipitacao_total_lag2"] = _lag(frame, "precipitacao_total", 2)

    frame["crescimento"] = np.log1p(frame["incidencia_lag1"]) - np.log1p(frame["incidencia_lag2"])
    frame["incidencia_media3"] = frame[["incidencia_lag1", "incidencia_lag2", "incidencia_lag3"]].mean(axis=1, skipna=False)
    # média histórica do município até o mês anterior (expansiva, sem olhar o futuro)
    frame["incidencia_historica"] = (
        frame.groupby("codigo_ibge")["incidencia_lag1"].transform(lambda s: s.expanding().mean())
    )

    state = frame.groupby("_period").agg(casos=("casos", "sum"), populacao=("populacao", "sum"))
    state_incidence = state["casos"] * 1e5 / state["populacao"]
    state_incidence.index = state_incidence.index + 1
    frame["incidencia_estado_lag1"] = frame["_period"].map(state_incidence)

    wide = frame.pivot(index="_period", columns="codigo_ibge", values="incidencia_lag1")
    neighbor_mean = pd.DataFrame({
        code: wide[[n for n in neighbors.get(int(code), []) if n in wide.columns]].mean(axis=1)
        for code in wide.columns
    })
    stacked = neighbor_mean.stack().rename("incidencia_vizinhos_lag1").reset_index()
    stacked.columns = ["_period", "codigo_ibge", "incidencia_vizinhos_lag1"]
    frame = frame.merge(stacked, on=["_period", "codigo_ibge"], how="left")

    frame["log_populacao"] = np.log(frame["populacao"])
    return frame.drop(columns="_period")
