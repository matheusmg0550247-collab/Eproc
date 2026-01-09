# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date, time as dt_time
from streamlit_autorefresh import st_autorefresh
import json
import threading
import base64

# --- CONFIGURAÇÃO DE PÁGINA (Sempre o primeiro comando) ---
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

# --- WEBHOOKS ---
URL_GOOGLE_SHEETS = "https://script.google.com/macros/s/AKfycbxRP77Ie-jbhjEDk3F6Za_QWxiIEcEqwRHQ0vQPk63ExLm0JCR24n_nqkWbqdVWT5lhJg/exec"
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
CHAT_WEBHOOK_BASTAO = ""
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

CONSULTORES = sorted([
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", 
    "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", 
    "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", 
    "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

LISTA_PROJETOS = ["Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", "IA nos Cartórios", "Notebook Lm"]
PUG2026_FILENAME = "pug2026.png"
BASTAO_EMOJI = "🥂"
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'

TEMPLATE_ERRO = """TITULO: 
OBJETIVO: 
RELATO DO ERRO/TESTE: 
RESULTADO: 
OBSERVAÇÃO (SE TIVER): """

# ============================================
# 2. INICIALIZAÇÃO DE ESTADO (Fix do AttributeError)
# ============================================

@st.cache_resource(show_spinner=False)
def get_global_state():
    return {
        'status_texto': {n: 'Indisponível' for n in CONSULTORES},
        'bastao_queue': [],
        'current_status_starts': {n: datetime.now() for n in CONSULTORES},
        'bastao_start_time': None,
        'report_last_run_date': date.min,
        'rotation_gif_start_time': None,
    }

# Garante que 'active_view' exista antes de qualquer renderização
if 'active_view' not in st.session_state:
    st.session_state.active_view = None

# Inicializa o restante do estado
persisted = get_global_state()
for key, value in persisted.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ============================================
# 3. UTILITÁRIOS
# ============================================

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return None

def disparar_chat(webhook_url, mensagem):
    if webhook_url:
        threading.Thread(target=lambda: requests.post(webhook_url, json={"text": mensagem}, timeout=10)).start()

def render_fireworks():
    st.markdown("""
    <style>
    @keyframes firework { 0% { transform: translate(var(--x), 60vmin); width: 0.5vmin; opacity: 1; } 100% { width: 45vmin; opacity: 0; } }
    .firework { --color1: #ff0000; --color2: #ffd700; position: absolute; top: 50%; left: 50%; animation: firework 2s infinite; background: radial-gradient(circle, var(--color1) 0.2vmin, #0000 0) 50% 0%; background-size: 0.5vmin 0.5vmin; background-repeat: no-repeat; }
    </style>
    <div class="firework"></div><div class="firework" style="left:30%; animation-delay:-0.5s;"></div><div class="firework" style="left:70%; animation-delay:-1s;"></div>
    """, unsafe_allow_html=True)

def registrar_mudanca(nome, novo_status):
    if nome == "Selecione um nome" or not nome: return
    old_status = st.session_state.status_texto.get(nome, "Indisponível")
    st.session_state.status_texto[nome] = novo_status
    st.session_state.current_status_starts[nome] = datetime.now()
    disparar_chat(GOOGLE_CHAT_WEBHOOK_REGISTRO, f"📝 *Status:* {nome} ➔ {novo_status}")

# ============================================
# 4. LÓGICA DO BASTÃO
# ============================================

def update_queue(nome):
    is_checked = st.session_state[f"chk_{nome}"]
    if is_checked:
        if nome not in st.session_state.bastao_queue:
            st.session_state.bastao_queue.append(nome)
            st.session_state.status_texto[nome] = ''
    else:
        if nome in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(nome)
        st.session_state.status_texto[nome] = 'Indisponível'
    check_and_assume_baton()

def check_and_assume_baton():
    q = st.session_state.bastao_queue
    dono = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if not dono and q:
        novo = q[0]
        st.session_state.status_texto[novo] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        disparar_chat(CHAT_WEBHOOK_BASTAO, f"🥂 *Responsável:* {novo}")
        st.balloons()

# ============================================
# 5. INTERFACE PRINCIPAL
# ============================================

st_autorefresh(interval=8000, key="refresh")
render_fireworks()

# --- CABEÇALHO (Pug + Título) ---
c_pug, c_enter = st.columns([2, 1])
with c_pug:
    b64 = get_img_as_base64(PUG2026_FILENAME)
    src = f"data:image/png;base64,{b64}" if b64 else GIF_BASTAO_HOLDER
    st.markdown(f'''<div style="display: flex; align-items: center; gap: 15px;">
        <h1 style="color: #FFD700; margin: 0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>
        <img src="{src}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;">
    </div>''', unsafe_allow_html=True)

st.divider()

col_main, col_side = st.columns([1.6, 1])

with col_main:
    # Responsável Atual com Pug
    responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.subheader("Responsável Atual")
    if responsavel:
        st.markdown(f'''<div style="background: #FFF8DC; border: 4px solid #FFD700; padding: 25px; border-radius: 20px; display: flex; align-items: center;">
            <img src="{src}" style="width: 60px; height: 60px; margin-right: 20px; border-radius: 50%;">
            <span style="font-size: 32px; font-weight: bold; color: #000080;">{responsavel}</span>
        </div>''', unsafe_allow_html=True)
    
    st.subheader("Consultor(a)")
    u_sel = st.selectbox("Seu nome:", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox", label_visibility="collapsed")
    
    st.markdown("**Ações Principais:**")
    btns = st.columns(8)
    if btns[0].button("🎯 Passar", use_container_width=True):
        if u_sel == responsavel:
            st.session_state.status_texto[responsavel] = ''
            if responsavel in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(responsavel)
            check_and_assume_baton(); st.rerun()
    if btns[1].button("📋 Atividades", use_container_width=True): st.session_state.active_view = "atv"
    if btns[2].button("🍽️ Almoço", use_container_width=True): registrar_mudanca(u_sel, "Almoço"); st.rerun()
    if btns[3].button("👤 Ausente", use_container_width=True): registrar_mudanca(u_sel, "Ausente"); st.rerun()
    if btns[4].button("🎙️ Sessão", use_container_width=True): st.session_state.active_view = "ses"
    if btns[5].button("🚶 Saída", use_container_width=True): registrar_mudanca(u_sel, "Saída rápida"); st.rerun()
    # BOTÃO PROJETOS NAS AÇÕES PRINCIPAIS
    if btns[6].button("📁 Projetos", use_container_width=True): st.session_state.active_view = "prj"
    btns[7].button("🔄 Atualizar", on_click=lambda: st.rerun(), use_container_width=True)

    # VIEWS DINÂMICAS
    if st.session_state.active_view == "prj":
        with st.container(border=True):
            p_sel = st.selectbox("Escolha o projeto:", LISTA_PROJETOS)
            if st.button("Gravar Projeto"):
                registrar_mudanca(u_sel, f"Projeto: {p_sel}"); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "err":
        with st.container(border=True):
            st.subheader("⚠️ Relatar Erro ou Novidade")
            t1, t2 = st.tabs(["📝 Preencher", "📖 Exemplo"])
            with t1:
                tipo = st.radio("Tipo:", ["Erro", "Novidade"], horizontal=True)
                txt = st.text_area("Descreva:", value=(TEMPLATE_ERRO if tipo == "Erro" else ""), height=200)
                if st.button("Enviar para o Chat"):
                    disparar_chat(WEBHOOK_ERROS, f"🚨 {tipo} por {u_sel}\n{txt}")
                    st.session_state.active_view = None; st.rerun()
            with t2: st.markdown("...Exemplo de Procuradorias...")

    st.markdown("---")
    # Barra de Ferramentas Inferior
    tool_cols = st.columns(6)
    tool_cols[0].button("📑 Checklist", use_container_width=True)
    tool_cols[1].button("🆘 Chamados", use_container_width=True)
    tool_cols[2].button("📝 Atendimento", use_container_width=True)
    tool_cols[3].button("⏰ H. Extras", use_container_width=True)
    tool_cols[4].button("🧠 Descanso", use_container_width=True)
    # BOTÃO ERRO/NOVIDADE POR EXTENSO
    if tool_cols[5].button("⚠️ Erro/Novidade", use_container_width=True):
        st.session_state.active_view = "err"; st.rerun()

with col_side:
    st.header("Status da Equipe")
    st.markdown("---")
    
    # FILA NUMERADA
    st.subheader(f"✅ Na Fila ({len(st.session_state.bastao_queue)})")
    for idx, n in enumerate(st.session_state.bastao_queue):
        cn, cc = st.columns([0.8, 0.2])
        pref = "🥂 " if st.session_state.status_texto[n] == "Bastão" else f"{idx+1}º "
        cn.markdown(f"**{pref}{n}**")
        cc.checkbox(" ", key=f"chk_{n}", value=True, on_change=update_queue, args=(n,), label_visibility="collapsed")

    # SEÇÃO PROJETOS (VIOLET BACKGROUND)
    st.divider()
    prjs = [n for n, s in st.session_state.status_texto.items() if "Projeto:" in s]
    st.subheader(f"📁 Projetos ({len(prjs)})")
    for n in prjs:
        st.markdown(f"**{n}** :violet-background[{st.session_state.status_texto[n].replace('Projeto: ', '')}]", unsafe_allow_html=True)
