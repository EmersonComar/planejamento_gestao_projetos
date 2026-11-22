# Modelo de risco e validação dos dados

## Definições

- **Caso no painel**: caso provável de dengue — confirmados, suspeitos e inconclusivos, sem os descartados
  (`casprov` do InfoDengue). A DIVE/SC usa a mesma definição, mas publica uma série oficial estadual separada.
  O total de notificações, que inclui os descartados, fica na coluna `notificacoes`.
- **Incidência**: casos prováveis do mês ÷ população do município naquele ano (IBGE) × 100 mil.
- **Mês epidêmico (alvo do modelo)**: incidência mensal de casos prováveis ≥ 300 por 100 mil.

Regras de montagem da base (`src/application/use_cases/base_analitica.py`):
- **Semanas:** a semana epidemiológica entra no mês em que começa, e a semana 53 é incluída.
- **População:** estimativas anuais do IBGE (tabela 6579) e Censo 2022 (tabela 4714). Em 2023 o
  IBGE não publicou estimativa municipal, então o valor é interpolado geometricamente.
- **Área:** Censo 2022.
- **Chuva:** cada município usa a estação automática do INMET mais próxima do seu centro que mediu
  ao menos 70% das horas do mês, até 60 km. Somar horas sem medição como zero subestimaria a chuva.
- **Lacunas:** ficam ausentes; nada é preenchido com zero.

## DIVE/SC como referência oficial estadual

A DIVE/SC é a fonte de verdade para os totais estaduais divulgados em seus informes. A série do
InfoDengue é mantida para análises por município e para o modelo, pois os informes usados aqui
publicam totais estaduais mensais, não a série municipal necessária ao painel. Os valores do
InfoDengue não são ajustados para coincidir com a DIVE.

`data/referencia/dive_sc_dengue_mensal.csv` traz os casos prováveis e as notificações por mês de
início dos sintomas, extraídos automaticamente dos Informes Epidemiológicos nº 34/2024, 17/2025 e
11/2026 (`src/infrastructure/sources/dive.py`). Os valores da referência foram conferidos mês a
mês com os três PDFs. A tabela abaixo compara a série municipal agregada do painel com os totais
estaduais oficiais da DIVE; exclui o mês mais recente de cada informe por cautela, para evitar
períodos possivelmente parciais:

| Ano/período | Casos prováveis do painel vs DIVE | Notificações do painel vs DIVE |
|---|---:|---:|
| 2024 (jan–nov) | +7,85% (+26.347) | +4,29% (+24.304) |
| 2025 (jan–nov) | +12,60% (+3.228) | +6,00% (+8.019) |
| 2026 (jan–out) | +18,26% (+637) | +5,44% (+2.069) |

A base agrega semanas epidemiológicas do InfoDengue, cujos dados são revisados retrospectivamente.
A DIVE publica dados do SINAN agrupados pelo mês de início dos sintomas, com data de corte própria;
casos suspeitos também podem ser reclassificados. As diferenças mensais podem ser maiores que as
anuais. Em 2026, o informe 11/2026 contém novembro, mas a base do painel termina em outubro; o
período comparável é janeiro a outubro. A página "Sobre os dados" do painel recalcula essa tabela
a partir da base vigente.

## Modelo

Treinado no notebook `notebooks/notebook_modelo_baseline.ipynb` (código em
`src/application/use_cases/model_training.py`). O modelo final é um `VotingClassifier` com voto
suave entre `RandomForestClassifier` e `HistGradientBoostingClassifier` (scikit-learn 1.6.1).

São 20 atributos, calculados por `src/application/use_cases/features.py`, o mesmo código usado no
treino, no painel e no simulador:
- clima do mês;
- casos e incidência dos meses anteriores (1, 2, 3 e 12 meses), tendência e média de 3 meses;
- clima defasado;
- histórico do município;
- incidência no estado e nos 6 municípios vizinhos no mês anterior;
- densidade e população.

O baseline é um Random Forest com 7 dessas informações: clima do mês, densidade, mês e casos e
incidência do mês anterior.

### Validação temporal

Para cada ano de teste T, de 2023 a 2026:
1. treina com os anos até T-2;
2. escolhe o limiar em T-1 (maior precisão com recall ≥ 85%);
3. re-treina até T-1 e testa em T.

O ano de teste nunca é usado para decidir nada. Validação cruzada com meses embaralhados não é
usada porque deixaria o modelo "ver o futuro".

| Média 2023–2026 | Baseline (RF, 7 atributos) | Modelo final (RF + HGB, 20 atributos) |
|---|---|---|
| PR-AUC | 0,698 | 0,740 |
| F1 | 0,452 | 0,507 |
| Precisão | 0,315 | 0,367 |
| Recall | 0,815 | 0,835 |
| Brier | 0,015 | 0,010 |

O limiar de decisão do modelo final (0,24) é escolhido nas previsões fora do tempo de todos os anos
de teste. Os números por ano estão em `models/metricas_modelo.json`.

Também foram avaliados:
- **Random Forest com os 20 atributos:** PR-AUC 0,719.
- **Gradient Boosting sem pesos por classe:** PR-AUC 0,736, maior precisão, mas recall de 76%, abaixo da meta.
- **Gradient Boosting com pesos por classe:** limiar instável entre anos.
- **Calibração sigmoide:** sem ganho.

Na importância por permutação, os casos recentes no município somam cerca de 65% e a temperatura
cerca de 20%, principalmente a do mês anterior.
