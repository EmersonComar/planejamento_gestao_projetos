"""Treino e avaliação do modelo de risco de dengue com validação temporal (sem vazamento).

Alvo: mês em que o município tem incidência de casos prováveis >= 300 por 100 mil habitantes.

Protocolo (janela temporal): para cada ano de teste T, o modelo é treinado com os anos até T-2, o
limiar de decisão é escolhido em T-1 e o modelo é re-treinado até T-1 para prever T. Nenhuma
decisão usa o ano de teste.

Regra do limiar: maior precisão entre os limiares que detectam pelo menos ``MIN_RECALL`` dos meses
epidêmicos (prioridade a não perder epidemias).
"""
from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score, brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score,
)

from src.application.use_cases.features import add_model_features, neighbor_table

EPIDEMIC_THRESHOLD = 300.0
MIN_RECALL = 0.85
TEST_YEARS = (2023, 2024, 2025, 2026)
SEED = 42
METRIC_COLUMNS = ["pr_auc", "roc_auc", "precisao", "recall", "f1", "brier"]

BASE_FEATURES = ["temperatura_media", "umidade_media", "precipitacao_total", "densidade_demografica",
                 "mes", "casos_lag1", "incidencia_lag1"]
RICH_FEATURES = BASE_FEATURES + [
    "incidencia_lag2", "incidencia_lag3", "incidencia_lag12", "crescimento", "incidencia_media3",
    "temperatura_media_lag1", "precipitacao_total_lag1", "precipitacao_total_lag2", "umidade_media_lag1",
    "incidencia_historica", "incidencia_estado_lag1", "incidencia_vizinhos_lag1", "log_populacao",
]


def random_forest():
    return RandomForestClassifier(n_estimators=300, min_samples_leaf=5, class_weight="balanced",
                                  random_state=SEED, n_jobs=-1)


def gradient_boosting(weighted: bool = False):
    return HistGradientBoostingClassifier(learning_rate=0.05, max_iter=300, max_leaf_nodes=15,
                                          min_samples_leaf=80, l2_regularization=1.0,
                                          class_weight="balanced" if weighted else None, random_state=SEED)


def rf_plus_gb():
    """Média das probabilidades de um Random Forest e de um Gradient Boosting."""
    return VotingClassifier([("rf", random_forest()), ("hgb", gradient_boosting())], voting="soft")


# nome: (fábrica do estimador, atributos, descrição)
CANDIDATES = {
    "baseline": (random_forest, BASE_FEATURES, "Random Forest com as 7 informações básicas"),
    "rf_completo": (random_forest, RICH_FEATURES, "Random Forest com as 20 informações"),
    "hgb_ponderado_completo": (lambda: gradient_boosting(weighted=True), RICH_FEATURES,
                               "Gradient Boosting com pesos por classe, 20 informações"),
    "hgb_completo": (gradient_boosting, RICH_FEATURES, "Gradient Boosting, 20 informações"),
    "rf+hgb_completo": (rf_plus_gb, RICH_FEATURES, "Random Forest + Gradient Boosting, 20 informações"),
}
CHOSEN = "rf+hgb_completo"
MODEL_NAMES = {"baseline": "Random Forest", "rf+hgb_completo": "Random Forest + Gradient Boosting"}


def prepare_dataset(base: pd.DataFrame, centroids: pd.DataFrame) -> pd.DataFrame:
    """Atributos do modelo + alvo; exclui meses sem casos do mês anterior (início da série)."""
    frame = add_model_features(base, neighbor_table(centroids))
    frame["alvo"] = (frame["incidencia_100k"] >= EPIDEMIC_THRESHOLD).astype(int)
    frame["ano"] = frame["ano_mes"].dt.year
    return frame.loc[frame["casos_lag1"].notna()].reset_index(drop=True)


def choose_threshold(y: np.ndarray, scores: np.ndarray, min_recall: float = MIN_RECALL) -> float:
    grid = np.round(np.arange(0.02, 0.981, 0.01), 2)
    best, best_precision = None, -1.0
    for threshold in grid:
        predicted = scores >= threshold
        if y.sum() == 0 or recall_score(y, predicted, zero_division=0) < min_recall:
            continue
        precision = precision_score(y, predicted, zero_division=0)
        if precision > best_precision:
            best, best_precision = threshold, precision
    if best is None:  # nenhum limiar atinge o recall mínimo: usa o que maximiza F1
        best = max(grid, key=lambda t: f1_score(y, scores >= t, zero_division=0))
    return float(best)


def _fit(make, features, train: pd.DataFrame, calibration: pd.DataFrame | None = None):
    model = make().fit(train[features], train["alvo"])
    if calibration is not None and calibration["alvo"].sum() >= 5:
        model = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid").fit(
            calibration[features], calibration["alvo"])
    return model


