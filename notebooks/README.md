# notebooks/

Pipeline completo do projeto, executado em ordem:

1. `notebook_eda_dengue.ipynb` — **Sprint 1, conhecendo os dados.** Baixa InfoDengue, IBGE, INMET e ANA para montar a base analítica municipal (`data/processed/base_analitica_sc.csv`). Baixa os informes da DIVE/SC separadamente como referência oficial estadual e compara as séries, sem usar os totais estaduais no modelo. Também analisa as hipóteses H1–H7.
2. `notebook_modelo_baseline.ipynb` — **Sprint 2, modelagem.** Define o alvo e os atributos, compara modelos com validação temporal, treina o baseline e o modelo final (`models/`) e gera a base pré-calculada do painel (`data/app/`).

Os notebooks funcionam localmente, com o kernel do projeto (`uv sync`), ou no Google Colab, onde a
primeira célula clona o repositório e instala as dependências. Os downloads ficam em `data/raw/` e
são reaproveitados. Para atualizar a série municipal, use `ATUALIZAR_INFODENGUE=True`; para baixar
novamente os PDFs de referência, use `ATUALIZAR_INFORMES_DIVE=True`. Quando um novo informe for
publicado, acrescente-o à lista `BULLETINS` em `src/infrastructure/sources/dive.py`.

O código chamado pelos notebooks fica em `src/` e também pode ser executado pelos scripts de
`scripts/`, com os mesmos resultados.
