# models/

Modelos treinados e métricas de avaliação, gerados pelo notebook `notebooks/notebook_modelo_baseline.ipynb`
(ou por `scripts/train_model.py treinar`).

| Arquivo | Descrição |
|---|---|
| `modelo_risco_dengue.pkl` | **Modelo usado pelo painel.** Dicionário `joblib` com: o modelo (`VotingClassifier`: Random Forest + HistGradientBoosting, scikit-learn 1.6.1); a lista dos 20 atributos; o limiar de decisão; o limiar de incidência do alvo; a importância por permutação; as métricas. |
| `modelo_baseline_risco_dengue.pkl` | Modelo baseline (Random Forest com as 7 informações básicas), no mesmo formato. Serve de referência de comparação. |
| `metricas_modelo.json` | Métricas do modelo final na validação temporal, por ano de 2023 a 2026 e na média; comparação com o baseline; regra do limiar; importância dos atributos. |

**Alvo:** mês em que o município tem 300 casos prováveis ou mais por 100 mil habitantes.
**Limiar de decisão:** a maior precisão entre os limiares que detectam ao menos 85% dos meses
epidêmicos nas previsões fora do período de treino.

Depois de retreinar, gere a base do painel (`scripts/build_data.py`; o notebook já faz isso). Os
testes falham se o painel estiver gerado com um modelo diferente do versionado. Detalhes em
`docs/modelo-e-validacao.md`.
