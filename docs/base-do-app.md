# Pipeline de dados e base pré-calculada do painel

O painel não recalcula dados a cada interação. Os notebooks (ou os scripts equivalentes) baixam as
fontes, montam a base analítica, treinam o modelo e transformam tudo em arquivos Parquet
versionados, consultados em tempo de execução por um DuckDB em memória (somente leitura).

```
InfoDengue, IBGE, INMET, ANA, DIVE/SC
        │  notebook_eda_dengue.ipynb  (ou scripts/update_base.py coletar + montar)
        ▼
data/processed/base_analitica_sc.csv   data/geo/   data/referencia/
        │  notebook_modelo_baseline.ipynb  (ou scripts/train_model.py treinar)
        ▼
models/modelo_risco_dengue.pkl   models/modelo_baseline_risco_dengue.pkl   models/metricas_modelo.json
        │  notebook_modelo_baseline.ipynb, seção 7  (ou scripts/build_data.py)
        ▼
data/app/*.parquet + metadados.json  ──►  DuckDbAnalyticsRepository (painel)
```

## Comandos equivalentes aos notebooks

```bash
uv run python scripts/update_base.py coletar   # baixa todas as fontes (rede, ~10 min pelo InfoDengue)
uv run python scripts/update_base.py montar    # processa o INMET, associa estações e monta a base
uv run python scripts/train_model.py avaliar   # compara os candidatos (validação temporal)
uv run python scripts/train_model.py treinar   # treina o baseline e o modelo final e grava métricas
uv run python scripts/build_data.py            # gera a base do painel
```

`tests/test_app_data.py` compara os hashes registrados em `data/app/metadados.json`
com os arquivos de origem (base analítica, modelo e malha) e falha se a base do
painel estiver desatualizada.

## Tabelas (`data/app/`)

| Arquivo | Conteúdo |
|---|---|
| `mensal.parquet` | Um registro por município × mês: casos prováveis, notificações, incidência mensal, clima, os 20 atributos do modelo, `incidencia_alta_observada` (≥ 300 casos prováveis/100 mil no mês), `entradas_validas`, `campos_pendentes`, `prob_alto` e `risco` previstos pelo modelo. |
| `cenarios.parquet` | Cenário simulado para os 3 meses seguintes ao último período: clima típico do mês, última densidade e atributos de casos do último mês observado mantidos fixos (`periodo_referencia`). O horizonte é curto porque o classificador não prevê casos. |
| `municipios.parquet` | Dimensão de municípios: população e densidade mais recentes, área, regiões do IBGE, centroide do maior polígono e os 6 vizinhos usados pelo modelo. |
| `perfil_tipico.parquet` | Valor típico (média dos anos) de cada atributo do modelo por município e mês do calendário; ponto de partida do simulador. |
| `metadados.json` | Data de geração, hashes das fontes, contagens, período e dados do modelo (atributos, limiares, importância global). |

Registros sem alguma informação obrigatória (temperatura, umidade, densidade ou casos do mês
anterior) não são classificados: `prob_alto` e `risco` ficam nulos e o motivo vai para
`campos_pendentes`. A chuva e os demais atributos podem faltar, e o modelo lida com a ausência.
Nada é preenchido com zero. As regras ficam em `src/domain/validation.py` e são as mesmas do
simulador.

## Geografia (`data/geo/`)

Malha municipal de SC em qualidade intermediária e lista de municípios com
meso/microrregião e regiões intermediária/imediata, obtidas das APIs públicas do
IBGE (Malhas v3 e Localidades v1). URLs e data de download em `data/geo/fonte.json`.
`estacoes_inmet_municipios.csv` lista as estações do INMET a até 60 km de cada município, em
ordem de distância, usadas para a chuva.

## Execução no Streamlit Community Cloud

O DuckDB roda em memória com `memory_limit=256MB` e `threads=2`, com um cursor por
consulta (seguro entre sessões). Nenhuma extensão do DuckDB é usada, então não há
download em tempo de execução. Os Parquet somam cerca de 2,5 MB.

## Interface (`app/`)

`app/main.py` define a navegação (`st.navigation`) e cada página fica em `app/app_pages/`:
Início, Mapa, Meu município, Entenda a dengue, Simulador e Sobre os dados. Só a página
aberta é executada. Módulos compartilhados em `app/ui/`: `data.py` (cache das consultas),
`charts.py` (figuras Plotly), `fmt.py` (formatação pt-BR e vocabulário) e `nav.py`
(atalhos entre páginas). O tema fica em `.streamlit/config.toml`.
