"""IBGE: municípios e regiões, malha municipal, população por ano e área territorial."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.infrastructure.sources.http import get_json

UF = 42
AGREGADOS = "https://servicodados.ibge.gov.br/api/v3/agregados"
LOCALITIES_URL = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF}/municipios"
MESH_URL = (f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{UF}"
            "?formato=application/vnd.geo+json&qualidade=intermediaria&intrarregiao=municipio")
POPULATION_ESTIMATES = (6579, 9324)   # tabela, variável: estimativas anuais de população residente
CENSUS_2022 = 4714                    # Censo 2022: população (93) e área (6318)


def municipalities() -> pd.DataFrame:
    """Os 295 municípios com meso/microrregião e regiões intermediária/imediata."""
    rows = []
    for item in get_json(LOCALITIES_URL):
        rows.append({
            "codigo_ibge": int(item["id"]), "nome": item["nome"],
            "mesorregiao": item["microrregiao"]["mesorregiao"]["nome"],
            "microrregiao": item["microrregiao"]["nome"],
            "regiao_intermediaria": item["regiao-imediata"]["regiao-intermediaria"]["nome"],
            "regiao_imediata": item["regiao-imediata"]["nome"],
        })
    return pd.DataFrame(rows).sort_values("codigo_ibge").reset_index(drop=True)


def mesh(names: dict[int, str]) -> dict:
    """Malha municipal (qualidade intermediária) com propriedades `codigo_ibge` e `nome`."""
    raw = get_json(MESH_URL)
    features = []
    for feature in raw["features"]:
        code = int(feature["properties"]["codarea"])
        features.append({"type": "Feature", "id": code,
                         "properties": {"codigo_ibge": code, "nome": names.get(code, "")},
                         "geometry": feature["geometry"]})
    if len({f["id"] for f in features}) != len(features):
        raise ValueError("Malha do IBGE com código duplicado.")
    return {"type": "FeatureCollection", "features": features}


def _series(table: int, variable: int, year: int) -> pd.Series:
    data = get_json(f"{AGREGADOS}/{table}/periodos/{year}/variaveis/{variable}",
                    params={"localidades": f"N6[N3[{UF}]]"})
    if not data or not data[0]["resultados"]:
        return pd.Series(dtype="float64")
    values = {int(s["localidade"]["id"]): s["serie"][str(year)] for s in data[0]["resultados"][0]["series"]}
    return pd.to_numeric(pd.Series(values), errors="coerce")


def population(first_year: int, last_year: int) -> pd.DataFrame:
    """População residente por município e ano.

    Estimativas anuais (tabela 6579); em 2022, o Censo (tabela 4714). Anos sem publicação do IBGE
    (2023) são interpolados geometricamente entre os anos vizinhos; anos após a última estimativa
    repetem a última disponível. A coluna `origem` registra de onde veio cada valor.
    """
    frames = []
    for year in range(first_year, last_year + 1):
        values = _series(CENSUS_2022, 93, year) if year == 2022 else _series(*POPULATION_ESTIMATES, year)
        if not values.empty:
            frames.append(pd.DataFrame({"codigo_ibge": values.index, "ano": year, "populacao": values.to_numpy(),
                                        "origem": "Censo 2022" if year == 2022 else "Estimativa IBGE"}))
    observed = pd.concat(frames, ignore_index=True)
    wide = observed.pivot(index="codigo_ibge", columns="ano", values="populacao")
    full = wide.reindex(columns=range(first_year, last_year + 1))
    filled = np.exp(np.log(full).interpolate(axis=1, limit_area="inside")).ffill(axis=1).bfill(axis=1)
    result = filled.stack().rename("populacao").reset_index()
    result["populacao"] = result["populacao"].round().astype("int64")
    origin = observed.set_index(["codigo_ibge", "ano"])["origem"]
    result["origem"] = [origin.get((c, y), "Interpolada" if wide.columns.min() < y < wide.columns.max() else "Repetida")
                        for c, y in zip(result["codigo_ibge"], result["ano"])]
    return result


def area() -> pd.DataFrame:
    """Área territorial (km²) do Censo 2022 — inclui os municípios criados após 2010."""
    values = _series(CENSUS_2022, 6318, 2022)
    return pd.DataFrame({"codigo_ibge": values.index, "area_km2": values.to_numpy()})
