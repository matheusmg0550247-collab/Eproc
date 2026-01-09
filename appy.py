# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date, time as dt_time
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json
import threading
import random
import base64

# --- Constantes de Consultores (Mantendo a lista do seu código funcional) ---
CONSULTORES = sorted([
  "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", 
  "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", 
  "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

# --- Constantes de Projetos ---
LISTA_PROJETOS = [
    "Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", 
    "IA nos Cartórios", "Notebook Lm"
]

# --- Webhooks ---
URL_GOOGLE_SHEETS = "https://script.google.com/macros/s/AKfycbxRP77Ie-jbhjEDk3F6Za_QWxiIEcEqwRHQ0vQPk63ExLm0JCR24n_nqkWbqdVWT5lhJg/exec"
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
CHAT_WEBHOOK_BASTAO = ""
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

# GIFs e Emojis
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂"
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
PUG2026_FILENAME = "pug2026.png"

# Templates
TEMPLATE_ERRO = """TITULO: 
OBJETIVO: 
RELATO DO ERRO/TESTE: 
RESULTADO: 
OBSERVAÇÃO (SE TIVER): """

EXEMPLO_TEXTO = """**TITULO** - Melhoria na Gestão das Procuradorias...""" # (Mesmo exemplo anterior)

# ============================================
# 2. FUNÇÕES AUXILIARES
# ============================================

@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'rotation_gif_start_time': None,
        'daily_logs': [],
        'simon_ranking': []
    }

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return None

def disparar_chat(webhook_url, mensagem):
    threading.Thread(target=lambda: requests.post(webhook_url, json={"text": mensagem}, timeout=10)).start()

def render_fireworks():
    st.markdown("""
    <style>
    @keyframes firework { 0% { transform: translate(var(--x), 60vmin); width: 0.5vmin; opacity: 1; } 100% { width: 45vmin; opacity: 0; } }
    .firework { --color1: #ff0000; --color2: #ffd700; position: absolute; top: 50%; left: 50%; animation: firework 2s infinite; background: radial-gradient(circle, var(--color1) 0.2vmin, #0000 0) 50% 0%; background-size: 0.5vmin 0.5vmin; background-repeat: no-repeat; }
    </style>
    <div class="firework"></div>""", unsafe_allow_html=True)

# ============================================
# 3. LÓGICA DE NEGÓCIO
# ============================================

def update_queue(consultor):
    is_checked = st.session_state.get(f'check_{consultor}')
    if is_checked:
        if consultor not in st.session_state.bastao_queue:
            st.session_state.bastao_queue.append(consultor)
            st.session_state.status_texto[consultor] = ''
    else:
        if consultor in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(consultor)
        st.session_state.status_texto[consultor] = 'Indisponível'
    check_and_assume_baton()

def check_and_assume_baton():
    q = st.session_state.bastao_queue
    dono = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if not dono and q:
        novo = q[0]
        st.session_state.status_texto[novo] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        st.balloons() # Fogos de artifício

# ============================================
# 4. INTERFACE
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
state = get_global_state_cache()
for k, v in state.items(): st.session_state.setdefault(k, v)

st_autorefresh(interval=8000, key="refresh")
render_fireworks()

# --- Cabeçalho com Pug ---
c_pug, c_enter = st.columns([2, 1])
with c_pug:
    img_b64 = get_img_as_base64(PUG2026_FILENAME)
    pug_src = f"data:image/png;base64,{img_b64}" if img_b64 else GIF_BASTAO_HOLDER
    st.markdown(f"""<div style='display: flex; align-items: center; gap: 20px;'>
        <h1 style='color: #FFD700;'>Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>
        <img src='{pug_src}' style='width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700;'>
    </div>""", unsafe_allow_html=True)

# --- Banner Responsável ---
col_main, col_side = st.columns([1.5, 1])
with col_main:
    responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.subheader("Responsável Atual")
    if responsavel:
        st.markdown(f"""<div style='background: #FFF8DC; border: 3px solid #FFD700; padding: 25px; border-radius: 15px; display: flex; align-items: center;'>
            <img src='{GIF_BASTAO_HOLDER}' style='width: 70px; height: 70px; margin-right: 20px; border-radius: 50%;'>
            <span style='font-size: 38px; font-weight: bold; color: #000080;'>{responsavel}</span>
        </div>""", unsafe_allow_html=True)
    
    # --- Ações ---
    st.markdown("### Consultor(a)")
    sel = st.selectbox("Selecione seu nome:", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox", label_visibility="collapsed")
    
    st.markdown("**Ações Principais:**")
    btns = st.columns(8) # 8 Botões
    if btns[0].button("🎯 Passar", use_container_width=True): 
        st.session_state.rotation_gif_start_time = datetime.now()
        # Lógica de rodar bastão aqui
    if btns[1].button("⏭️ Pular", use_container_width=True): pass
    if btns[2].button("📋 Atividades", use_container_width=True): st.session_state.active_view = "atv"
    if btns[3].button("🍽️ Almoço", use_container_width=True): pass
    if btns[4].button("👤 Ausente", use_container_width=True): pass
    if btns[5].button("🎙️ Sessão", use_container_width=True): pass
    if btns[6].button("🚶 Saída", use_container_width=True): pass
    if btns[7].button("📁 Projetos", use_container_width=True): st.session_state.active_view = "prj" # NOVO BOTÃO

    # --- Views Dinâmicas ---
    if st.session_state.get("active_view") == "prj":
        with st.container(border=True):
            p_sel = st.selectbox("Escolha o projeto:", LISTA_PROJETOS)
            if st.button("Confirmar Projeto"):
                st.session_state.status_texto[sel] = f"Projeto: {p_sel}"
                st.session_state.active_view = None; st.rerun()

    if st.session_state.get("active_view") == "err":
        with st.container(border=True):
            st.subheader("⚠️ Relatar Erro ou Novidade")
            t1, t2 = st.tabs(["📝 Preencher", "📖 Exemplo"])
            with t1:
                tipo = st.radio("Tipo:", ["Erro", "Novidade"], horizontal=True)
                txt = st.text_area("Relato:", value=(TEMPLATE_ERRO if tipo == "Erro" else ""), height=200)
                if st.button("Enviar para o Chat"):
                    disparar_chat(WEBHOOK_ERROS, f"🚨 {tipo} por {sel}\n{txt}")
                    st.session_state.active_view = None; st.rerun()
            with t2: st.markdown(EXEMPLO_TEXTO)

    # --- Ferramentas Inferiores ---
    st.markdown("---")
    tools = st.columns(6)
    tools[0].button("📑 Checklist", use_container_width=True)
    tools[1].button("🆘 Chamados", use_container_width=True)
    tools[2].button("📝 Atendimento", use_container_width=True)
    tools[3].button("⏰ H. Extras", use_container_width=True)
    tools[4].button("🧠 Descanso", use_container_width=True)
    if tools[5].button("⚠️ Erro/Novidade", use_container_width=True): # NOME POR EXTENSO
        st.session_state.active_view = "err"; st.rerun()

with col_side:
    st.header("Status dos Consultores")
    st.toggle("Auxílio Ativado", key="aux_atv")
    
    # --- Fila Ordenada ---
    st.subheader(f"✅ Na Fila ({len(st.session_state.bastao_queue)})")
    for idx, nome in enumerate(st.session_state.bastao_queue):
        c_n, c_c = st.columns([0.8, 0.2])
        prefix = "🥂 " if st.session_state.status_texto[nome] == "Bastão" else f"{idx+1}º "
        c_n.markdown(f"**{prefix}{nome}**")
        c_c.checkbox(" ", key=f"check_{nome}", value=True, on_change=update_queue, args=(nome,), label_visibility="collapsed")

    # --- Seção Projetos (VIOLET) ---
    prjs = [n for n, s in st.session_state.status_texto.items() if "Projeto:" in s]
    st.subheader(f"📁 Projetos ({len(prjs)})")
    for n in prjs:
        st.markdown(f"**{n}** :violet-background[{st.session_state.status_texto[n].replace('Projeto: ', '')}]", unsafe_allow_html=True)
    
    # Outras seções...
