# Análise e Predição de Arboviroses: O Impacto do Saneamento Básico no Brasil

Este projeto possui o objetivo de realizar um estudo analítico referente as arboviroses no Brasil. Para isso, a estratégia será realizar um estudo sobre a biologia do mosquito *Aedes aegypti* e, de acordo com suas caracteristicas biológicas (preferencia de clima, distância máxima de voo, tempo de vida, ciclo de reprodução, etc), vamos levantar hipóteses de como as condições ambientais e socioeconômicas do Brasil podem influenciar a proliferação do mosquito e, consequentemente, investigar como fatores climáticos, ambientais, demográficos e socioeconômicos estão associados à incidência de arboviroses transmitidas pelo Aedes aegypti e avaliar posteriormente a capacidade dessas variáveis de contribuir para modelos preditivos de incidência.

Vamos adotar a abordagem de Conhecimento de Domínio para guiar a coleta e análise de dados, o que significa que o conhecimento científico sobre a doença e o mosquito será fundamental para guiar as hipóteses e análises.


## Entregas - Sprint 0 (Planejamento)

Artefatos e links exigidos para a entrega da **Sprint 0**:

* **Business Model Canvas:** [Google Drive](https://docs.google.com/presentation/d/1HZ8j-pS682aF5SrYdd5c_HHmTg-nMQDT/edit?usp=sharing&ouid=117602217482546459756&rtpof=true&sd=true)
* **Backlog e Kanban:** [Trello](https://trello.com/invite/b/6a81b15d7f2522018a2e3036/ATTI2dee072f623d7f4b682fe7fdc171889c398FA237/planejamentogestaoprojetos)
* **Artigo científico:** [Google Drive](https://docs.google.com/document/d/18nw0vBVnCc_96Eqpvj3kVELwDdO7K6Er8t0rc9T7D2g/edit?usp=sharing)

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

O escopo analítico utiliza as seguintes fontes públicas para extração de variáveis demográficas, climáticas e epidemiológicas:

* [IBGE - SIDRA (Sistema de Recuperação Automática)](https://sidra.ibge.gov.br/)
* [DATASUS - TabNet (Casos de Dengue e Chikungunya no SINAN)](https://datasus.saude.gov.br/informacoes-de-saude-tabnet/)
* [INMET - Instituto Nacional de Meteorologia (Dados Históricos)](https://portal.inmet.gov.br/dadoshistoricos)
* [Ipeadata - Indicadores Socioeconômicos Regionais](http://www.ipeadata.gov.br/Default.aspx)