import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date, time as dt_time
from streamlit_autorefresh import st_autorefresh
import json
import threading
import base64
import plotly.express as px

# 1. CONFIGURAÇÕES E ESTILIZAÇÃO (Visual do Dashboard + Pug)
st.set_page_config(page_title="Gestão Cesupe 2026", layout="wide", page_icon="🥂")

# Carregamento do Pug
PUG_FILENAME = "pug2026.png"
@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return None

st.markdown("""
    <style>
    .title-card { padding: 8px; border-radius: 5px; color: white; font-weight: bold; text-align: center; width: 100%; margin-bottom: 10px; text-transform: uppercase; font-size: 14px; }
    .bg-bastao { background-color: #D4AF37; } .bg-atividade { background-color: #0056b3; }
    .bg-projeto { background-color: #8b5cf6; } .bg-sessao { background-color: #6f42c1; }
    .bg-almoco { background-color: #d9534f; } .bg-ausente { background-color: #6c757d; }
    .stPopover { display: flex; justify-content: center; margin-bottom: 5px; }
    div[data-testid="stPopoverBody"] { min-width: 800px !important; }
    .stPopover button { width: 220px !important; font-size: 11px !important; border: 1px solid #ddd !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONSTANTES E WEBHOOKS
CONSULTORES = sorted(["Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"])
LISTA_PROJETOS = ["Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", "IA nos Cartórios", "Notebook Lm"]
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"
CHAT_WEBHOOK_BASTAO = ""

# 3. LÓGICA DE ESTADO
@st.cache_resource
def get_global_state():
    return {'status_texto': {n: 'Ausente' for n in CONSULTORES}, 'bastao_queue': [], 'starts': {n: datetime.now() for n in CONSULTORES}, 'last_run': date.min}

if 'status_texto' not in st.session_state:
    for k, v in get_global_state().items(): st.session_state[k] = v
    st.session_state.active_view = None

st_autorefresh(interval=10000, key="global_refresh")

# 4. CABEÇALHO (Pug + Título)
c_pug, c_enter = st.columns([2, 1])
with c_pug:
    img_data = get_img_as_base64(PUG_FILENAME)
    pug_src = f"data:image/png;base64,{img_data}" if img_data else ""
    st.markdown(f'<div style="display: flex; align-items: center; gap: 20px;"><h1 style="color: #FFD700; margin: 0;">Controle Bastão Cesupe 2026 🥂</h1><img src="{pug_src}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid #FFD700;"></div>', unsafe_allow_html=True)

# 5. ÁREA DE AÇÃO (Banner + Botões)
st.divider()
col_act, col_chart = st.columns([1.8, 1.2])

with col_act:
    responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if responsavel:
        st.markdown(f'<div style="background: #FFF8DC; border: 3px solid #FFD700; padding: 15px; border-radius: 12px; display: flex; align-items: center;"><img src="{pug_src}" style="width: 45px; height: 45px; margin-right: 15px; border-radius: 50%;"><span style="font-size: 24px; font-weight: bold; color: #000080;">{responsavel}</span></div>', unsafe_allow_html=True)
    
    sel_user = st.selectbox("Selecione seu nome:", ["Selecione..."] + CONSULTORES, key="main_user")
    
    # Duas linhas de botões
    b1, b2, b3, b4, b5 = st.columns(5)
    if b1.button("🎯 Passar", use_container_width=True): st.balloons() # Fogos
    b2.button("📋 Atividades", use_container_width=True)
    b3.button("🎙️ Sessão", use_container_width=True)
    b4.button("📁 Projetos", use_container_width=True)
    b5.button("👤 Ausente", use_container_width=True)
    
    t1, t2, t3, t4, t5, t6 = st.columns(6)
    t1.button("📑 Checklist", use_container_width=True)
    t2.button("🆘 Chamados", use_container_width=True)
    t3.button("📝 Atendimento", use_container_width=True)
    t4.button("⏰ H. Extras", use_container_width=True)
    t5.button("🧠 Descanso", use_container_width=True)
    t6.button("⚠️ Erro/Novidade", use_container_width=True)

with col_chart:
    # Gráfico Donut
    status_counts = pd.Series(st.session_state.status_texto).value_counts().reset_index()
    fig = px.pie(status_counts, values='count', names='index', hole=.4, height=220, color_discrete_sequence=px.colors.qualitative.Pastel)
    fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

# 6. GRID DE STATUS (O Visual das 6 Colunas)
st.divider()
cols = st.columns(6)
cats = [("Bastão", "bg-bastao"), ("Atividade", "bg-atividade"), ("Projeto", "bg-projeto"), ("Sessão", "bg-sessao"), ("Almoço", "bg-almoco"), ("Ausente", "bg-ausente")]

for i, (name, css) in enumerate(cats):
    with cols[i]:
        st.markdown(f'<div class="title-card {css}">{name}</div>', unsafe_allow_html=True)
        # Filtra e exibe os consultores conforme o grid do dashboard
        for consultor, status in st.session_state.status_texto.items():
            if (name == "Bastão" and status == "Bastão") or (name != "Bastão" and name.lower() in status.lower()):
                with st.popover(consultor, use_container_width=True):
                    st.write(f"Histórico de {consultor}") # Popover amplo
