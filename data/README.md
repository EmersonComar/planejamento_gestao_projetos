# data/

Dados extraídos de fontes públicas e arquivos derivados. Tudo é baixado e gerado pelo notebook
`notebooks/notebook_eda_dengue.ipynb` (ou por `scripts/update_base.py`).

| Pasta | Conteúdo | Versionado |
|---|---|---|
| `raw/` | Downloads: série semanal do InfoDengue (`infodengue_sc.csv`), zips anuais do INMET (`<ano>.zip`) e informes da DIVE/SC em PDF (`dive/`). | Não |
| `processed/` | `base_analitica_sc.csv` (município × mês) e seus metadados. Intermediários não versionados: população e área do IBGE, saneamento da ANA, precipitação mensal por estação e coordenadas das estações. | Só a base |
| `app/` | Base pré-calculada do painel em Parquet (`mensal`, `cenarios`, `municipios`, `perfil_tipico`) e `metadados.json`, gerada pelo notebook de modelagem. | Sim |
| `geo/` | Malha municipal de SC e regiões do IBGE (origem em `fonte.json`) e as estações do INMET a até 60 km de cada município, em ordem de distância (`estacoes_inmet_municipios.csv`). | Sim |
| `referencia/` | Casos prováveis e notificações por mês extraídos dos informes epidemiológicos da DIVE/SC, com URL e data de corte de cada documento. | Sim |

## Base analítica (`processed/base_analitica_sc.csv`)

Um registro por município e mês, de jan/2015 ao último mês completo.

| Coluna | Origem | Descrição |
|---|---|---|
| `casos` | InfoDengue (`casprov`) | Casos prováveis de dengue: confirmados, suspeitos e inconclusivos. |
| `notificacoes` | InfoDengue (`casos`) | Todas as notificações, inclusive descartadas. |
| `populacao` | IBGE | Estimativa do ano (tabela 6579); Censo em 2022; 2023 interpolado. |
| `incidencia_100k` | — | Casos prováveis do mês ÷ população × 100 mil. |
| `temperatura_*`, `umidade_*` | InfoDengue | Médias mensais das semanas. |
| `precipitacao_total` | INMET | Chuva do mês na estação mais próxima que mediu ao menos 70% das horas, até 60 km. |
| `area_km2`, `densidade_demografica` | IBGE (Censo 2022) | Área e habitantes por km². |
| `qtd_ete_ativas`, `remocao_dbo_media` | ANA (Atlas Esgotos 2020) | Estações de tratamento de esgoto ativas e remoção média de DBO (fração de 0 a 1). |

Lacunas ficam ausentes; nada é preenchido com zero.
