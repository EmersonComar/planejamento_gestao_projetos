# Mapa de risco de dengue em Santa Catarina

## Desenho aprovado

Adicionar ao Streamlit um mapa dos municípios de SC com filtros de mês e ano. Reutilizar `PredictRiskUseCase.execute_batch` e o artefato da calculadora atual para apresentar risco baixo/alto e probabilidade de risco alto. Não treinar outro modelo.

## Interface

Incluir uma seção de mapa no Painel Analítico. Disponibilizar mês por nome, ano e modo Histórico ou Cenário futuro. O histórico oferece somente os períodos presentes na base; o cenário permite escolher períodos posteriores ao último registro, até os próximos 12 meses.

Usar pontos nas coordenadas dos municípios: verde para baixo risco e vermelho para alto risco, com legenda textual. O tooltip apresenta município, período, classe e probabilidade de risco alto. No histórico, também apresenta a incidência observada por 100 mil habitantes. Uma tabela abaixo permite consultar os mesmos resultados e abrir o simulador com os parâmetros usados.

## Cálculo histórico

Para cada município no período selecionado, usar clima, densidade demográfica e mês da respectiva linha. Obter casos e incidência do mês calendário imediatamente anterior do mesmo município. Não substituir lacunas por zero nem usar uma linha de outro município. Registros com entradas ausentes ou não finitas ficam fora da inferência, com a quantidade e motivo informados na interface.

O resultado histórico é uma aplicação do modelo atual aos dados selecionados, e não uma avaliação retrospectiva com um modelo treinado exclusivamente até aquela data.

## Cenário futuro

Para cada município, calcular as médias de temperatura, umidade e precipitação do mês escolhido usando somente registros disponíveis até o último período da base. Usar a última densidade demográfica disponível e os últimos casos e incidência como referência fixa para as entradas defasadas. Usar o mês selecionado como entrada do modelo.

Identificar o resultado como cenário simulado e informar o período de referência dos casos. Para meses distantes, manter essa referência fixa explicitamente: o classificador não prevê casos para alimentar os meses seguintes. O ano identifica o cenário; não é uma variável do classificador, portanto entradas iguais produzem o mesmo resultado.

Não exibir incidência futura prevista: o modelo retorna classe de risco e probabilidade, não taxa de incidência. No tooltip futuro, rotular a incidência de referência com seu período.

## Componentes e dados

Manter preparo e validação das entradas em um caso de uso dedicado em `src/application/use_cases`, deixando renderização e widgets em `app/main.py`. Reutilizar o repositório CSV e a conversão de entradas da calculadora, evitando divergência entre mapa e simulador.

A base atual não contém latitude/longitude. Adicionar um arquivo local de coordenadas municipais com origem documentada, obtido de uma fonte pública verificável e associado pelo código IBGE. O mapa usa pontos, sem exigir polígonos municipais. Informar municípios sem coordenadas e mantê-los disponíveis na tabela quando o cálculo for válido. O carregamento normal não depende de baixar coordenadas pela rede.

## Erros e validação

Tratar períodos vazios, entradas incompletas, coordenadas ausentes e falhas do modelo com mensagens claras. Não tentar inferência em lote vazio. Validar latitude/longitude e unicidade dos códigos municipais no arquivo geográfico.

Testar isolamento das defasagens por município, lacunas entre meses, agregação climática do cenário, equivalência entre entradas do mapa e da calculadora e apresentação de filtros/resultados no Streamlit. Executar os testes existentes relevantes para verificar regressões.

## Critérios de aceite

- O mapa apresenta municípios de SC e atualiza com os filtros.
- Cores, tabela e tooltip correspondem aos resultados da calculadora para as mesmas entradas.
- Histórico e cenário futuro estão identificados e mostram a origem temporal das entradas.
- Incidência observada, incidência de referência e probabilidade de risco alto têm rótulos distintos.
- A aplicação informa dados insuficientes sem fabricar entradas ou resultados.
- As alterações existentes no notebook e arquivos não relacionados são preservadas.
