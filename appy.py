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
import re
import threading
import random
import base64
import os

# --- Constantes de Consultores ---
CONSULTORES = sorted([
  "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

LISTA_PROJETOS = [
    "Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", 
    "IA nos Cartórios", "Notebook Lm"
]

# --- FUNÇÃO DE CACHE GLOBAL ---
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        'lunch_warning_info': None,
        'auxilio_ativo': False, 
        'daily_logs': [],
        'simon_ranking': []
    }

# --- Constantes (Webhooks) ---
URL_GOOGLE_SHEETS = "https://script.google.com/macros/s/AKfycbxRP77Ie-jbhjEDk3F6Za_QWxiIEcEqwRHQ0vQPk63ExLm0JCR24n_nqkWbqdVWT5lhJg/exec"
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "" 
GOOGLE_CHAT_WEBHOOK_REGISTRO = ""
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

TEMPLATE_ERRO = """TITULO: 
OBJETIVO: 
RELATO DO ERRO/TESTE: 
RESULTADO: 
OBSERVAÇÃO (SE TIVER): """

EXEMPLO_TEXTO = """**TITULO** - Melhoria na Gestão das Procuradorias
**OBJETIVO**
Permitir que os perfis de Procurador Chefe e Gerente de Procuradoria possam gerenciar os usuários das procuradorias...
**RELATO DO TESTE**
Foram realizados testes no menu “Gerenciar Procuradores”...
**RESULTADO**
O teste não foi bem-sucedido: mensagem de erro ao cadastrar novos usuários."""

GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
PUG2026_FILENAME = "pug2026.png"

# ============================================
# 2. FUNÇÕES AUXILIARES
# ============================================

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception: return None

def save_state():
    global_data = get_global_state_cache()
    try:
        for k in global_data.keys():
            if k in st.session_state: global_data[k] = st.session_state[k]
    except Exception as e: print(f'Erro save: {e}')

def load_state():
    return get_global_state_cache()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def log_status_change(consultor, old_status, new_status, duration):
    entry = {'timestamp': datetime.now(), 'consultor': consultor, 'old_status': old_status, 'new_status': new_status, 'duration': duration}
    st.session_state.daily_logs.append(entry)
    st.session_state.current_status_starts[consultor] = datetime.now()

def _send_webhook_thread(url, payload):
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        msg = {"text": f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}"}
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, msg)).start()

def render_fireworks():
    fireworks_css = """
    <style>
    @keyframes firework { 0% { transform: translate(var(--x), 60vmin); width: 0.5vmin; opacity: 1; } 100% { width: 45vmin; opacity: 0; } }
    .firework { --color1: #ff0000; --color2: #ffd700; position: absolute; top: 50%; left: 50%; animation: firework 2s infinite; background: radial-gradient(circle, var(--color1) 0.2vmin, #0000 0) 50% 0%; background-size: 0.5vmin 0.5vmin; background-repeat: no-repeat; }
    </style>
    <div class="firework"></div><div class="firework" style="left:30%; animation-delay:-0.5s;"></div><div class="firework" style="left:70%; animation-delay:-1s;"></div>
    """
    st.markdown(fireworks_css, unsafe_allow_html=True)

# ============================================
# 3. LÓGICA DE NEGÓCIO
# ============================================

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    num = len(queue)
    next_idx = (current_index + 1) % num
    attempts = 0
    while attempts < num:
        c = queue[next_idx]
        if not skips.get(c, False) and st.session_state.get(f'check_{c}'): return next_idx
        next_idx = (next_idx + 1) % num
        attempts += 1
    return -1

def check_and_assume_baton():
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    
    if not current_holder and queue:
        idx = find_next_holder_index(-1, queue, skips)
        if idx != -1:
            target = queue[idx]
            st.session_state.status_texto[target] = 'Bastão'
            st.session_state.bastao_start_time = datetime.now()
            st.session_state.play_sound = True
            send_chat_notification_internal(target, 'Bastão')
            save_state()

def update_queue(consultor):
    is_checked = st.session_state.get(f'check_{consultor}')
    old_s = st.session_state.status_texto.get(consultor, '')
    dur = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())
    
    if is_checked:
        log_status_change(consultor, old_s, '', dur)
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    else:
        log_status_change(consultor, old_s, 'Indisponível', dur)
        st.session_state.status_texto[consultor] = 'Indisponível'
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
    
    check_and_assume_baton()
    save_state()

def rotate_bastao():
    selected = st.session_state.consultor_selectbox
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder: return
    
    queue = st.session_state.bastao_queue
    idx = queue.index(current_holder)
    next_idx = find_next_holder_index(idx, queue, st.session_state.skip_flags)
    
    if next_idx != -1:
        new_holder = queue[next_idx]
        dur = datetime.now() - st.session_state.bastao_start_time
        log_status_change(current_holder, 'Bastão', '', dur)
        st.session_state.status_texto[current_holder] = ''
        st.session_state.status_texto[new_holder] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.rotation_gif_start_time = datetime.now()
        st.balloons()
        save_state()

# ============================================
# 4. EXECUÇÃO PRINCIPAL
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
persisted = load_state()
for k, v in persisted.items():
    if k not in st.session_state: st.session_state[k] = v

