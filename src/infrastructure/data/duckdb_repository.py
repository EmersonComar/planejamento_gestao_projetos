"""Repositório analítico: DuckDB em memória com views sobre os Parquet pré-calculados."""
from __future__ import annotations

import json
import threading
from functools import cached_property
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

from src.domain.ports import IAnalyticsRepository
from src.infrastructure.data.app_data_builder import SCHEMA_VERSION, TABLES, AppDataPaths, file_sha256



class AppDataUnavailableError(RuntimeError):
    """A base pré-calculada não existe ou é incompatível; rode scripts/build_data.py."""


class DuckDbAnalyticsRepository(IAnalyticsRepository):
    def __init__(self, root: Path, memory_limit: str = "256MB", threads: int = 2):
        self._paths = AppDataPaths(Path(root))
        missing = [str(self._paths.table(name)) for name in TABLES if not self._paths.table(name).exists()]
        if missing or not self._paths.metadata.exists():
            raise AppDataUnavailableError("Base do app não encontrada: " + ", ".join(missing or [str(self._paths.metadata)]))
        if self.metadata().get("versao_esquema") != SCHEMA_VERSION:
            raise AppDataUnavailableError("Base do app gerada com outra versão de esquema.")
        self._con = duckdb.connect(":memory:", config={"memory_limit": memory_limit, "threads": threads})
        self._lock = threading.Lock()
        for name in TABLES:
            path = str(self._paths.table(name)).replace("'", "''")
            self._con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")

    def query(self, sql: str, params: Optional[list] = None) -> pd.DataFrame:
        """Executa SQL somente leitura; um cursor por chamada (seguro entre threads)."""
        with self._lock:
            cursor = self._con.cursor()
        try:
            return cursor.execute(sql, params or []).df()
        finally:
            cursor.close()

    # ----- metadados e dimensões -----
    @cached_property
    def _metadata(self) -> dict:
        return json.loads(self._paths.metadata.read_text(encoding="utf-8"))

    def metadata(self) -> dict:
        return dict(self._metadata)

    def is_stale(self) -> bool:
        """True se CSV, modelo ou malha mudaram desde a geração (fontes ausentes não contam)."""
        sources = {
            "csv_sha256": self._paths.csv, "modelo_sha256": self._paths.model,
            "malha_sha256": self._paths.geojson, "regioes_sha256": self._paths.regions,
        }
        return any(path.exists() and file_sha256(path) != self._metadata.get(key) for key, path in sources.items())

    def periods(self) -> list[pd.Timestamp]:
        return self.query("SELECT DISTINCT ano_mes FROM mensal ORDER BY 1")["ano_mes"].tolist()

    def scenario_periods(self) -> list[pd.Timestamp]:
        return self.query("SELECT DISTINCT ano_mes FROM cenarios ORDER BY 1")["ano_mes"].tolist()

    def municipalities(self) -> pd.DataFrame:
        return self.query("SELECT * FROM municipios ORDER BY nome_municipio")

    def geojson(self) -> dict:
        return json.loads(self._paths.geojson.read_text(encoding="utf-8"))

    # ----- consultas -----
    def monthly(self, codigo_ibge: Optional[int] = None, start=None, end=None) -> pd.DataFrame:
        where, params = self._filters(codigo_ibge, start, end)
        return self.query(f"SELECT * FROM mensal {where} ORDER BY codigo_ibge, ano_mes", params)

    def state_monthly(self, start=None, end=None) -> pd.DataFrame:
        """Série estadual. Incidência = casos / população do estado (não média de municípios)."""
        where, params = self._filters(None, start, end)
        return self.query(f"""
            SELECT ano_mes,
                   SUM(casos)::BIGINT AS casos,
                   SUM(populacao)::BIGINT AS populacao,
                   SUM(casos) * 1e5 / NULLIF(SUM(populacao), 0) AS incidencia_100k,
                   COUNT(*) AS municipios,
                   COUNT(*) FILTER (WHERE incidencia_alta_observada) AS municipios_incidencia_alta,
                   COUNT(*) FILTER (WHERE risco = 'Alto') AS municipios_risco_alto,
                   COUNT(*) FILTER (WHERE entradas_validas) AS municipios_classificados,
                   AVG(temperatura_media) AS temperatura_media,
                   AVG(umidade_media) AS umidade_media,
                   AVG(precipitacao_total) AS precipitacao_total
            FROM mensal {where}
            GROUP BY ano_mes ORDER BY ano_mes
        """, params)

    def map_snapshot(self, period) -> pd.DataFrame:
        """Um registro por município no período: histórico se existir, senão cenário simulado."""
        period = pd.Timestamp(period)
        historic = self.query("SELECT COUNT(*) AS n FROM mensal WHERE ano_mes = ?", [period])["n"].iat[0] > 0
        if historic:
            sql = """
                SELECT m.codigo_ibge, m.nome_municipio, m.ano_mes, 'historico' AS tipo,
                       m.casos, m.incidencia_100k, m.populacao, m.incidencia_alta_observada,
                       m.temperatura_media, m.umidade_media, m.precipitacao_total,
                       m.casos_lag1, m.incidencia_lag1, NULL::TIMESTAMP AS periodo_referencia,
                       m.entradas_validas, m.campos_pendentes, m.prob_alto, m.risco,
                       u.mesorregiao, u.regiao_imediata
                FROM mensal m LEFT JOIN municipios u USING (codigo_ibge)
                WHERE m.ano_mes = ?"""
        else:
            sql = """
                SELECT c.codigo_ibge, c.nome_municipio, c.ano_mes, 'cenario' AS tipo,
                       NULL::BIGINT AS casos, NULL::DOUBLE AS incidencia_100k, u.populacao,
                       NULL::BOOLEAN AS incidencia_alta_observada,
                       c.temperatura_media, c.umidade_media, c.precipitacao_total,
                       c.casos_lag1, c.incidencia_lag1, c.periodo_referencia,
                       c.entradas_validas, c.campos_pendentes, c.prob_alto, c.risco,
                       u.mesorregiao, u.regiao_imediata
                FROM cenarios c LEFT JOIN municipios u USING (codigo_ibge)
                WHERE c.ano_mes = ?"""
        return self.query(sql + " ORDER BY nome_municipio", [period])

    def ranking(self, start=None, end=None, limit: int = 10) -> pd.DataFrame:
        """Municípios com mais casos no intervalo: incidência acumulada (sobre a população média), meses em nível
        epidêmico e maior incidência mensal (a que é comparada com o limiar epidêmico)."""
        where, params = self._filters(None, start, end)
        return self.query(f"""
            SELECT codigo_ibge, ANY_VALUE(nome_municipio) AS nome_municipio,
                   SUM(casos)::BIGINT AS casos,
                   SUM(casos) * 1e5 / NULLIF(AVG(populacao), 0) AS incidencia_100k,
                   COUNT(*) FILTER (WHERE incidencia_alta_observada) AS meses_incidencia_alta,
                   MAX(incidencia_100k) AS incidencia_pico_mensal,
                   ROUND(AVG(populacao))::BIGINT AS populacao
            FROM mensal {where}
            GROUP BY codigo_ibge
            ORDER BY casos DESC, nome_municipio
            LIMIT ?""", [*params, int(limit)])

    def calendar_profile(self, codigo_ibge: Optional[int] = None) -> pd.DataFrame:
        """Perfil típico por mês do calendário: médias anuais de casos, incidência e clima."""
        where, params = self._filters(codigo_ibge, None, None)
        return self.query(f"""
            WITH por_ano AS (
                SELECT ano, mes, SUM(casos) AS casos,
                       SUM(casos) * 1e5 / NULLIF(SUM(populacao), 0) AS incidencia_100k,
                       AVG(temperatura_media) AS temperatura_media,
                       AVG(umidade_media) AS umidade_media,
                       AVG(precipitacao_total) AS precipitacao_total
                FROM mensal {where} GROUP BY ano, mes
            )
            SELECT mes, AVG(casos) AS casos_medios, MAX(casos)::BIGINT AS casos_max,
                   AVG(incidencia_100k) AS incidencia_media,
                   AVG(temperatura_media) AS temperatura_media,
                   AVG(umidade_media) AS umidade_media,
                   AVG(precipitacao_total) AS precipitacao_total,
                   COUNT(*) AS anos
            FROM por_ano GROUP BY mes ORDER BY mes""", params)

    def month_year_matrix(self, codigo_ibge: Optional[int] = None) -> pd.DataFrame:
        """Casos e incidência por ano × mês (estado ou município) para mapas de calor."""
        where, params = self._filters(codigo_ibge, None, None)
        return self.query(f"""
            SELECT ano, mes, SUM(casos)::BIGINT AS casos,
                   SUM(casos) * 1e5 / NULLIF(SUM(populacao), 0) AS incidencia_100k
            FROM mensal {where}
            GROUP BY ano, mes ORDER BY ano, mes""", params)

    @staticmethod
    def _filters(codigo_ibge, start, end) -> tuple[str, list]:
        clauses, params = [], []
        if codigo_ibge is not None:
            clauses.append("codigo_ibge = ?")
            params.append(int(codigo_ibge))
        if start is not None:
            clauses.append("ano_mes >= ?")
            params.append(pd.Timestamp(start))
        if end is not None:
            clauses.append("ano_mes <= ?")
            params.append(pd.Timestamp(end))
        return ("WHERE " + " AND ".join(clauses)) if clauses else "", params
