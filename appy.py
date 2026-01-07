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
    "Alex Paulo da Silva",
    "Dirceu Gonçalves Siqueira Neto",
    "Douglas de Souza Gonçalves",
    "Farley Leandro de Oliveira Juliano", 
    "Gleis da Silva Rodrigues",
    "Hugo Leonardo Murta",
    "Igor Dayrell Gonçalves Correa",
    "Jerry Marcos dos Santos Neto",
    "Jonatas Gomes Saraiva",
    "Leandro Victor Catharino",
    "Luiz Henrique Barros Oliveira",
    "Marcelo dos Santos Dutra",
    "Marina Silva Marques",
    "Marina Torres do Amaral",
    "Vanessa Ligiane Pimenta Santos"
])

# --- FUNÇÃO DE CACHE GLOBAL (Persistência entre usuários) ---
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    return {
        'status_texto': {nome: 'Ausente' for nome in CONSULTORES},
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

# --- Constantes de Webhooks ---
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQA5CyNolU/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zolqmc0YfJ5bPzsqLrefwn8yBbNQLLfFBzLTwIkr7W4" 
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "Whatsapp/Plantão", "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"]
ATIVIDADES_EXIGEM_DETALHE = ["Treinamento", "Homologação", "Redação Documentos", "Outros"]

REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]

GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUSES_DE_SAIDA = ['Atendimento', 'Almoço', 'Saída rápida', 'Ausente', 'Sessão'] 
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
PUG2026_FILENAME = "pug2026.png"

# ============================================
# 2. FUNÇÕES AUXILIARES E ESTADO
# ============================================

def save_state():
    global_data = get_global_state_cache()
    try:
        keys_to_persist = [
            'status_texto', 'bastao_queue', 'skip_flags', 'current_status_starts', 
            'bastao_counts', 'priority_return_queue', 'bastao_start_time', 
            'report_last_run_date', 'rotation_gif_start_time', 'lunch_warning_info', 
            'auxilio_ativo', 'daily_logs', 'simon_ranking'
        ]
        for key in keys_to_persist:
            if key in st.session_state:
                global_data[key] = st.session_state[key]
    except: pass

def init_session_state():
    global_data = get_global_state_cache()
    
    # Definições Padrão Locais (Resetam ao dar F5 no navegador)
    defaults = {
        'active_view': None,
        'play_sound': False,
        'gif_warning': False,
        'consultor_selectbox': 'Selecione um nome',
        'simon_status': 'start',
        'simon_sequence': [],
        'simon_user_input': []
    }
    
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Carregar dados persistentes do Cache Global para a Sessão Atual
    for key, val in global_data.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Sincronizar Checkboxes com o Status atual
    for nome in CONSULTORES:
        status = st.session_state.status_texto.get(nome, 'Ausente')
        st.session_state[f'check_{nome}'] = (status == 'Bastão' or status == '')
    
    check_and_assume_baton()

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    st.session_state.daily_logs.append({'timestamp': datetime.now(), 'consultor': consultor, 'old_status': old_status, 'new_status': new_status, 'duration': duration})
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def _send_webhook_thread(url, payload):
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def send_chat_notification_internal(consultor, status):
    if status == 'Bastão':
        msg = {"text": f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Responsável:** {consultor}\n- **Painel:** {APP_URL_CLOUD}"}
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, msg)).start()

# ============================================
# 3. LÓGICA DO BASTÃO
# ============================================

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    num = len(queue)
    next_idx = (current_index + 1) % num
    for _ in range(num):
        c = queue[next_idx]
        if not skips.get(c, False) and st.session_state.get(f'check_{c}'): return next_idx
        next_idx = (next_idx + 1) % num
    return -1

def check_and_assume_baton():
    queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    is_valid = (current_holder and current_holder in queue and st.session_state.get(f'check_{current_holder}'))
    
    first_idx = find_next_holder_index(-1, queue, skips)
    should_have = current_holder if is_valid else (queue[first_idx] if first_idx != -1 else None)
    
    changed = False
    for c in CONSULTORES:
        if c != should_have and st.session_state.status_texto.get(c) == 'Bastão':
            log_status_change(c, 'Bastão', 'Ausente', datetime.now() - st.session_state.current_status_starts.get(c, datetime.now()))
            st.session_state.status_texto[c] = 'Ausente'; changed = True
            
    if should_have and st.session_state.status_texto.get(should_have) != 'Bastão':
        st.session_state.status_texto[should_have] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        send_chat_notification_internal(should_have, 'Bastão'); changed = True
        
    if changed: save_state()

def update_queue(consultor):
    is_checked = st.session_state.get(f'check_{consultor}')
    old_status = st.session_state.status_texto.get(consultor, 'Ausente')
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())
    
    if is_checked:
        log_status_change(consultor, old_status, '', duration)
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    else:
        # CORREÇÃO: Ao desmarcar, vai direto para Ausente
        log_status_change(consultor, old_status, 'Ausente', duration)
        st.session_state.status_texto[consultor] = 'Ausente'
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
        st.session_state.skip_flags.pop(consultor, None)
        
    check_and_assume_baton(); save_state()

def rotate_bastao():
    selected = st.session_state.consultor_selectbox
    if selected == 'Selecione um nome': return
    
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder: 
        st.session_state.gif_warning = True
        return
        
    queue = st.session_state.bastao_queue
    try: idx = queue.index(current_holder)
    except: return
    
    nxt_idx = find_next_holder_index(idx, queue, st.session_state.skip_flags)
    if nxt_idx != -1:
        next_h = queue[nxt_idx]
        log_status_change(current_holder, 'Bastão', '', datetime.now() - st.session_state.bastao_start_time)
        st.session_state.status_texto[current_holder] = ''
        st.session_state.status_texto[next_h] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        st.session_state.rotation_gif_start_time = datetime.now()
        send_chat_notification_internal(next_h, 'Bastão'); save_state()