st_autorefresh(interval=8000, key="refresh")
render_fireworks()

# --- CABEÇALHO ---
c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img_b64 = get_img_as_base64(PUG2026_FILENAME)
    src = f"data:image/png;base64,{img_b64}" if img_b64 else GIF_BASTAO_HOLDER
    st.markdown(f"""<div style="display: flex; align-items: center; gap: 15px;">
        <h1 style="color: #FFD700; margin:0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>
        <img src="{src}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700;">
    </div>""", unsafe_allow_html=True)

# --- GRID PRINCIPAL ---
col_p, col_d = st.columns([1.5, 1])

with col_p:
    resp = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável pelo Bastão")
    if resp:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%); border: 3px solid #FFD700; padding: 20px; border-radius: 15px; display: flex; align-items: center;">
            <img src="{GIF_BASTAO_HOLDER}" style="width: 70px; height: 70px; border-radius: 50%; margin-right: 20px;">
            <span style="font-size: 38px; font-weight: bold; color: #000080;">{resp}</span>
        </div>""", unsafe_allow_html=True)
    
    st.subheader("Consultor(a)")
    st.selectbox('Selecione seu nome:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    st.markdown("**Ações:**")
    # EXPANDIDO PARA 8 BOTÕES (Incluindo Projetos)
    btns = st.columns(8)
    btns[0].button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    btns[1].button('⏭️ Pular', use_container_width=True)
    btns[2].button('📋 Atividades', on_click=lambda: st.session_state.update({'active_view': 'atv'}), use_container_width=True)
    btns[3].button('🍽️ Almoço', use_container_width=True)
    btns[4].button('👤 Ausente', use_container_width=True)
    btns[5].button('🎙️ Sessão', use_container_width=True)
    btns[6].button('🚶 Saída', use_container_width=True)
    # BOTÃO PROJETOS
    if btns[7].button('📁 Projetos', use_container_width=True): 
        st.session_state.active_view = 'prj'

    # --- VIEWS DINÂMICAS ---
    if st.session_state.active_view == 'prj':
        with st.container(border=True):
            st.markdown("### 📁 Selecionar Projeto")
            p_sel = st.selectbox("Escolha o projeto:", LISTA_PROJETOS)
            if st.button("Confirmar Projeto", type="primary"):
                user = st.session_state.consultor_selectbox
                if user != 'Selecione um nome':
                    st.session_state.status_texto[user] = f"Projeto: {p_sel}"
                    st.session_state.active_view = None
                    st.rerun()

    if st.session_state.active_view == 'err':
        with st.container(border=True):
            st.subheader("⚠️ Relatar Erro ou Novidade")
            tab1, tab2 = st.tabs(["📝 Preencher", "📖 Exemplo"])
            with tab1:
                tipo = st.radio("Tipo:", ["Erro", "Novidade"], horizontal=True)
                val = TEMPLATE_ERRO if tipo == "Erro" else ""
                txt = st.text_area("Descreva:", value=val, height=200)
                if st.button("Enviar para o Chat"):
                    payload = {"text": f"🚨 *NOVO RELATO: {tipo}*\n*Consultor:* {st.session_state.consultor_selectbox}\n\n{txt}"}
                    threading.Thread(target=_send_webhook_thread, args=(WEBHOOK_ERROS, payload)).start()
                    st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
            with tab2: st.markdown(EXEMPLO_TEXTO)

    st.markdown("---")
    # BOTÕES INFERIORES (6 Colunas para Erro/Novidade)
    tools = st.columns(6)
    tools[0].button("📑 Checklist", use_container_width=True)
    tools[1].button("🆘 Chamados", use_container_width=True)
    tools[2].button("📝 Atendimento", use_container_width=True)
    tools[3].button("⏰ H. Extras", use_container_width=True)
    tools[4].button("🧠 Descanso", use_container_width=True)
    # BOTÃO ERRO/NOVIDADE POR EXTENSO
    if tools[5].button("⚠️ Erro/Novidade", use_container_width=True):
        st.session_state.active_view = 'err'
        st.rerun()

with col_d:
    st.header('Status da Equipe')
    st.toggle("Auxílio HP/Emails/Whatsapp", key='aux_atv')
    
    # --- RENDERIZAÇÃO DA FILA ---
    st.subheader(f"✅ Na Fila ({len(st.session_state.bastao_queue)})")
    for idx, nome in enumerate(st.session_state.bastao_queue):
        c_n, c_c = st.columns([0.8, 0.2])
        prefix = "🥂 " if st.session_state.status_texto[nome] == "Bastão" else f"{idx+1}º "
        c_n.markdown(f"**{prefix}{nome}**")
        c_c.checkbox(' ', key=f'check_{nome}', value=True, on_change=update_queue, args=(nome,))

    # --- RENDERIZAÇÃO PROJETOS ---
    prjs = [n for n, s in st.session_state.status_texto.items() if "Projeto:" in s]
    st.subheader(f"📁 Projetos ({len(prjs)})")
    for n in prjs:
        st.markdown(f"**{n}** :violet-background[{st.session_state.status_texto[n].replace('Projeto: ', '')}]", unsafe_allow_html=True)
