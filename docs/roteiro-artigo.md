# Roteiro do artigo

Guia para escrever o artigo a partir do que o repositório produz. Para cada seção, indica o
conteúdo, de onde vêm os números e as figuras que podem ser reaproveitadas. Os valores abaixo
correspondem à base de jan/2015 a out/2026. Se a base ou o modelo forem atualizados, confira-os
de novo nas fontes indicadas.

## Regra geral

O artigo **reproduz** números; não os calcula por conta própria.

| Tipo de informação | Onde buscar |
|---|---|
| Totais de casos, população, cobertura | [`notebook_eda_dengue.ipynb`](../notebooks/notebook_eda_dengue.ipynb), seções 2 a 4 |
| Hipóteses H1–H7 | [`notebook_eda_dengue.ipynb`](../notebooks/notebook_eda_dengue.ipynb), seção 5 (gráficos, correlações e conclusões) |
| Desempenho do modelo | [`models/metricas_modelo.json`](../models/metricas_modelo.json) e [`notebook_modelo_baseline.ipynb`](../notebooks/notebook_modelo_baseline.ipynb), seções 4 e 5 |
| Definições e métodos | [`docs/modelo-e-validacao.md`](modelo-e-validacao.md) |

Cite o painel (<https://dengue-sc.streamlit.app/>) como produto e o repositório
(<https://github.com/EmersonComar/planejamento_gestao_projetos>) como material de reprodução.
Quando houver uma versão pública do artigo, registre o link em `app/ui/links.py` (`ARTICLE_URL`)
e na tabela "Como navegar este projeto" do README.

## Estrutura sugerida

### 1. Introdução
- Dengue como problema de saúde pública e sua expansão recente em Santa Catarina: de 4.565 casos
  prováveis em 2015 para 363.859 em 2024.
- Objetivo: investigar a associação de clima, população e saneamento com a incidência e oferecer
  uma classificação de risco mensal por município, acessível ao público.

### 2. Fundamentação
- Ciclo do *Aedes aegypti* e do vírus: temperatura, chuva e umidade.
- Limiar de 300 casos por 100 mil habitantes para caracterizar epidemia.
- Classificação com classes raras: PR-AUC, precisão, recall.
- Validação temporal em séries temporais.

### 3. Dados
- **Fontes:** InfoDengue, IBGE, INMET, ANA e DIVE/SC. A tabela está na seção 1 do notebook de dados.
- **Definição de caso:** caso provável (confirmados, suspeitos e inconclusivos), conceito da DIVE/SC.
- **Unidade de análise:** município × mês; 295 municípios, 142 meses, 41.890 registros.
- **População e área:** população anual do IBGE (Censo 2022 e estimativas; 2023 interpolado) e área do Censo 2022.
- **Chuva:** estação automática do INMET mais próxima que mediu ao menos 70% das horas do mês, até 60 km.
- **Lacunas:** sem chuva em 9,1% das linhas; sem temperatura e umidade em 6,9%. Nada é preenchido com zero.
- **Conferência com os informes da DIVE/SC** (casos prováveis; notificações entre parênteses):
  - 2024: +8% (+4%);
  - 2025: +13% (+6%);
  - 2026: +33% (+5%).

  A diferença se explica pela data de referência: semana de notificação × início dos sintomas.
  Figura: comparação mensal, seção 4.2 do notebook de dados.

### 4. Análise exploratória (hipóteses)

Dados de 2022 em diante; correlação de Spearman. Figuras na seção 5 do notebook de dados.

| Hipótese | Resultado |
|---|---|
| H1 Sazonalidade | 81% dos casos entre março e maio |
| H2 Temperatura | ρ = 0,12 no mês; ρ = 0,25 com um mês de defasagem |
| H3 Chuva | ρ = 0,02; sem relação simples |
| H4 Umidade | ρ = 0,15; associação fraca |
| H5 Densidade | ρ = 0,40 entre os 295 municípios |
| H6 Saneamento | ρ = 0,09 (p = 0,5; 55 municípios com ETE); não confirmada |
| H7 Dependência temporal | ρ = 0,60. Após um mês epidêmico, 62% dos meses seguintes também são epidêmicos; após um mês sem casos, 0,1% |

### 5. Modelo
- **Alvo:** incidência mensal ≥ 300 casos prováveis por 100 mil habitantes. São 665 meses epidêmicos (1,6% dos registros), concentrados em 2022 (174), 2023 (87) e 2024 (342).
- **Atributos:** 7 no baseline e 20 no modelo final; a tabela está na seção 2 do notebook de modelagem.
- **Candidatos:** Random Forest, Gradient Boosting (com e sem pesos por classe) e a combinação dos dois.
- **Validação temporal:** para cada ano T de 2023 a 2026, treino até T-2, limiar escolhido em T-1, teste em T.
- **Regra do limiar:** maior precisão com recall ≥ 85%. O limiar final é 0,24.

### 6. Resultados

| Média 2023–2026 | Baseline (RF, 7 atributos) | Modelo final (RF + GB, 20 atributos) |
|---|---|---|
| PR-AUC | 0,698 | 0,740 |
| ROC-AUC | 0,979 | 0,978 |
| Recall | 0,815 | 0,835 |
| Precisão | 0,315 | 0,367 |
| F1 | 0,452 | 0,507 |
| Brier | 0,015 | 0,010 |

Por ano (modelo final):

| Ano | Meses epidêmicos | Alertas | Recall | Precisão | PR-AUC |
|---|---|---|---|---|---|
| 2023 | 87 | 196 | 0,85 | 0,38 | 0,66 |
| 2024 | 342 | 817 | 1,00 | 0,42 | 0,92 |
| 2025 | 23 | 42 | 0,83 | 0,45 | 0,71 |
| 2026 | 3 | 9 | 0,67 | 0,22 | 0,67 |

- **Importância por permutação:** casos recentes no município, cerca de 65%; temperatura, cerca de 20% (a do mês anterior responde por 15%).
- **Figuras:** gráficos de PR-AUC e F1 por ano e de importância por grupo, nas seções 4 e 5 do notebook de modelagem.

### 7. Produto
- Painel com seis páginas, mapa, simulador e explicação do modelo para leigos. Capturas de tela podem ilustrar esta seção.
- Arquitetura: base pré-calculada em Parquet e DuckDB e publicação no Streamlit Community Cloud ([`docs/base-do-app.md`](base-do-app.md)).

### 8. Discussão e limitações
- Poucos anos epidêmicos: 2025 e 2026 têm 23 e 3 meses epidêmicos, o que deixa as métricas desses anos instáveis.
- Associação não é causa; sorotipos e imunidade não estão nos dados.
- O saneamento tem cobertura parcial (55 municípios) e mede tratamento, não acesso.
- Os cenários futuros são simulações com clima típico; o modelo não prevê o número de casos.
- Os dados recentes ainda podem ser revistos.

### 9. Conclusão
- A dependência temporal e a temperatura defasada explicam a maior parte do risco.
- O modelo detecta a maioria dos meses epidêmicos com validação honesta.
- O painel torna o resultado acessível ao público.

## Ao atualizar dados ou modelo
1. Execute os dois notebooks em ordem e rode os testes.
2. Atualize neste roteiro e no artigo os números das seções 3 a 6, a partir das fontes da tabela "Regra geral".
3. Confira se as conclusões das hipóteses no notebook de dados continuam valendo para os novos números.
