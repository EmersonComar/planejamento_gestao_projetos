# Análise e Predição de Arboviroses: O Impacto do Saneamento Básico no Brasil

Este projeto investiga como fatores climáticos, ambientais, demográficos e socioeconômicos se associam à incidência de arboviroses transmitidas pelo mosquito *Aedes aegypti*. O MVP concentra-se na dengue em Santa Catarina: integra dados municipais, explora hipóteses orientadas por conhecimento de domínio e avalia o uso dessas variáveis em um modelo de classificação de risco, apresentado em um painel web para o público leigo.

O conhecimento científico sobre a doença e a biologia do mosquito orienta a coleta de dados e a formulação das hipóteses.

## Como navegar este projeto

O projeto tem quatro componentes, cada um para um público. Todos partem deste repositório:

| Componente | Para que serve | Para quem | Onde |
|---|---|---|---|
| **Painel** | Mostrar a situação da dengue e o risco por município, em linguagem simples | Cidadãos, gestores municipais, imprensa | [dengue-sc.streamlit.app](https://dengue-sc.streamlit.app/) |
| **Artigo** | Registrar a pesquisa: problema, métodos, resultados e limitações | Banca, professores, comunidade científica | Em elaboração ([roteiro](docs/roteiro-artigo.md)) |
| **Notebooks** | Mostrar e reproduzir a análise, das fontes ao modelo | Avaliadores técnicos e quem quer refazer os resultados | [Dados e análise exploratória](notebooks/notebook_eda_dengue.ipynb) e [modelagem](notebooks/notebook_modelo_baseline.ipynb) |
| **Repositório** | Guardar código, dados, modelo, testes e documentação; publica o painel | Desenvolvedores e mantenedores | Este README, [`docs/`](docs/README.md) e as pastas abaixo |

```
Fontes públicas ─► Notebook de dados ─► base analítica ─► Notebook de modelagem ─► modelo + base do painel
                                                                                          │
                                         repositório (versiona tudo) ─► Streamlit Cloud ─► Painel
                                         notebooks e métricas ───────────────────────────► Artigo
```

**Por onde começar**
- **Quer saber como está a dengue na sua cidade?** Abra o [painel](https://dengue-sc.streamlit.app/). A página "Sobre os dados" explica as fontes e os limites.
- **Está avaliando a pesquisa?** Leia as [entregas por sprint](#entregas-por-sprint) e os dois notebooks, que trazem cada etapa com gráficos e conclusões. Os métodos estão resumidos em [`docs/modelo-e-validacao.md`](docs/modelo-e-validacao.md).
- **Vai manter ou atualizar o projeto?** Siga [Executar a Aplicação](#executar-a-aplicação) e [Atualizar Dados e Modelo](#atualizar-dados-e-modelo), e a arquitetura em [`docs/base-do-app.md`](docs/base-do-app.md).

Os números têm uma única origem: totais de casos vêm da base analítica e métricas do modelo vêm de [`models/metricas_modelo.json`](models/metricas_modelo.json). O painel e o artigo apenas os reproduzem.

## Entregas por Sprint

### Sprint 0 — Planejamento

- **Business Model Canvas:** [Google Slides](https://docs.google.com/presentation/d/1HZ8j-pS682aF5SrYdd5c_HHmTg-nMQDT/edit?usp=sharing&ouid=117602217482546459756&rtpof=true&sd=true)
- **Backlog e Kanban:** [Trello](https://trello.com/b/MSoAuU1e/planejamentogestaoprojetos).
- **Artigo científico:** [Overleaf](https://www.overleaf.com/project/6a9ee65cc6d68da88e434a98).

### Sprint 1 — Conhecendo os Dados

- Coleta automatizada de todas as fontes públicas (InfoDengue, IBGE, INMET, ANA e informes da DIVE/SC) e montagem da base analítica mensal por município, de jan/2015 ao último mês completo, no [notebook de dados](notebooks/notebook_eda_dengue.ipynb).
- **Caso** é o *caso provável* de dengue (confirmados, suspeitos e inconclusivos, sem os descartados), conceito da Diretoria de Vigilância Epidemiológica de SC. A incidência é a do mês, com a população do IBGE de cada ano.
- A DIVE/SC é a referência oficial para os totais estaduais publicados; o painel usa InfoDengue para análises municipais e para o modelo. As séries não são intercambiáveis: os casos prováveis do painel diferem dos totais DIVE em 8% (2024), 13% (2025) e 18% (2026) nos períodos comparáveis ([detalhes](docs/modelo-e-validacao.md)).
- Análise exploratória das hipóteses H1–H7. Confirmadas: sazonalidade, temperatura (mais forte com um mês de defasagem), densidade e dependência temporal. Sem relação clara: chuva e saneamento.
- Backlog refinado no [Trello](https://trello.com/b/MSoAuU1e/planejamentogestaoprojetos).

### Sprint 2 — MVP Analítico

- Modelos treinados e avaliados no [notebook de modelagem](notebooks/notebook_modelo_baseline.ipynb), com validação temporal: cada ano é testado com um modelo treinado só com os anos anteriores.
- **Baseline:** Random Forest com 7 informações ([`models/modelo_baseline_risco_dengue.pkl`](models/modelo_baseline_risco_dengue.pkl)).
- **Modelo final:** Random Forest + Gradient Boosting com 20 informações, entre elas casos nos municípios vizinhos e no estado e temperatura do mês anterior ([`models/modelo_risco_dengue.pkl`](models/README.md)). Média de 2023 a 2026:
  - PR-AUC de 0,740, contra 0,698 do baseline;
  - 84% dos meses epidêmicos detectados, contra 82%;
  - 37% dos alertas confirmados, contra 32%.

### Sprint 3 — MVP do Produto

- **Painel web em Streamlit para o público leigo** ([`app/`](app/README.md)), com seis páginas:
  - Início, com período de análise selecionável;
  - Mapa, coroplético e clicável, com os 295 municípios;
  - Meu município;
  - Entenda a dengue;
  - Simulador "e se?", que parte dos valores típicos de cada município;
  - Sobre os dados, com fontes, conferência oficial e desempenho do modelo.
- Consultas pré-calculadas em Parquet e DuckDB: cada página abre em menos de 1 s.
- Testes automatizados da coleta e montagem da base, dos atributos e do modelo, da base do painel e das páginas.

### Publicação no Streamlit Community Cloud

- **Aplicação publicada:** [MVP Dengue SC](https://dengue-sc.streamlit.app/).

A aplicação é publicada a partir deste repositório, branch `main`, com entrada em `app/main.py`. Em **Advanced settings**, selecione **Python 3.13**. As dependências de execução estão em [`app/requirements.txt`](app/requirements.txt), com `scikit-learn==1.6.1` fixado para carregar o modelo, e o tema em [`.streamlit/config.toml`](.streamlit/config.toml).

O painel só lê arquivos versionados (`data/app/`, `data/geo/`, `data/referencia/` e `models/`); nada é baixado ou recalculado em tempo de execução, exceto o simulador. O ambiente local de desenvolvimento usa Python 3.14 ou superior.

## Executar a Aplicação

É necessário ter Python 3.14 ou superior e o [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado. No terminal, a partir da raiz do repositório:

```bash
uv sync
uv run -m streamlit run app/main.py
```

O Streamlit abrirá a aplicação no navegador, normalmente em <http://localhost:8501>. Para encerrar o servidor, pressione `Ctrl+C` no terminal.

Para executar os testes automatizados:

```bash
uv run python -m pytest tests/
```

## Atualizar Dados e Modelo

A atualização é manual e segue a ordem dos notebooks:

1. [`notebooks/notebook_eda_dengue.ipynb`](notebooks/notebook_eda_dengue.ipynb): baixa todas as fontes, monta a base analítica, confere com a DIVE/SC e executa a análise exploratória. Para trazer meses novos, marque `ATUALIZAR_INFODENGUE = True` e `ATUALIZAR_INMET_ANO_CORRENTE = True`; para incluir um informe novo da DIVE, acrescente-o em `src/infrastructure/sources/dive.py`.
2. [`notebooks/notebook_modelo_baseline.ipynb`](notebooks/notebook_modelo_baseline.ipynb): avalia os candidatos, treina o baseline e o modelo final e gera a base pré-calculada do painel.
3. `uv run python -m pytest tests/` confere a consistência entre base, modelo e painel.

Os notebooks funcionam localmente (kernel do projeto) ou no Google Colab, onde a primeira célula clona o repositório e instala as dependências. O mesmo pipeline pode ser executado pela linha de comando:

```bash
uv run python scripts/update_base.py coletar   # baixa as fontes (rede; ~10 min)
uv run python scripts/update_base.py montar    # monta a base analítica
uv run python scripts/train_model.py treinar   # treina e grava os modelos e as métricas
uv run python scripts/build_data.py            # gera a base pré-calculada do painel
```

Detalhes em [`docs/base-do-app.md`](docs/base-do-app.md).

## Escopo e Estrutura de Diretórios

O projeto segue a padronização obrigatória de diretórios definida para o ciclo de desenvolvimento contínuo:

* `/app`: aplicação web em Streamlit
* `/data`: dados brutos, processados, base do painel, geografia e referências oficiais
* `/docs`: documentação técnica
* `/models`: modelos treinados e métricas de avaliação
* `/notebooks`: coleta, análise exploratória e modelagem
* `/scripts`: execução do pipeline pela linha de comando
* `/src`: domínio, casos de uso, fontes de dados e infraestrutura
* `/tests`: testes automatizados
* `.github/`: automação e configurações do GitHub

## Configuração do Ambiente

O gerenciamento de dependências e a execução local são feitos com `uv`. Consulte [Executar a Aplicação](#executar-a-aplicação) para configurar o ambiente e iniciar o painel.

## Referências e Bases de Dados

O escopo analítico utiliza as seguintes fontes públicas, todas baixadas pelo [notebook de dados](notebooks/notebook_eda_dengue.ipynb). As fontes originalmente cogitadas na Sprint 0 — DATASUS TabNet e Ipeadata — foram substituídas por instabilidade e/ou falta de granularidade municipal:

* [InfoDengue (Fiocruz)](https://info.dengue.mat.br/) — fonte dos casos prováveis, notificações, temperatura e umidade por município e semana epidemiológica usados nas análises municipais e no modelo. Substituiu a API SINAN/DEMAS original (`apidadosabertos.saude.gov.br`), que se mostrou instável em uso real.
* [IBGE - SIDRA](https://sidra.ibge.gov.br/) — população residente por município: estimativas anuais (tabela 6579) e Censo 2022 (tabela 4714), além da área territorial do Censo 2022. [APIs de Malhas e Localidades](https://servicodados.ibge.gov.br/api/docs/) — mapa dos municípios e regiões.
* [INMET - Dados Históricos](https://portal.inmet.gov.br/dadoshistoricos) — precipitação horária das estações automáticas. Cada município usa a estação mais próxima que mediu o mês, até 60 km.
* [ANA - Atlas Esgotos ETE 2020](https://dadosabertos.ana.gov.br/search) — remoção de DBO (qualidade do tratamento) por Estação de Tratamento de Esgoto ativa, agregada por município. Cobertura parcial: 55 dos 295 municípios de SC têm ETE ativa registrada nesse Atlas.
* [DIVE/SC — Dengue](https://dive.saude.sc.gov.br/index.php/doencas-e-agravos/dengue) — fonte oficial dos totais estaduais publicados; os informes também são mantidos como referência separada para comparação ([`data/referencia/`](data/README.md)).
