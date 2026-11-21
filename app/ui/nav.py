"""Caminhos das páginas e atalhos de navegação entre elas."""
from __future__ import annotations

import streamlit as st

HOME = "app_pages/inicio.py"
MAP = "app_pages/mapa.py"
MUNICIPALITY = "app_pages/municipio.py"
FACTORS = "app_pages/fatores.py"
SIMULATOR = "app_pages/simulador.py"
ABOUT = "app_pages/sobre.py"


PENDING_KEY = "_ir_para_pagina"


def open_municipality(name: str) -> None:
    """Callback: escolhe o município e agenda a troca de página."""
    st.session_state["municipio"] = name
    st.session_state[PENDING_KEY] = MUNICIPALITY


def open_simulator(name: str, month: int | None = None) -> None:
    """Callback: pré-seleciona município/mês no simulador e agenda a troca de página."""
    st.session_state["sim_municipio"] = name
    if month is not None:
        st.session_state["sim_mes"] = month
    st.session_state["sim_modo"] = "Simples"
    st.session_state[PENDING_KEY] = SIMULATOR


def follow_pending_navigation() -> None:
    """Chamado no entrypoint, depois de st.navigation: troca de página fora do callback."""
    target = st.session_state.pop(PENDING_KEY, None)
    if target:
        st.switch_page(target)
