from __future__ import annotations

import pandas as pd

from src.domain.ports import IDataRepository


class DashboardAnalyticsUseCase:
    def __init__(self, repo: IDataRepository):
        self._repo = repo

    @staticmethod
    def _sample_for_chart(frame: pd.DataFrame, max_rows: int = 2000) -> pd.DataFrame:
        if frame is None or frame.empty:
            return frame
        if len(frame) <= max_rows:
            return frame
        return frame.sample(n=max_rows, random_state=42).copy()

    def build_dashboard_snapshot(self) -> dict:
        df_full = self._repo.load()
        summary = self._repo.get_state_summary_by_period()

        top_mun = (
            df_full.groupby("nome_municipio", as_index=False)["incidencia_100k"]
            .sum()
            .sort_values("incidencia_100k", ascending=False)
            .head(15)
            .copy()
        )
        top_mun["nome_municipio"] = pd.Categorical(
            top_mun["nome_municipio"],
            categories=top_mun["nome_municipio"].tolist(),
            ordered=True,
        )

        hypotheses = {
            "sazonalidade": (
                df_full.assign(mes=df_full["ano_mes"].dt.month)
                .groupby("mes", as_index=False)["casos"]
                .sum()
                .rename(columns={"mes": "Mes", "casos": "Casos"})
            ),
            "temperatura": self._sample_for_chart(
                df_full[["temperatura_media", "incidencia_100k"]].dropna().copy()
            ),
            "precipitacao": self._sample_for_chart(
                (
                    df_full[["precipitacao_total", "incidencia_100k"]]
                    .dropna()
                    .copy()
                    .assign(precipitacao_total_lag1=lambda frame: frame["precipitacao_total"].shift(1).fillna(0))
                )
            ),
            "umidade": self._sample_for_chart(
                df_full[["umidade_media", "incidencia_100k"]].dropna().copy()
            ),
            "densidade": self._sample_for_chart(
                df_full[["densidade_demografica", "incidencia_100k"]].dropna().copy()
            ),
            "saneamento": (
                self._sample_for_chart(
                    df_full[["remocao_dbo_media", "incidencia_100k"]].dropna().copy()
                )
                if "remocao_dbo_media" in df_full.columns
                else None
            ),
            "dependencia_temporal": self._sample_for_chart(
                (
                    df_full.sort_values(["codigo_ibge", "ano_mes"]).copy()
                    .assign(casos_lag1=lambda frame: frame.groupby("codigo_ibge")["casos"].transform(lambda series: series.shift(1).fillna(0)))
                    [["casos", "casos_lag1"]]
                    .dropna()
                    .copy()
                )
            ),
        }

        return {
            "df_full": df_full,
            "summary": summary,
            "top_mun": top_mun,
            "hypotheses": hypotheses,
        }

    def build_municipality_snapshot(self, municipality: str) -> dict:
        df_mun = self._repo.filter_by_municipality(municipality).sort_values("ano_mes").copy()
        df_mun["mes"] = df_mun["ano_mes"].dt.month
        df_mun["casos_lag1"] = df_mun["casos"].shift(1).fillna(0.0)
        df_mun["incidencia_lag1"] = df_mun["incidencia_100k"].shift(1).fillna(0.0)

        return {
            "municipality": municipality,
            "df": df_mun,
            "casos_por_tempo": self._sample_for_chart(
                df_mun[["ano_mes", "casos"]].rename(columns={"ano_mes": "ano_mes", "casos": "Casos"})
            ),
            "temperatura_x_incidencia": self._sample_for_chart(
                df_mun[["temperatura_media", "incidencia_100k"]].dropna().copy()
            ),
            "umidade_x_incidencia": self._sample_for_chart(
                df_mun[["umidade_media", "incidencia_100k"]].dropna().copy()
            ),
            "precipitacao_x_incidencia": self._sample_for_chart(
                df_mun[["precipitacao_total", "incidencia_100k"]].dropna().copy()
            ),
            "lag_casos": self._sample_for_chart(
                df_mun[["ano_mes", "casos", "casos_lag1"]].copy()
            ),
            "detalhes": df_mun[[
                "ano_mes",
                "casos",
                "incidencia_100k",
                "temperatura_media",
                "umidade_media",
                "precipitacao_total",
                "densidade_demografica",
                "populacao",
            ]].copy(),
        }
