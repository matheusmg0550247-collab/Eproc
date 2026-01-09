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
import base64

# --- Constantes de Consultores ---
CONSULTORES = sorted([
  "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", 
  "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", 
  "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

LISTA_PROJETOS = ["Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", "IA nos Cartórios", "Notebook Lm"]

# --- Webhooks e Integração ---
URL_GOOGLE_SHEETS = "https://script.google.com/macros/s/AKfycbxRP77Ie-jbhjEDk3F6Za_QWxiIEcEqwRHQ0vQPk63ExLm0JCR24n_nqkWbqdVWT5lhJg/exec"
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k" 

# --- CONFIGURAÇÃO DE ESTADO GLOBAL ---
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min,
        'auxilio_ativo': False, 
        'daily_logs': []
    }

# ============================================
# 2. FUNÇÕES AUXILIARES (LOGS E GOOGLE SHEETS)
# ============================================

def save_state():
    # Sincroniza o session_state com o recurso de cache global
    global_data = get_global_state_cache()
    for k in global_data.keys():
        if k in st.session_state: global_data[k] = st.session_state[k]

def log_to_google_sheets(consultor, old_status, new_status, duration):
    payload = {"consultor": consultor, "old_status": old_status, "new_status": new_status, "duration": duration}
    try: requests.post(URL_GOOGLE_SHEETS, json=payload, timeout=10)
    except: pass

def log_status_change(consultor, old_status, new_status, duration):
    dur_str = format_time_duration(duration)
    # Envio assíncrono para não travar a tela
    threading.Thread(target=log_to_google_sheets, args=(consultor, old_status, new_status, dur_str)).start()
    threading.Thread(target=lambda: requests.post(GOOGLE_CHAT_WEBHOOK_REGISTRO, json={"text": f"📝 *Status:* {consultor} ➔ {new_status} ({dur_str})"})).start()
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '00:00:00'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

# ============================================
# 3. LÓGICA DO BASTÃO E FILA
# ============================================

def check_and_assume_baton():
    q = st.session_state.bastao_queue
    dono = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if not dono and q:
        novo = q[0]
        st.session_state.status_texto[novo] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        save_state()

def update_queue(consultor):
    is_checked = st.session_state.get(f'check_{consultor}')
    old_s = st.session_state.status_texto.get(consultor, 'Indisponível')
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

# ============================================
# 4. INTERFACE PRINCIPAL
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

# Inicialização de Estado
if 'status_texto' not in st.session_state:
    for k, v in get_global_state_cache().items(): st.session_state[k] = v
    st.session_state.active_view = None

st_autorefresh(interval=8000, key="refresh")

# Cabeçalho
st.markdown(f'<h1 style="color:#FFD700;">Controle Bastão Cesupe 2026 🥂</h1>', unsafe_allow_html=True)
st.divider()

col_p, col_d = st.columns([1.5, 1])

with col_p:
    # Banner Responsável
    resp = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável Atual")
    if resp:
        st.markdown(f'<div style="background:#FFF8DC;border:3px solid #FFD700;padding:20px;border-radius:15px;font-size:32px;font-weight:bold;color:#000080;">🥂 {resp}</div>', unsafe_allow_html=True)
    
    st.subheader("Ações")
    sel_u = st.selectbox("Selecione seu nome:", ["Selecione um nome"] + CONSULTORES, key="user_sel")
    
    # Grid de 8 Colunas para Ações
    c_btn = st.columns(8)
    c_btn[0].button('🎯 Passar', use_container_width=True)
    c_btn[1].button('⏭️ Pular', use_container_width=True)
    c_btn[2].button('📋 Atividades', use_container_width=True)
    c_btn[3].button('🍽️ Almoço', use_container_width=True)
    c_btn[4].button('👤 Ausente', use_container_width=True)
    c_btn[5].button('🎙️ Sessão', use_container_width=True)
    c_btn[6].button('🚶 Saída', use_container_width=True)
    if c_btn[7].button('📁 Projetos', use_container_width=True): st.session_state.active_view = 'prj'

    # Views Dinâmicas (Projetos / Erros)
    if st.session_state.active_view == 'prj':
        with st.container(border=True):
            p_sel = st.selectbox("Escolha o Projeto:", LISTA_PROJETOS)
            if st.button("Gravar Projeto"):
                log_status_change(sel_u, st.session_state.status_texto[sel_u], f"Projeto: {p_sel}", timedelta(0))
                st.session_state.status_texto[sel_u] = f"Projeto: {p_sel}"
                st.session_state.active_view = None; st.rerun()

    st.markdown("---")
    # Barra de Ferramentas Inferior (6 Colunas)
    t_cols = st.columns(6)
    t_cols[0].button("📑 Checklist", use_container_width=True)
    t_cols[1].button("🆘 Chamados", use_container_width=True)
    t_cols[2].button("📝 Atendimento", use_container_width=True)
    t_cols[3].button("⏰ H. Extras", use_container_width=True)
    t_cols[4].button("🧠 Descanso", use_container_width=True)
    if t_cols[5].button("⚠️ Erro/Novidade", use_container_width=True): st.session_state.active_view = 'err'; st.rerun()

with col_d:
    st.header('Status da Equipe')
    st.toggle("Auxílio HP/Emails/Whatsapp", key='aux_atv', on_change=save_state)
    st.markdown("---")
    
    # LISTA COMPLETA COM CHECKBOXES (Restaurada)
    for n in CONSULTORES:
        s = st.session_state.status_texto.get(n, 'Indisponível')
        c_n, c_c = st.columns([0.8, 0.2])
        
        # Checkbox para todos os consultores (Marcar entra na fila, Desmarcar sai)
        is_in_queue = (s == 'Bastão' or s == '')
        c_c.checkbox(' ', key=f'check_{n}', value=is_in_queue, on_change=update_queue, args=(n,), label_visibility='collapsed')
        
        # Estilização visual por categoria
        if n == resp: c_n.markdown(f"**🥂 {n}**")
        elif s.startswith('Projeto:'): c_n.markdown(f"**{n}** :violet-background[{s.replace('Projeto: ', '')}]")
        elif s == '': c_n.write(f"**{n}** :blue-background[Aguardando]")
        elif s == 'Indisponível': c_n.caption(f"• {n} (Fora da Fila)")
        else: c_n.markdown(f"**{n}** :orange-background[{s}]")
