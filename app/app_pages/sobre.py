import pandas as pd
import streamlit as st

from app.ui import charts, data, fmt, links

meta = data.metadata()
model = meta["modelo"]
metrics = model.get("metricas") or {}
threshold = model["limiar_incidencia_alta"]
missing = data.missing_inputs().iloc[0]

st.title("Sobre os dados", icon=":material/menu_book:")
st.markdown("De onde vêm as informações, como o risco é calculado e até onde é possível confiar nos resultados.")

with st.container(border=True):
    st.subheader("Sobre o projeto", icon=":material/school:")
    st.markdown(
        "Este painel é o produto de uma pesquisa acadêmica que investiga como clima, população e saneamento "
        "se relacionam com a dengue nos municípios de Santa Catarina. Tudo o que aparece aqui pode ser conferido "
        "e refeito a partir dos materiais abaixo."
    )
    with st.container(horizontal=True):
        st.link_button("Código, dados e documentação", links.REPO_URL, icon=":material/code:")
        st.link_button("Notebook: dados e análise exploratória", links.NOTEBOOK_DATA_URL, icon=":material/query_stats:")
        st.link_button("Notebook: modelo de risco", links.NOTEBOOK_MODEL_URL, icon=":material/psychology:")
        if links.ARTICLE_URL:
            st.link_button("Artigo científico", links.ARTICLE_URL, icon=":material/article:")
    if not links.ARTICLE_URL:
        st.caption(":material/article: O artigo científico com os métodos e resultados está em elaboração.")

with st.container(border=True):
    st.subheader("De onde vêm os dados", icon=":material/database:")
    st.table(pd.DataFrame([
        ("InfoDengue (Fiocruz)",
         "Série municipal de casos e notificações, temperatura e umidade; usada nas análises municipais e no modelo",
         "https://info.dengue.mat.br/"),
        ("IBGE", "População de cada ano, área (Censo 2022), regiões e mapa dos municípios", "https://www.ibge.gov.br/"),
        ("INMET", "Chuva medida na estação meteorológica mais próxima de cada município",
         "https://portal.inmet.gov.br/dadoshistoricos"),
        ("ANA — Atlas Esgotos", "Tratamento de esgoto (usado só na análise exploratória)",
         "https://dadosabertos.ana.gov.br/"),
        ("DIVE/SC",
         "Fonte oficial dos totais estaduais publicados; referência para comparação, separada da série municipal usada no modelo",
         "https://dive.saude.sc.gov.br/index.php/doencas-e-agravos/dengue"),
    ], columns=["Fonte", "O que fornece", "Endereço"]).set_index("Fonte"))
    generated = pd.Timestamp(meta["gerado_em"]).tz_convert("America/Sao_Paulo")
    st.markdown(
        "**O que contamos como caso:** *casos prováveis* — confirmados, suspeitos e inconclusivos, sem os "
        "descartados. É o mesmo conceito que a Secretaria de Estado da Saúde usa desde 2024. "
        "**Casos por 100 mil habitantes** são os casos prováveis do mês divididos pela população."
    )
    st.caption(
        f"Período: {fmt.month_year(meta['periodo_inicio'] + '-01')} a {fmt.month_year(meta['periodo_fim'] + '-01')}. "
        f"Painel atualizado em {generated:%d/%m/%Y}. Os meses mais recentes ainda podem mudar: as fichas de "
        "notificação continuam sendo encerradas pelos municípios."
    )

with st.container(border=True):
    st.subheader("Comparação com os totais estaduais oficiais da DIVE/SC", icon=":material/fact_check:")
    comparison = data.official_comparison()
    st.markdown(
        "A DIVE/SC é a referência oficial para os totais estaduais publicados. Os valores do painel vêm da série "
        "InfoDengue agregada a partir dos municípios e são usados para as análises municipais e o modelo; não são "
        "ajustados para coincidir com os boletins. As diferenças também refletem que o painel conta os casos pela "
        "**semana epidemiológica do InfoDengue**, e a DIVE agrupa os registros do SINAN pelo **mês em que os "
        "sintomas começaram**. As fontes têm datas de corte diferentes, o InfoDengue é revisado retrospectivamente "
        "e casos suspeitos podem ser reclassificados."
    )
    table = comparison.assign(
        periodo=comparison.apply(lambda r: f"{r['ano']} (jan a {fmt.MONTHS_SHORT[int(r['meses']) - 1]})", axis=1),
        casos_dif=comparison["diferenca_casos"].map(lambda v: f"{'+' if v >= 0 else ''}{fmt.pct(v)}"),
        notif_dif=comparison["diferenca_notificacoes"].map(lambda v: f"{'+' if v >= 0 else ''}{fmt.pct(v)}"),
    )
    st.dataframe(
        table[["periodo", "casos_dive", "casos_painel", "casos_dif", "notificacoes_dive", "notificacoes_painel",
               "notif_dif", "documento"]],
        hide_index=True,
        column_config={
            "periodo": "Período",
            "casos_dive": st.column_config.NumberColumn("Casos prováveis (DIVE)", format="localized"),
            "casos_painel": st.column_config.NumberColumn("Casos prováveis (painel)", format="localized"),
            "casos_dif": "Diferença",
            "notificacoes_dive": st.column_config.NumberColumn("Notificações (DIVE)", format="localized"),
            "notificacoes_painel": st.column_config.NumberColumn("Notificações (painel)", format="localized"),
            "notif_dif": "Diferença ",
            "documento": "Boletim consultado",
        },
        alt="Comparação entre os totais do painel e os boletins da DIVE/SC",
    )
    st.caption(
        "O mês mais recente de cada informe fica de fora por cautela, "
        "para evitar comparar períodos possivelmente parciais."
    )

