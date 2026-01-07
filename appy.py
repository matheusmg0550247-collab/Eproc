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

# --- FUNÇÃO DE CACHE GLOBAL ---
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

# --- Constantes (Webhooks) ---
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQA5CyNolU/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zolqmc0YfJ5bPzsqLrefwn8yBbNQLLfFBzLTwIkr7W4" 
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

OPCOES_ATIVIDADES_STATUS = [
    "HP", "E-mail", "Whatsapp/Plantão", 
    "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"
]
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
GIF_URL_LUNCH_WARNING = 'https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGZlbHN1azB3b2drdTI1eG10cDEzeWpmcmtwenZxNTV0bnc2OWgzZSYlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/bNlqpmBJRDMpxulfFB/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
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
    except: return None

def save_state():
    global_data = get_global_state_cache()
    try:
        global_data['status_texto'] = st.session_state.status_texto.copy()
        global_data['bastao_queue'] = st.session_state.bastao_queue.copy()
        global_data['skip_flags'] = st.session_state.skip_flags.copy()
        global_data['current_status_starts'] = st.session_state.current_status_starts.copy()
        global_data['bastao_counts'] = st.session_state.bastao_counts.copy()
        global_data['priority_return_queue'] = st.session_state.priority_return_queue.copy()
        global_data['bastao_start_time'] = st.session_state.bastao_start_time
        global_data['report_last_run_date'] = st.session_state.report_last_run_date
        global_data['rotation_gif_start_time'] = st.session_state.get('rotation_gif_start_time')
        global_data['lunch_warning_info'] = st.session_state.get('lunch_warning_info')
        global_data['auxilio_ativo'] = st.session_state.get('auxilio_ativo', False) 
        global_data['daily_logs'] = st.session_state.daily_logs.copy()
        if 'simon_ranking' in st.session_state: global_data['simon_ranking'] = st.session_state.simon_ranking.copy()
    except: pass

def load_state():
    return get_global_state_cache()

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    entry = {'timestamp': datetime.now(), 'consultor': consultor, 'old_status': old_status, 'new_status': new_status, 'duration': duration}
    st.session_state.daily_logs.append(entry)
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def _send_webhook_thread(url, payload):
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        msg = {"text": f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {APP_URL_CLOUD}"}
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, msg)).start()
    return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira=""):
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO: return False
    jira_str = f"\n🔢 **Jira:** CESUPE-{jira}" if jira else ""
    msg = {"text": f"📋 **Novo Registro**\n\n👤 **Consultor:** {consultor}\n🏢 **Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Desc:** {descricao}{jira_str}"}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_REGISTRO, msg)).start()
    return True

def render_fireworks():
    fireworks_css = """<style>@keyframes firework {0% { transform: translate(var(--x), var(--initialY)); width: var(--initialSize); opacity: 1; } 50% { width: 0.5vmin; opacity: 1; } 100% { width: var(--finalSize); opacity: 0; }} .firework, .firework::before, .firework::after { --initialSize: 0.5vmin; --finalSize: 45vmin; --particleSize: 0.2vmin; --color1: #ff0000; --color2: #ffd700; --y: -30vmin; --x: -50%; --initialY: 60vmin; content: ""; animation: firework 2s infinite; position: absolute; top: 50%; left: 50%; transform: translate(-50%, var(--y)); width: var(--initialSize); aspect-ratio: 1; background: radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%; background-size: var(--initialSize) var(--initialSize); background-repeat: no-repeat; }</style><div class="firework"></div>"""
    st.markdown(fireworks_css, unsafe_allow_html=True)

# ============================================
# 3. LÓGICA DO BASTÃO
# ============================================

def init_session_state():
    state = load_state()
    for key, val in state.items():
        if key not in st.session_state: st.session_state[key] = val
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0)
        st.session_state.skip_flags.setdefault(nome, False)
        status = st.session_state.status_texto.get(nome, 'Ausente')
        st.session_state[f'check_{nome}'] = (status == 'Bastão' or status == '')
    check_and_assume_baton()

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
        log_status_change(should_have, st.session_state.status_texto.get(should_have, ''), 'Bastão', timedelta(0))
        st.session_state.status_texto[should_have] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        send_chat_notification_internal(should_have, 'Bastão'); changed = True
    if changed: save_state()

def update_queue(consultor):
    is_checked = st.session_state.get(f'check_{consultor}')
    old_status = st.session_state.status_texto.get(consultor, '')
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())
    if is_checked:
        log_status_change(consultor, old_status, '', duration)
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    else:
        # CORREÇÃO: Ao desmarcar, leva para 'Ausente'
        if old_status not in STATUSES_DE_SAIDA or old_status == '':
             log_status_change(consultor, old_status, 'Ausente', duration)
             st.session_state.status_texto[consultor] = 'Ausente'
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
        st.session_state.skip_flags.pop(consultor, None)
    check_and_assume_baton(); save_state()

def rotate_bastao():
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': return
    queue = st.session_state.bastao_queue; current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder: st.session_state.gif_warning = True; return
    try: idx = queue.index(current_holder)
    except: return
    nxt_idx = find_next_holder_index(idx, queue, st.session_state.skip_flags)
    if nxt_idx != -1:
        next_h = queue[nxt_idx]
        log_status_change(current_holder, 'Bastão', '', datetime.now() - st.session_state.bastao_start_time)
        st.session_state.status_texto[current_holder] = ''
        log_status_change(next_h, '', 'Bastão', timedelta(0))
        st.session_state.status_texto[next_h] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        st.session_state.rotation_gif_start_time = datetime.now(); send_chat_notification_internal(next_h, 'Bastão'); save_state()

