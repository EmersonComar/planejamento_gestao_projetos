# app/

Código-fonte principal da aplicação web (Streamlit).

O painel informa o último mês disponível na base e que sua atualização é manual.
A célula de exportação de `notebooks/notebook_eda_dengue.ipynb` grava o CSV e
`data/processed/base_analitica_sc.metadata.json`, com a data de geração em UTC
e a identificação SHA-256 do CSV. Disponibilize os dois arquivos juntos ao
atualizar a aplicação. O painel exibe o horário de Brasília somente quando
os metadados correspondem ao CSV; caso contrário, mostra “Não registrada”.
A data de geração não representa a data de atualização das fontes externas.