with st.container(border=True):
    st.subheader("Como o risco é calculado", icon=":material/psychology:")
    st.markdown(f"""
1. **O que é risco alto.** Um mês é considerado epidêmico quando o município tem **{fmt.num(threshold)} casos
   prováveis ou mais para cada 100 mil habitantes** naquele mês.
2. **O modelo.** Uma combinação de dois modelos de aprendizado de máquina (*{model['nome']}*) aprendeu, com os
   anos anteriores, que situações costumam vir antes de meses epidêmicos: casos recentes no município, nos
   vizinhos e no estado, temperatura, chuva, época do ano e tamanho da população.
3. **A pontuação.** Para cada município e mês, o modelo dá uma pontuação de 0% a 100%. A partir de
   **{fmt.pct(model['limiar_decisao'])}**, a previsão é de risco alto. Esse ponto de corte foi escolhido para que
   o modelo não deixe passar a maioria dos meses epidêmicos, mesmo que isso gere alguns alarmes a mais.
4. **Meses passados.** No mapa, a previsão é aplicada aos dados de cada mês e pode ser comparada com o que de fato
   aconteceu.
5. **Próximos meses.** Como ainda não há dados, usamos o clima típico de cada mês e os casos do último mês
   disponível. É uma simulação, não uma previsão do número de casos.
""")

if metrics:
    with st.container(border=True):
        st.subheader("Quanto o modelo acerta", icon=":material/target:")
        by_year = pd.DataFrame(metrics["avaliacao_por_ano"])
        average = metrics["media"]
        st.markdown(
            "Testamos o modelo como se estivéssemos no passado: para avaliar cada ano, ele foi treinado **só com os "
            "anos anteriores**, sem ver o ano testado. Em média, nos anos de "
            f"{by_year['ano_teste'].min()} a {by_year['ano_teste'].max()}:"
        )
        with st.container(horizontal=True):
            st.metric("Meses epidêmicos detectados", fmt.pct(average["recall"]), border=True,
                      help="De cada 100 meses em que um município chegou ao nível epidêmico, quantos o modelo apontou.")
            st.metric("Alertas que se confirmaram", fmt.pct(average["precisao"]), border=True,
                      help="De cada 100 alertas de risco alto, quantos viraram de fato meses epidêmicos.")
            previous = metrics.get("comparacao_baseline")
            if previous:
                st.metric("Qualidade geral (PR-AUC)", fmt.num(average["pr_auc"], 2),
                          f"+{fmt.pct(average['pr_auc'] / previous['pr_auc'] - 1)}", border=True,
                          delta_description="em relação ao modelo baseline",
                          help="Mede, de 0 a 1, o quanto o modelo coloca os meses epidêmicos no topo da lista de risco. "
                               "Comparação com o modelo baseline (Random Forest com as 7 informações básicas), avaliado do mesmo jeito.")
        st.dataframe(
            by_year[["ano_teste", "meses_epidemicos", "alertas", "recall", "precisao", "pr_auc"]],
            hide_index=True,
            column_config={
                "ano_teste": st.column_config.NumberColumn("Ano testado", format="plain"),
                "meses_epidemicos": st.column_config.NumberColumn("Meses epidêmicos reais", format="localized"),
                "alertas": st.column_config.NumberColumn("Alertas do modelo", format="localized"),
                "recall": st.column_config.ProgressColumn("Detectados", format="percent", min_value=0, max_value=1),
                "precisao": st.column_config.ProgressColumn("Alertas confirmados", format="percent", min_value=0, max_value=1),
                "pr_auc": st.column_config.NumberColumn("PR-AUC", format="%.2f"),
            },
            alt="Desempenho do modelo em cada ano testado",
        )
        st.caption("Em anos com poucas epidemias (2025 e 2026), poucos acertos ou erros mudam muito os percentuais.")

