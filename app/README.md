# app/

Painel web em Streamlit voltado ao público leigo. Entrada: `app/main.py` (local e no Streamlit Community Cloud).

## Estrutura

- `main.py`: configuração da página e navegação (`st.navigation`, menu no topo). Só a página aberta é executada.
- `app_pages/`: uma página por arquivo.
  - `inicio.py`: indicadores do período escolhido (casos, incidência, municípios em nível epidêmico e mês de pico), mapa e ranking dos municípios no período e prevenção.
  - `mapa.py`: mapa coroplético por mês (risco previsto, casos por 100 mil ou número de casos), cenário dos próximos meses e resumo do município clicado.
  - `municipio.py`: histórico, comparação com o estado, sazonalidade e clima de um município (`?municipio=Nome`).
  - `fatores.py`: explicações sobre época do ano, clima, tendência, regiões e o que o modelo considera.
  - `simulador.py`: simulador "e se?". O modo simples parte dos valores típicos do município; o avançado permite editar as 20 informações do modelo.
  - `sobre.py`: papéis das fontes, definição de caso provável, comparação do InfoDengue com os totais estaduais oficiais da DIVE/SC, desempenho do modelo e limitações.
- `ui/`: código compartilhado.
  - `data.py`: acesso aos dados com cache;
  - `charts.py`: figuras Plotly em pt-BR;
  - `components.py`: componentes reutilizados entre páginas;
  - `fmt.py`: formatação e vocabulário para leigos;
  - `nav.py`: atalhos entre páginas.

## Dados

O painel não lê o CSV da base nem recalcula indicadores: consulta, via DuckDB em memória, os arquivos
pré-calculados em `data/app/` (gerados por `scripts/build_data.py`). O modelo
(`models/modelo_risco_dengue.pkl`) só é executado no simulador. "Casos" são **casos prováveis**
(confirmados, suspeitos e inconclusivos) e a incidência é a do mês. Ver `docs/base-do-app.md` e
`docs/modelo-e-validacao.md`.

A atualização é manual: novos meses aparecem depois de rodar os scripts de `scripts/` e publicar os
arquivos gerados. A página "Sobre os dados" mostra o período coberto e a data de geração.
