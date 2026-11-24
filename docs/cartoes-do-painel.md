# Cartões do painel

Referência de todos os cartões de indicadores do painel: o que cada um mostra, como o valor é
calculado, a que período se refere e para que serve. Use este documento ao alterar um cartão, ao
explicar o painel a alguém ou ao citar um número do painel no artigo.

## Convenções

- **Caso** é sempre o *caso provável* de dengue: confirmados, suspeitos e inconclusivos, sem os descartados.
- **Nível epidêmico:** 300 casos prováveis ou mais **para cada 100 mil habitantes num mesmo mês**. Não é 300 casos. Num município de 10 mil habitantes, 30 casos num mês bastam.
- **Pontuação de risco:** a probabilidade (de 0% a 100%) que o modelo atribui a um mês epidêmico. A partir do **limiar de decisão** (hoje 24%, em `models/metricas_modelo.json`), o mês é classificado como **risco alto**.
- **Variação (seta abaixo do número):** compara com o período anterior indicado no próprio cartão. As cores são invertidas, porque mais casos é pior: **verde** significa queda e **vermelho**, aumento. Sem período anterior para comparar, a variação não aparece.
- **Ícone (?)** ao lado do título: abre a explicação do cartão para o usuário.
- O código de cada página fica em `app/app_pages/`. Os dados vêm de `data/app/`, consultados por `app/ui/data.py`.

## Início (`inicio.py`)

Todos os cartões seguem o **período analisado** escolhido no topo da página (padrão: últimos 12
meses). A comparação é com **os mesmos meses do ano anterior** (ex.: jan–out/26 contra jan–out/25),
para não misturar épocas diferentes do ano, já que a dengue é sazonal. Em períodos de mais de 12
meses, o recuo é em anos inteiros. Em "Toda a série" não há comparação.

| Cartão | O que mostra | Como é calculado | Objetivo |
|---|---|---|---|
| **Casos no período** | Total de casos no estado, com barras por mês (ou por ano, em períodos de mais de 24 meses) | Soma dos casos de todos os municípios nos meses do período | Dar a dimensão do problema e mostrar a evolução dentro do período |
| **Casos por 100 mil habitantes** | Incidência acumulada do estado | Casos do período × 100 mil ÷ população média do estado no período | Comparar períodos de forma justa, descontando o crescimento da população |
| **Municípios em nível epidêmico** | Quantos municípios chegaram ao nível epidêmico; o botão **Ver municípios** abre a lista | Municípios com pelo menos um mês de incidência ≥ 300 por 100 mil no período. A lista traz: meses em nível epidêmico, **pico** (maior incidência mensal, que é o valor comparado com 300) e total de casos. Ordena por meses e, no empate, pelo pico | Mostrar o quanto a epidemia se espalhou pelo território e quais municípios foram atingidos |
| **Mês com mais casos** | Mês de pico no estado e o número de casos naquele mês | Mês com a maior soma de casos dentro do período | Localizar o momento mais grave do período |

## Mapa (`mapa.py`)

Os cartões se referem ao **mês escolhido** no controle da página.

| Cartão | Aparece em | Como é calculado | Objetivo |
|---|---|---|---|
| **Casos em ⟨mês⟩** | Meses passados | Soma dos casos de todos os municípios no mês | Situar o mês no contexto do estado |
| **Municípios em nível epidêmico** | Meses passados | Municípios com incidência ≥ 300 por 100 mil naquele mês | Mostrar quantos municípios estavam de fato em epidemia |
| **Municípios com risco alto previsto** | Meses passados e próximos meses | Municípios com pontuação ≥ limiar de decisão | Mostrar onde o modelo aponta risco. Nos meses passados, permite comparar com o cartão anterior |
| **Sem dados suficientes para prever** | Meses passados e próximos meses | Municípios sem alguma informação obrigatória para o modelo (temperatura, umidade, densidade ou casos do mês anterior) | Explicar os municípios em cinza no mapa e deixar claro que nenhum valor foi inventado |

**Cartão do município selecionado** (à direita do mapa, ao clicar num município):

| Elemento | O que mostra | Objetivo |
|---|---|---|
| Selo de risco | "Risco alto", "Risco baixo" ou "Sem dados suficientes" | Leitura imediata da classificação |
| **Casos no mês** | Casos do município no mês (meses passados) | Número absoluto, fácil de entender |
| **Por 100 mil habitantes** | Incidência do município no mês (meses passados) | Valor que é comparado com o limiar epidêmico |
| **Casos em ⟨mês⟩ (referência)** | Casos do último mês com dados (próximos meses) | Mostrar em que situação real o cenário se baseia |
| **Pontuação de risco do modelo** | Pontuação do município no mês | Mostrar o quão perto ou longe está do limiar |