def update_status(status_text):
    selected = st.session_state.consultor_selectbox
    if selected == 'Selecione um nome': return
    st.session_state[f'check_{selected}'] = False
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, st.session_state.status_texto.get(selected, ''), status_text, duration)
    st.session_state.status_texto[selected] = status_text
    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    check_and_assume_baton(); save_state()

# ============================================
# 4. INTERFACE STREAMLIT
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()

# Refresh Automático
st_autorefresh(interval=8000, key='auto_refresh')

# Estilo e Cabeçalho
st.markdown(f'<h1 style="color: #FFD700; text-align: center;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>', unsafe_allow_html=True)
st.markdown("<hr style='border: 1px solid #FFD700;'>", unsafe_allow_html=True)

col_principal, col_disponibilidade = st.columns([1.5, 1])

with col_principal:
    responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável Atual")
    if responsavel:
        st.markdown(f'<div style="background: #FFF8DC; border: 3px solid #FFD700; padding: 20px; border-radius: 15px; font-size: 32px; font-weight: bold; color: #000080; text-align: center;">🥂 {responsavel}</div>', unsafe_allow_html=True)
        dur = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        st.caption(f"⏱️ Tempo com o bastão: {format_time_duration(dur)}")
    else: st.subheader("(Ninguém com o bastão)")

    st.markdown("### Selecione seu nome:")
    st.selectbox('Selecione seu nome:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    st.markdown("**Ações:**")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    
    def set_view(v): st.session_state.active_view = v if st.session_state.active_view != v else None

    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    c2.button('⏭️ Pular', on_click=lambda: st.session_state.skip_flags.update({st.session_state.consultor_selectbox: True}) or rotate_bastao(), use_container_width=True)
    c3.button('📋 Atividades', on_click=lambda: set_view('menu_atividades'), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=lambda: update_status('Almoço'), use_container_width=True)
    c5.button('👤 Ausente', on_click=lambda: update_status('Ausente'), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=lambda: set_view('form_sessao'), use_container_width=True)
    c7.button('🚶 Saída', on_click=lambda: update_status('Saída rápida'), use_container_width=True)

    # Menus de Opções
    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            escolhas = st.multiselect("Atividades:", OPCOES_ATIVIDADES_STATUS, placeholder="Escolha as opções")
            detalhe = ""
            if any(x in ATIVIDADES_EXIGEM_DETALHE for x in escolhas):
                detalhe = st.text_input("Tipo/Setor/Descrição (Obrigatório):")
            if st.button("Confirmar", type="primary"):
                if escolhas and (not any(x in ATIVIDADES_EXIGEM_DETALHE for x in escolhas) or detalhe.strip()):
                    status = f"Atividade: {', '.join(escolhas)}" + (f" [{detalhe}]" if detalhe else "")
                    update_status(status); st.session_state.active_view = None; st.rerun()
                else: st.error("Preencha os campos obrigatórios.")

    if st.session_state.active_view == 'form_sessao':
        with st.container(border=True):
            setor = st.text_input("Setor da Sessão (Obrigatório):")
            if st.button("Confirmar Sessão", type="primary"):
                if setor.strip(): update_status(f"Sessão: {setor}"); st.session_state.active_view = None; st.rerun()
                else: st.error("Setor é obrigatório.")

with col_disponibilidade:
    st.header("Status dos Consultores")
    st.toggle("Auxílio HP/Emails/Whatsapp", key='auxilio_ativo', on_change=save_state)
    st.markdown("---")
    
    ui = {'fila': [], 'atv': [], 'ses': [], 'alm': [], 'sai': [], 'aus': []}
    for nome in CONSULTORES:
        status = st.session_state.status_texto.get(nome, 'Ausente')
        if status in ['Bastão', '']: ui['fila'].append(nome)
        elif 'Atividade:' in status: ui['atv'].append((nome, status.replace('Atividade: ', '')))
        elif 'Sessão:' in status: ui['ses'].append((nome, status.replace('Sessão: ', '')))
        elif status == 'Almoço': ui['alm'].append(nome)
        elif status == 'Saída rápida': ui['sai'].append(nome)
        else: ui['aus'].append(nome)

    def render_section(title, items, color, is_tuple=False):
        st.subheader(f"{title} ({len(items)})")
        for item in items:
            nome = item[0] if is_tuple else item
            info = item[1] if is_tuple else title
            c_n, c_c = st.columns([0.7, 0.3])
            c_c.checkbox(" ", key=f"chk_{nome}", value=st.session_state.get(f"check_{nome}"), on_change=update_queue, args=(nome,), label_visibility="collapsed")
            if nome == responsavel: c_n.markdown(f"🥂 **{nome}**")
            else: c_n.markdown(f"**{nome}** :{color}-background[{info}]", unsafe_allow_html=True)
        st.markdown("---")

    render_section("Na Fila", ui['fila'], "blue")
    render_section("Em Atividade", ui['atv'], "orange", True)
    render_section("Sessão", ui['ses'], "green", True)
    render_section("Almoço", ui['alm'], "red")
    render_section("Saída Rápida", ui['sai'], "red")
    render_section("Ausente", ui['aus'], "grey")
