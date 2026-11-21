# notebooks/

Pipeline completo do projeto, executado em ordem:

1. `notebook_eda_dengue.ipynb` — **Sprint 1, conhecendo os dados.** Baixa todas as fontes (InfoDengue, IBGE, INMET, ANA e informes da DIVE/SC), monta a base analítica mensal por município (`data/processed/base_analitica_sc.csv`), confere os totais com os informes oficiais e analisa as hipóteses H1–H7.
2. `notebook_modelo_baseline.ipynb` — **Sprint 2, modelagem.** Define o alvo e os atributos, compara modelos com validação temporal, treina o baseline e o modelo final (`models/`) e gera a base pré-calculada do painel (`data/app/`).

Os notebooks funcionam localmente, com o kernel do projeto (`uv sync`), ou no Google Colab, onde a
primeira célula clona o repositório e instala as dependências. Os downloads ficam em `data/raw/` e
são reaproveitados; as flags da seção 0 do notebook de dados forçam um novo download quando houver
meses novos.

O código chamado pelos notebooks fica em `src/` e também pode ser executado pelos scripts de
`scripts/`, com os mesmos resultados.
