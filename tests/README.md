# tests/

Testes automatizados (`uv run python -m pytest tests/`).

- `test_sources.py`: extração da tabela dos informes da DIVE/SC, população do IBGE (Censo e interpolação) e leitura dos zips do INMET.
- `test_base_analitica.py`: estação mais próxima com medição válida, chuva ausente em vez de zero, casos prováveis e incidência mensal.
- `test_features.py`: atributos do modelo (defasagens por mês calendário sem preencher lacunas, vizinhos, estado e histórico).
- `test_build_analytics_data.py`: validação vetorizada igual à validação campo a campo, previsões do histórico, cenários com referência fixa e perfil típico.
- `test_app_data.py`: base do painel atualizada em relação à base analítica, ao modelo e à malha; previsões publicadas iguais às do modelo; consultas do repositório DuckDB.
- `test_prediction.py`: carregamento do modelo, metadados do artefato e regra do limiar.
- `test_data_metadata.py`: data de geração da base, aceita só quando o hash confere, e a célula de exportação do notebook de dados.
- `test_app.py`: páginas do painel (Streamlit `AppTest`), período da página inicial, métricas iguais às do banco, simulador igual ao modelo, navegação e funcionamento sem a base.