def evaluate(name: str, data: pd.DataFrame, calibrate: bool = False, scores_out: list | None = None) -> list[dict]:
    """Avaliação por ano de teste (janela temporal)."""
    make, features, _ = CANDIDATES[name]
    rows = []
    for year in TEST_YEARS:
        train = data[data["ano"] <= year - 2]
        validation = data[data["ano"] == year - 1]
        test = data[data["ano"] == year]
        if test.empty:
            continue
        inner = _fit(make, features, train, validation if calibrate else None)
        threshold = choose_threshold(validation["alvo"].to_numpy(), inner.predict_proba(validation[features])[:, 1])
        scores = _fit(make, features, pd.concat([train, validation])).predict_proba(test[features])[:, 1]
        predicted = scores >= threshold
        y = test["alvo"].to_numpy()
        if scores_out is not None:
            scores_out.append(pd.DataFrame({"alvo": y, "pontuacao": scores, "ano": year}))
        rows.append({
            "modelo": name + ("+calibracao" if calibrate else ""), "ano_teste": year, "registros": int(len(test)),
            "meses_epidemicos": int(y.sum()), "limiar": threshold,
            "pr_auc": float(average_precision_score(y, scores)) if y.sum() else None,
            "roc_auc": float(roc_auc_score(y, scores)) if 0 < y.sum() < len(y) else None,
            "precisao": float(precision_score(y, predicted, zero_division=0)),
            "recall": float(recall_score(y, predicted, zero_division=0)) if y.sum() else None,
            "f1": float(f1_score(y, predicted, zero_division=0)) if y.sum() else None,
            "brier": float(brier_score_loss(y, scores)),
            "alertas": int(predicted.sum()),
        })
    return rows


def summarize(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows).groupby("modelo")[METRIC_COLUMNS].mean().sort_values("pr_auc", ascending=False)


def train(name: str, data: pd.DataFrame, baseline_rows: list[dict] | None = None,
          evaluation: tuple[list[dict], list[pd.DataFrame]] | None = None) -> dict:
    """Avalia, escolhe o limiar final, treina com todos os dados e devolve o artefato do modelo.

    ``evaluation``: resultado já calculado de ``evaluate(name, data, scores_out=...)`` (linhas e
    pontuações), para não repetir a avaliação.

    Limiar final: aplicado às previsões fora do tempo de todos os anos de teste (cada uma feita por
    um modelo que não viu aquele ano). As métricas por ano usam limiares escolhidos só com o passado.
    """
    make, features, description = CANDIDATES[name]
    if evaluation is None:
        pooled: list[pd.DataFrame] = []
        rows = evaluate(name, data, scores_out=pooled)
    else:
        rows, pooled = evaluation
    pooled_scores = pd.concat(pooled)
    threshold = choose_threshold(pooled_scores["alvo"].to_numpy(), pooled_scores["pontuacao"].to_numpy())
    model = make().fit(data[features], data["alvo"])

    recent = data[data["ano"] >= data["ano"].max() - 2]
    importance = permutation_importance(model, recent[features], recent["alvo"], scoring="average_precision",
                                        n_repeats=5, random_state=SEED, n_jobs=-1)
    weights = np.clip(importance.importances_mean, 0, None)
    global_importance = dict(zip(features, (weights / weights.sum()).round(4).tolist()))

    metrics = {
        "gerado_em": datetime.now(UTC).isoformat(timespec="seconds"),
        "configuracao": name,
        "descricao": description,
        "alvo": f"incidência mensal de casos prováveis >= {EPIDEMIC_THRESHOLD:g} por 100 mil habitantes",
        "periodo_treino": f"{data['ano_mes'].min():%Y-%m} a {data['ano_mes'].max():%Y-%m}",
        "limiar_decisao": threshold,
        "regra_limiar": (f"maior precisão com recall >= {MIN_RECALL:.0%} nas previsões fora do tempo de "
                         f"{min(TEST_YEARS)}–{max(TEST_YEARS)}"),
        "avaliacao_por_ano": rows,
        "media": pd.DataFrame(rows)[METRIC_COLUMNS].mean().to_dict(),
        "importancia_global": global_importance,
    }
    if baseline_rows:
        metrics["comparacao_baseline"] = pd.DataFrame(baseline_rows)[METRIC_COLUMNS].mean().to_dict()
    return {
        "modelo": model,
        "nome_modelo": MODEL_NAMES.get(name, description),
        "atributos": features,
        "limiar_alto_risco_incidencia": EPIDEMIC_THRESHOLD,
        "limiar_decisao_modelo": threshold,
        "importancia_global": global_importance,
        "sklearn_version": sklearn.__version__,
        "metricas": metrics,
    }
