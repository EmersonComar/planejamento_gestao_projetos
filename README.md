# Análise e Predição de Arboviroses: O Impacto do Saneamento Básico no Brasil

Este projeto investiga como fatores climáticos, ambientais, demográficos e socioeconômicos se associam à incidência de arboviroses transmitidas pelo mosquito *Aedes aegypti*. O MVP atual concentra-se na dengue em Santa Catarina: integra dados municipais, explora hipóteses orientadas por conhecimento de domínio e avalia o uso dessas variáveis em um modelo de classificação de risco.

O conhecimento científico sobre a doença e a biologia do mosquito orienta a coleta de dados e a formulação das hipóteses.

## Entregas por Sprint

### Sprint 0 — Planejamento

- **Business Model Canvas:** [Google Slides](https://docs.google.com/presentation/d/1HZ8j-pS682aF5SrYdd5c_HHmTg-nMQDT/edit?usp=sharing&ouid=117602217482546459756&rtpof=true&sd=true)
- **Backlog e Kanban:** [Trello](https://trello.com/b/MSoAuU1e/planejamentogestaoprojetos).
- **Artigo científico:** [Overleaf](https://www.overleaf.com/project/6a9ee65cc6d68da88e434a98).

### Sprint 1 — Conhecendo os Dados

- Levantamento e integração de fontes públicas de dados epidemiológicos, climáticos, demográficos e de saneamento.
- Análise exploratória e formulação de hipóteses no [notebook de EDA](notebooks/notebook_eda_dengue.ipynb).
- Backlog refinado no [Trello](https://trello.com/b/MSoAuU1e/planejamentogestaoprojetos).

### Sprint 2 — MVP Analítico

- Modelo baseline treinado e versionado em [`models/modelo_baseline_risco_dengue.pkl`](models/modelo_baseline_risco_dengue.pkl).
- Pipeline e treinamento documentados no [notebook do modelo baseline](notebooks/notebook_modelo_baseline.ipynb).

### Sprint 3 — MVP do Produto

- Aplicação web em Streamlit integrada ao modelo baseline.
- Simulador de risco com entradas climáticas, demográficas e temporais; apresenta classe de risco, probabilidade e fatores de importância global do modelo.
- Links da tabela de análise preenchem o simulador com os valores da respectiva linha.
- Testes automatizados cobrem o carregamento da aplicação, as métricas de risco e a consistência entre dados reais, tabela e simulador.

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

## Escopo e Estrutura de Diretórios

O projeto segue a padronização obrigatória de diretórios definida para o ciclo de desenvolvimento contínuo:

* `/app`: aplicação web em Streamlit
* `/data`: dados brutos e processados
* `/docs`: documentação técnica
* `/models`: modelos treinados e exportados
* `/notebooks`: análise exploratória e experimentação
* `/src`: domínio, casos de uso e infraestrutura
* `/tests`: testes automatizados
* `.github/`: automação e configurações do GitHub

## Configuração do Ambiente

O gerenciamento de dependências e a execução local são feitos com `uv`. Consulte [Executar a Aplicação](#executar-a-aplicação) para configurar o ambiente e iniciar o dashboard.

## Referências e Bases de Dados

O escopo analítico utiliza as seguintes fontes públicas para extração de variáveis demográficas, climáticas e epidemiológicas. A lista abaixo reflete o que está de fato integrado ao notebook após a Sprint 1 (as fontes originalmente cogitadas na Sprint 0 — DATASUS TabNet e Ipeadata — foram substituídas pelas abaixo por instabilidade e/ou falta de granularidade municipal):

* [InfoDengue (Fiocruz/UFMG)](https://info.dengue.mat.br/) — casos de dengue, temperatura, umidade e população por município e semana epidemiológica. Substituiu a API SINAN/DEMAS original (`apidadosabertos.saude.gov.br`), que se mostrou instável em uso real.
* [IBGE - SIDRA](https://sidra.ibge.gov.br/) — estimativas de população residente (tabela 6579) e área territorial (tabela 1301), por município.
* [INMET - Dados Históricos](https://portal.inmet.gov.br/dadoshistoricos) — precipitação horária por estação meteorológica, agregada por município.
* [ANA - Atlas Esgotos ETE 2020](https://dadosabertos.ana.gov.br/search) — remoção de DBO (qualidade do tratamento) por Estação de Tratamento de Esgoto ativa, agregada por município. Cobertura parcial: 55 dos 295 municípios de SC têm ETE ativa registrada nesse Atlas.