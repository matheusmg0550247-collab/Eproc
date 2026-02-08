# app_equipes.py
# -*- coding: utf-8 -*-
import streamlit as st
from dashboard_equipes import render_dashboard

APP_URL_CLOUD = "https://statusconsultores.streamlit.app/"

# --- CONFIG INICIAL ---
st.set_page_config(
    page_title="Controle de Bastão - Cesupe",
    layout="wide",
    page_icon="🛡️"
)

# --- TIMES ---
EQUIPES = {
    1: {
        "nome_exibicao": "Equipe Eproc",
        "consultores": ["Gleissiane", "Bruno", "Marcelo", "Leonardo", "Michael", "Douglas"],
        "webhook_key": "bastao_eq1",
        "app_url": APP_URL_CLOUD
    },
    2: {
        "nome_exibicao": "Equipe Legados",
        "consultores": ["Hugo", "Gleyce", "Barbara", "Leandro", "Matheus", "Pablo", "Claudia", "Victoria"],
        "webhook_key": "bastao_eq2",
        "app_url": APP_URL_CLOUD
    }
}

# --- SESSION STATE ---
if "time_selecionado" not in st.session_state:
    st.session_state.time_selecionado = None
if "consultor_logado" not in st.session_state:
    st.session_state.consultor_logado = None

# --- LOGIN SIMPLES: ESCOLHE EQUIPE E CONSULTOR ---
if st.session_state.time_selecionado is None:
    st.markdown("## 🧑‍💻 Selecione sua equipe")

    col1, col2 = st.columns(2)
    for idx, (team_id, info) in enumerate(EQUIPES.items()):
        col = col1 if idx % 2 == 0 else col2
        with col:
            if st.button(info["nome_exibicao"], use_container_width=True):
                st.session_state.time_selecionado = team_id
                st.rerun()

elif st.session_state.consultor_logado is None:
    dados_time = EQUIPES[st.session_state.time_selecionado]
    st.markdown(f"## 👤 Selecione seu nome - {dados_time['nome_exibicao']}")

    cols = st.columns(3)
    for i, nome in enumerate(dados_time["consultores"]):
        with cols[i % 3]:
            if st.button(nome, use_container_width=True):
                st.session_state.consultor_logado = nome
                st.rerun()

else:
    # --- DASHBOARD PRINCIPAL ---
    time_selecionado = st.session_state.time_selecionado
    dados_time = EQUIPES[time_selecionado]

    other_team_id = 1 if time_selecionado == 2 else 2
    other_dados_time = EQUIPES[other_team_id]

    render_dashboard(
        team_id=time_selecionado,
        team_name=dados_time["nome_exibicao"],
        consultores_list=dados_time["consultores"],
        webhook_key=dados_time["webhook_key"],
        app_url=dados_time["app_url"],
        other_team_id=other_team_id,
        other_team_name=other_dados_time["nome_exibicao"],
        usuario_logado=st.session_state["consultor_logado"]
    )