Também fazem parte da página:
- **Frase de concordância (meses passados):** em quantos % dos municípios com dados completos a previsão coincidiu com o que aconteceu (passar ou não de 300 por 100 mil).
- **Aviso de simulação (próximos meses):** explica que o cenário usa o clima típico do mês e os casos do último mês com dados, e que o modelo não prevê o número de casos.

## Meu município (`municipio.py`)

Os cartões usam **períodos fixos** relativos ao último mês com dados. Esta página não tem
seletor de período.

| Cartão | O que mostra | Como é calculado | Objetivo |
|---|---|---|---|
| Selos de identificação | Mesorregião, região imediata e população | Dados do IBGE | Situar o município no estado |
| **Casos em ⟨último mês⟩** | Casos do último mês com dados, com barras dos últimos 12 meses (a mais escura é o mês do cartão) | Casos do mês; variação contra o mês anterior | Mostrar a situação mais recente e a tendência do último ano |
| **Casos nos últimos 12 meses** | Total dos 12 meses mais recentes | Soma dos casos; variação contra os 12 meses anteriores | Comparar o último ano com o anterior |
| **Maior surto** | Mês com mais casos desde 2015 (o número de casos aparece na ajuda) | Mês com o maior número de casos na série do município | Dar a referência do pior momento já vivido |
| **Meses em nível epidêmico** | Quantos meses o município passou de 300 por 100 mil desde 2015 | Contagem dos meses com incidência ≥ 300 por 100 mil; a ajuda traduz o limiar em número de casos para a população do município | Mostrar com que frequência o município enfrenta epidemias |
| **Cenário para ⟨próximo mês⟩** (faixa colorida) | Risco alto (vermelho), risco baixo (verde) ou falta de dados (azul) | Classificação do modelo no cenário simulado do próximo mês | Antecipar o risco, com a ressalva de que é uma simulação |

## Simulador (`simulador.py`)

| Cartão | O que mostra | Como é calculado | Objetivo |
|---|---|---|---|
| **Medidor de pontuação** | Pontuação de 0% a 100%, com traço preto no limiar de decisão | Modelo aplicado aos valores escolhidos; as informações não editadas ficam nos valores típicos do município e do mês | Mostrar visualmente o quão perto do risco alto está a situação simulada |
| **Risco alto / Risco baixo** (faixa colorida) | Classificação e o número de casos que equivale ao nível epidêmico para a população do município | Pontuação comparada ao limiar; casos = 300 × população ÷ 100 mil | Traduzir a pontuação numa frase e num número de casos que o leigo entende |
| **Com os valores típicos, a pontuação seria** | Pontuação com os valores típicos e a diferença, em pontos, para a simulação | Mesmo modelo, sem as alterações do usuário | Mostrar o efeito das mudanças feitas nos controles |

O gráfico **"O que mais muda o resultado?"** completa o simulador. Ele mostra como a pontuação
varia com um único fator, mantendo os demais, e informa a partir de que valor o risco passa a ser
alto.

## Sobre os dados (`sobre.py`)

| Cartão | O que mostra | Como é calculado | Objetivo |
|---|---|---|---|
| **Meses epidêmicos detectados** | Recall médio do modelo | Média, nos anos de teste (2023–2026), da fração de meses epidêmicos que o modelo apontou, em validação temporal | Dizer, em linguagem simples, quantas epidemias o modelo não deixa passar |
| **Alertas que se confirmaram** | Precisão média do modelo | Média da fração de alertas de risco alto que viraram meses epidêmicos | Dizer quanto dos alertas são falsos alarmes |
| **Qualidade geral (PR-AUC)** | PR-AUC média e o ganho percentual sobre o modelo baseline | Média da PR-AUC nos anos de teste; variação relativa ao baseline (Random Forest com 7 informações), avaliado do mesmo jeito | Resumir a qualidade do modelo e mostrar o ganho das informações adicionais |
| **Registros (município × mês)** | Tamanho da base | Número de linhas da base mensal | Dar a escala dos dados |
| **Com dados completos para o modelo** | Percentual de registros com previsão | Registros com todas as informações obrigatórias ÷ total | Mostrar a cobertura da previsão |
| **Municípios no mapa** | Municípios com geometria em relação ao total | Municípios com polígono na malha do IBGE | Confirmar que todo o estado aparece no mapa |

## Ao alterar um cartão

1. Mantenha o título curto. A explicação completa vai no `help` (ícone ?).
2. Se o cartão segue um período, deixe o período visível no título, na variação ou na ajuda.
3. Atualize este documento e, se o número for citado, o `docs/roteiro-artigo.md`.
4. Rode `uv run python -m pytest tests/test_app.py`: vários testes conferem os valores dos cartões contra o banco.
