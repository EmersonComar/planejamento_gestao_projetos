"""Ponto de entrada do app (Streamlit Community Cloud: app/main.py)."""
import sys
from pathlib import Path

# O Community Cloud adiciona só a pasta do entrypoint ao path; incluímos a raiz do projeto.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from app.ui import links, nav  # noqa: E402

st.set_page_config(page_title="Dengue em SC", page_icon=":material/pest_control:", layout="wide")

page = st.navigation(
    [
        st.Page(nav.HOME, title="Início", icon=":material/home:", default=True),
        st.Page(nav.MAP, title="Mapa", icon=":material/map:", url_path="mapa"),
        st.Page(nav.MUNICIPALITY, title="Meu município", icon=":material/location_city:", url_path="municipio"),
        st.Page(nav.FACTORS, title="Entenda a dengue", icon=":material/query_stats:", url_path="entenda"),
        st.Page(nav.SIMULATOR, title="Simulador", icon=":material/tune:", url_path="simulador"),
        st.Page(nav.ABOUT, title="Sobre os dados", icon=":material/menu_book:", url_path="sobre"),
    ],
    position="top",
)
nav.follow_pending_navigation()
page.run()

st.space("large")
st.caption(
    "Dados públicos: InfoDengue (Fiocruz), IBGE, INMET, ANA e DIVE/SC. Este painel é um projeto acadêmico "
    "e não substitui os boletins oficiais da Secretaria de Estado da Saúde de Santa Catarina. "
    f"[Código, dados e análises]({links.REPO_URL}) · "
    + (f"[Artigo]({links.ARTICLE_URL})" if links.ARTICLE_URL else "Artigo científico em elaboração")
)
