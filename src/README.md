# src/

Código do projeto, organizado em camadas e sem dependência do Streamlit. É usado pelos notebooks,
pelos scripts e pelo painel.

- `domain/`
  - `entities.py`: entrada (`DengueRiskInput`) e saída do modelo;
  - `validation.py`: regras de validação de cada informação; marca quais são obrigatórias e quais podem faltar;
  - `ports.py`: interfaces do preditor e do repositório analítico.
- `application/use_cases/`
  - `base_analitica.py`: montagem da base mensal (casos prováveis, população, chuva por estação próxima);
  - `features.py`: atributos do modelo (defasagens, tendência, histórico, vizinhos e estado);
  - `model_training.py`: candidatos, validação temporal, limiar e treino;
  - `build_analytics_data.py`: tabelas do painel (histórico com previsões, cenários, perfil típico e municípios);
  - `predict_risk.py`: caso de uso da previsão.
- `infrastructure/`
  - `sources/`: download das fontes, com cache em `data/raw/` (`infodengue.py`, `ibge.py`, `inmet.py`, `ana.py`, `dive.py`);
  - `pipeline.py`: etapas do pipeline e caminhos dos arquivos;
  - `ml/predictor.py`: adaptador do modelo scikit-learn;
  - `data/app_data_builder.py`: geração dos Parquet do painel;
  - `data/duckdb_repository.py`: consultas analíticas com DuckDB.