with st.container(border=True):
    st.subheader("Até onde dá para confiar", icon=":material/verified:")
    st.markdown("""
- A pontuação indica semelhança com situações do passado. Ela **não é uma probabilidade exata** nem prova que o clima
  causa os casos.
- Os casos são os **notificados como prováveis**: quando muita gente não procura atendimento, o número real é maior.
- Parte dos dados de clima não existe para alguns municípios e meses, e o sistema **não inventa valores**. Sem
  temperatura, o município aparece em cinza como "sem dados suficientes"; sem chuva, o modelo decide com as demais
  informações.
- Nos meses passados do mapa, parte dos dados exibidos foi usada para treinar o modelo; o desempenho honesto é o da
  seção acima.
- Este painel é um projeto acadêmico. Para decisões de saúde pública, consulte os boletins oficiais da Secretaria de
  Estado da Saúde.
""")

with st.container(border=True):
    st.subheader("Quantidade e qualidade dos dados", icon=":material/data_check:")
    total = int(missing["total"])
    with st.container(horizontal=True):
        st.metric("Registros (município × mês)", fmt.num(total), border=True)
        st.metric("Com dados completos para o modelo", fmt.pct(meta["registros_classificados"] / total), border=True,
                  help=f"{fmt.num(meta['registros_classificados'])} registros.")
        st.metric("Municípios no mapa", f"{meta['municipios_com_geometria']} de {meta['municipios']}", border=True)
    gaps = pd.DataFrame({
        "Informação": [fmt.FEATURE_LABELS[key] for key in
                       ("temperatura_media", "umidade_media", "precipitacao_total", "densidade_demografica", "casos_lag1")],
        "Registros sem o dado": [int(missing[key]) for key in
                                 ("temperatura_media", "umidade_media", "precipitacao_total", "densidade_demografica", "casos_lag1")],
    })
    gaps["Percentual"] = (gaps["Registros sem o dado"] / total).map(lambda v: fmt.pct(v, 1))
    st.dataframe(gaps, hide_index=True, alt="Registros sem cada informação usada pelo modelo",
                 column_config={"Registros sem o dado": st.column_config.NumberColumn(format="localized")})
    st.caption("Casos no mês anterior faltam no primeiro mês da série e quando o mês anterior não existe na base.")

technical = st.expander("Detalhes para especialistas", icon=":material/school:", on_change="rerun", key="sobre_tecnico")
if technical.open:
    with technical:
        st.markdown(f"""
- **Modelo:** {model['nome']} (scikit-learn, `VotingClassifier` com voto suave entre `RandomForestClassifier` e
  `HistGradientBoostingClassifier`). Alvo binário: {metrics.get('alvo', '')}. Limiar de decisão
  {model['limiar_decisao']}: {metrics.get('regra_limiar', '')}.
- **Validação:** janela temporal — para cada ano T, treino até T-2, limiar escolhido em T-1, re-treino até T-1 e
  teste em T. Média: PR-AUC {fmt.num(metrics.get('media', {}).get('pr_auc'), 3)}, F1 {fmt.num(metrics.get('media', {}).get('f1'), 3)},
  Brier {fmt.num(metrics.get('media', {}).get('brier'), 4)}.
- **Atributos ({len(model['atributos'])}):** {', '.join(f'`{name}`' for name in model['atributos'])}. Defasagens
  pelo mês calendário do mesmo município, sem preencher lacunas; vizinhos = 6 municípios mais próximos pelo centroide.
- **Importância:** por permutação (queda de PR-AUC) nos três anos mais recentes.
- **Reprodução:** notebooks `notebook_eda_dengue.ipynb` (coleta de todas as fontes, base e análise exploratória) e
  `notebook_modelo_baseline.ipynb` (avaliação, treino e base do painel), ou os scripts equivalentes em `scripts/`.
  Detalhes em `docs/base-do-app.md`.
""")
        st.plotly_chart(charts.importance_bars(model["importancia_global"], fmt.FEATURE_LABELS, height=520),
                        config=charts.PLOTLY_CONFIG, key="sobre_importancia",
                        alt="Importância de cada atributo do modelo")
        st.caption(f"Base de origem: `{meta['csv_sha256'][:12]}…` · modelo: `{meta['modelo_sha256'][:12]}…`")

st.download_button(
    "Baixar os dados mensais (CSV)", data=data.monthly_csv, file_name="dengue_sc_mensal.csv", mime="text/csv",
    icon=":material/download:", on_click="ignore",
    help="Um registro por município e mês, com casos prováveis, notificações, clima e a previsão do modelo.",
)