def update_status(status_text):
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': return
    st.session_state[f'check_{selected}'] = False
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, st.session_state.status_texto.get(selected, ''), status_text, duration)
    st.session_state.status_texto[selected] = status_text
    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    check_and_assume_baton(); save_state()

# ============================================
# 4. INTERFACE
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
render_fireworks()

c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img_data = get_img_as_base64(PUG2026_FILENAME)
    img_src = f"data:image/png;base64,{img_data}" if img_data else GIF_BASTAO_HOLDER
    st.markdown(f'<div style="display: flex; align-items: center; gap: 15px;"><h1 style="color: #FFD700;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>'
                f'<img src="{img_src}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700;"></div>', unsafe_allow_html=True)
with c_topo_dir:
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    novo_resp = c_sub1.selectbox("Entrar na Fila", options=["Selecione"] + CONSULTORES, label_visibility="collapsed")
    if c_sub2.button("🚀 Entrar"):
        if novo_resp != "Selecione": st.session_state[f'check_{novo_resp}'] = True; update_queue(novo_resp); st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700;'>", unsafe_allow_html=True)
st_autorefresh(interval=8000, key='auto_rerun')

col_principal, col_disponibilidade = st.columns([1.5, 1])
queue = st.session_state.bastao_queue; responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)

with col_principal:
    st.header("Responsável Atual")
    if responsavel:
        st.markdown(f'<div style="background: #FFF8DC; border: 3px solid #FFD700; padding: 20px; border-radius: 15px; font-size: 32px; font-weight: bold; color: #000080;">🥂 {responsavel}</div>', unsafe_allow_html=True)
        st.caption(f"⏱️ Tempo: {format_time_duration(datetime.now() - (st.session_state.bastao_start_time or datetime.now()))}")
    else: st.subheader("(Ninguém com o bastão)")
    
    st.markdown("### Consultor(a)")
    st.selectbox('Selecione seu nome:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    def toggle_view(v): st.session_state.active_view = None if st.session_state.active_view == v else v

    st.markdown("**Ações:**")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    c2.button('⏭️ Pular', on_click=lambda: st.session_state.skip_flags.update({st.session_state.consultor_selectbox: True}) or rotate_bastao(), use_container_width=True)
    c3.button('📋 Atividades', on_click=lambda: toggle_view('menu_atividades'), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=lambda: update_status('Almoço'), use_container_width=True)
    c5.button('👤 Ausente', on_click=lambda: update_status('Ausente'), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=lambda: toggle_view('form_sessao'), use_container_width=True)
    c7.button('🚶 Saída', on_click=lambda: update_status('Saída rápida'), use_container_width=True)

    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            st.markdown("### Selecione a Atividade")
            escolhas = st.multiselect("Escolha as opções:", OPCOES_ATIVIDADES_STATUS, placeholder="Escolha as opções")
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
            st.markdown("### Registrar Sessão")
            setor = st.text_input("Setor (Obrigatório):")
            if st.button("Confirmar Sessão", type="primary"):
                if setor.strip(): update_status(f"Sessão: {setor}"); st.session_state.active_view = None; st.rerun()

with col_disponibilidade:
    st.header("Status dos Consultores")
    st.toggle("Auxílio HP/Emails/Whatsapp", key='auxilio_ativo', on_change=save_state)
    st.markdown("---")
    
    ui_lists = {'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade': [], 'sessao': []}
    for nome in CONSULTORES:
        status = st.session_state.status_texto.get(nome, 'Ausente')
        if status in ['Bastão', '']: ui_lists['fila'].append(nome)
        elif 'Atividade:' in status: ui_lists['atividade'].append((nome, status.replace('Atividade: ', '')))
        elif 'Sessão:' in status: ui_lists['sessao'].append((nome, status.replace('Sessão: ', '')))
        elif status == 'Almoço': ui_lists['almoco'].append(nome)
        elif status == 'Saída rápida': ui_lists['saida'].append(nome)
        elif status == 'Ausente': ui_lists['ausente'].append(nome)

    def render_list(title, items, color, is_tuple=False):
        st.subheader(f"{title} ({len(items)})")
        for item in items:
            nome = item[0] if is_tuple else item; info = item[1] if is_tuple else title
            c_n, c_c = st.columns([0.7, 0.3])
            c_c.checkbox(" ", key=f"chk_{nome}", value=st.session_state.get(f"check_{nome}"), on_change=update_queue, args=(nome,), label_visibility="collapsed")
            if nome == responsavel: c_n.markdown(f"🥂 **{nome}**")
            else: c_n.markdown(f"**{nome}** :{color}-background[{info}]", unsafe_allow_html=True)

    render_list("Na Fila", ui_lists['fila'], "blue")
    render_list("Em Atividade", ui_lists['atividade'], "orange", True)
    render_list("Sessão", ui_lists['sessao'], "green", True)
    render_list("Almoço", ui_lists['almoco'], "red")
    render_list("Saída Rápida", ui_lists['saida'], "red")
    render_list("Ausente", ui_lists['ausente'], "grey")
