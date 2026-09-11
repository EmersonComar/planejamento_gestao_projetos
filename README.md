# Análise e Predição de Arboviroses: O Impacto do Saneamento Básico no Brasil

Este projeto possui o objetivo de realizar um estudo analítico referente as arboviroses no Brasil. Para isso, a estratégia será realizar um estudo sobre a biologia do mosquito *Aedes aegypti* e, de acordo com suas caracteristicas biológicas (preferencia de clima, distância máxima de voo, tempo de vida, ciclo de reprodução, etc), vamos levantar hipóteses de como as condições ambientais e socioeconômicas do Brasil podem influenciar a proliferação do mosquito e, consequentemente, investigar como fatores climáticos, ambientais, demográficos e socioeconômicos estão associados à incidência de arboviroses transmitidas pelo Aedes aegypti e avaliar posteriormente a capacidade dessas variáveis de contribuir para modelos preditivos de incidência.

Vamos adotar a abordagem de Conhecimento de Domínio para guiar a coleta e análise de dados, o que significa que o conhecimento científico sobre a doença e o mosquito será fundamental para guiar as hipóteses e análises.


## Entregas - Sprint 0 (Planejamento)

Artefatos e links exigidos para a entrega da **Sprint 0**:

- **Business Model Canvas:** [Google Slides](https://docs.google.com/presentation/d/1HZ8j-pS682aF5SrYdd5c_HHmTg-nMQDT/edit?usp=sharing&ouid=117602217482546459756&rtpof=true&sd=true)
- **Backlog e Kanban:** [Trello](https://trello.com/b/MSoAuU1e/planejamentogestaoprojetos) — quadro estruturado em 5 listas (Backlog/To do/Doing/Testing/Done), com WIP limit configurado nas colulas Doing e Testing
- **Artigo científico:** [Overleaf](https://www.overleaf.com/project/6a9ee65cc6d68da88e434a98)
- **Repositório GitHub criado**

## Entregas - Sprint 1 (Conhecendo os Dados)

- **Levantamento de datasets:** múltiplas fontes públicas reais integradas.
- **Notebook de EDA:** [`notebooks/notebook_eda_dengue.ipynb`](notebooks/notebook_eda_dengue.ipynb) — pipeline completo executado de ponta a ponta para os 295 municípios de Santa Catarina (2015-2025). As 7 hipóteses de pesquisa (H1-H7) testadas com dado real; H6 (saneamento) com cobertura parcial (55 de 295 municípios, ver abaixo)
- **Backlog refinado:** quadro Trello consolidado (ver Sprint 0).
- **Artigo — Fundamentação Teórica:** ainda não iniciada

## Escopo e Estrutura de Diretórios

O projeto segue a padronização obrigatória de diretórios definida para o ciclo de desenvolvimento contínuo:

* `/app`: Código-fonte principal da aplicação web (Streamlit)
* `/data`: Dados brutos e processados extraídos de fontes governamentais
* `/docs`: Documentação técnica adicional
* `/models`: Modelos preditivos treinados e exportados
* `/notebooks`: Experimentação, análise exploratória e pipeline de pré-processamento
* `/src`: Scripts auxiliares e módulos Python
* `/tests`: Cobertura de testes unitários e de integração
* `.github/`: Configurações de automação e templates do repositório

## Configuração do Ambiente

O gerenciamento de dependências e a execução local dos scripts Python são estruturados através do gerenciador de pacotes `uv`. A arquitetura do projeto foi desenhada para operar com máxima performance em sistemas Ubuntu, facilitando a reprodução da análise de dados.

## Referências e Bases de Dados

O escopo analítico utiliza as seguintes fontes públicas para extração de variáveis demográficas, climáticas e epidemiológicas. A lista abaixo reflete o que está de fato integrado ao notebook após a Sprint 1 (as fontes originalmente cogitadas na Sprint 0 — DATASUS TabNet e Ipeadata — foram substituídas pelas abaixo por instabilidade e/ou falta de granularidade municipal):

* [InfoDengue (Fiocruz/UFMG)](https://info.dengue.mat.br/) — casos de dengue, temperatura, umidade e população por município e semana epidemiológica. Substituiu a API SINAN/DEMAS original (`apidadosabertos.saude.gov.br`), que se mostrou instável em uso real.
* [IBGE - SIDRA](https://sidra.ibge.gov.br/) — estimativas de população residente (tabela 6579) e área territorial (tabela 1301), por município.
* [INMET - Dados Históricos](https://portal.inmet.gov.br/dadoshistoricos) — precipitação horária por estação meteorológica, agregada por município.
* [ANA - Atlas Esgotos ETE 2020](https://dadosabertos.ana.gov.br/search) — remoção de DBO (qualidade do tratamento) por Estação de Tratamento de Esgoto ativa, agregada por município. Cobertura parcial: 55 dos 295 municípios de SC têm ETE ativa registrada nesse Atlas.