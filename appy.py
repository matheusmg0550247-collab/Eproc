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

PROJETOS_OPCOES = [
    "Soma", "Treinamentos Eproc", "Manuais Eproc", 
    "Cartilhas Gabinetes", "Notebook Lm", "Inteligência artifical cartórios"
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
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k" 
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

# Listas para o formulário de atendimento
REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]

CAMARAS_DICT = {
    "Cartório da 1ª Câmara Cível": "caciv1@tjmg.jus.br", "Cartório da 2ª Câmara Cível": "caciv2@tjmg.jus.br",
    "Cartório da 3ª Câmara Cível": "caciv3@tjmg.jus.br", "Cartório da 4ª Câmara Cível": "caciv4@tjmg.jus.br",
    "Cartório da 5ª Câmara Cível": "caciv5@tjmg.jus.br", "Cartório da 6ª Câmara Cível": "caciv6@tjmg.jus.br",
    "Cartório da 7ª Câmara Cível": "caciv7@tjmg.jus.br", "Cartório da 8ª Câmara Cível": "caciv8@tjmg.jus.br",
    "Cartório da 9ª Câmara Cível": "caciv9@tjmg.jus.br", "Cartório da 10ª Câmara Cível": "caciv10@tjmg.jus.br",
    "Cartório da 11ª Câmara Cível": "caciv11@tjmg.jus.br", "Cartório da 12ª Câmara Cível": "caciv12@tjmg.jus.br",
    "Cartório da 13ª Câmara Cível": "caciv13@tjmg.jus.br", "Cartório da 14ª Câmara Cível": "caciv14@tjmg.jus.br",
    "Cartório da 15ª Câmara Cível": "caciv15@tjmg.jus.br", "Cartório da 16ª Câmara Cível": "caciv16@tjmg.jus.br",
    "Cartório da 17ª Câmara Cível": "caciv17@tjmg.jus.br", "Cartório da 18ª Câmara Cível": "caciv18@tjmg.jus.br",
    "Cartório da 19ª Câmara Cível": "caciv19@tjmg.jus.br", "Cartório da 20ª Câmara Cível": "caciv20@tjmg.jus.br",
    "Cartório da 21ª Câmara Cível": "caciv21@tjmg.jus.br"
}
CAMARAS_OPCOES = sorted(list(CAMARAS_DICT.keys()))

OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"]
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
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f: data = f.read()
        return base64.b64encode(data).decode()
    except: return None

def date_serializer(obj):
    if isinstance(obj, (datetime, date, dt_time)): return obj.isoformat()
    if isinstance(obj, timedelta): return obj.total_seconds()
    return str(obj)

def save_state():
    global_data = get_global_state_cache()
    try:
        for k in ['status_texto', 'bastao_queue', 'skip_flags', 'current_status_starts', 'bastao_counts', 'priority_return_queue', 'bastao_start_time', 'report_last_run_date', 'auxilio_ativo', 'simon_ranking']:
            if k in st.session_state: global_data[k] = st.session_state[k]
        global_data['daily_logs'] = json.loads(json.dumps(st.session_state.daily_logs, default=date_serializer))
    except Exception as e: print(f'Erro ao salvar estado: {e}')

def load_state():
    global_data = get_global_state_cache()
    logs = global_data.get('daily_logs', [])
    final_logs = []
    
    # Tratamento para evitar conversão duplicada (Correção do TypeError)
    for log in logs:
        if isinstance(log, dict):
            if 'duration' in log and not isinstance(log['duration'], timedelta):
                try: log['duration'] = timedelta(seconds=float(log['duration']))
                except: log['duration'] = timedelta(0)
            
            if 'timestamp' in log and isinstance(log['timestamp'], str):
                try: log['timestamp'] = datetime.fromisoformat(log['timestamp'])
                except: log['timestamp'] = datetime.min
            final_logs.append(log)
            
    data = {k: v for k, v in global_data.items() if k != 'daily_logs'}
    data['daily_logs'] = final_logs
    return data

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    entry = {
        'timestamp': datetime.now(),
        'consultor': consultor,
        'old_status': old_status, 
        'new_status': new_status,
        'duration': duration,
    }
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
        msg = {"text": f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Painel:** {APP_URL_CLOUD}"}
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, msg)).start()
        return True
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    if not GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS: return False
    msg = f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n🕐 **Início:** {inicio.strftime('%H:%M')}\n⏱️ **Tempo:** {tempo}\n📝 **Motivo:** {motivo}"
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS, {"text": msg})).start()
    return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira=""):
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO: return False
    j_str = f"\n🔢 **Jira:** CESUPE-{jira}" if jira else ""
    msg = f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n👥 **Usuário:** {usuario}\n🏢 **Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {descricao}\n📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{j_str}"
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_REGISTRO, {"text": msg})).start()
    return True

def render_fireworks():
    fireworks_css = """<style>@keyframes firework {0% { transform: translate(var(--x), var(--initialY)); width: var(--initialSize); opacity: 1; } 50% { width: 0.5vmin; opacity: 1; } 100% { width: var(--finalSize); opacity: 0; }} .firework, .firework::before, .firework::after { --initialSize: 0.5vmin; --finalSize: 45vmin; --particleSize: 0.2vmin; --color1: #ff0000; --color2: #ffd700; --y: -30vmin; --x: -50%; --initialY: 60vmin; content: ""; animation: firework 2s infinite; position: absolute; top: 50%; left: 50%; transform: translate(-50%, var(--y)); width: var(--initialSize); aspect-ratio: 1; background: radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%; background-size: var(--initialSize) var(--initialSize); background-repeat: no-repeat; } .firework:nth-child(2) { --x: 30vmin; left: 30%; top: 60%; } .firework:nth-child(3) { --x: -30vmin; left: 70%; top: 60%; }</style><div class="firework"></div><div class="firework"></div><div class="firework"></div>"""
    st.markdown(fireworks_css, unsafe_allow_html=True)

def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'

def init_session_state():
    data = load_state()
    defaults = {
        'bastao_start_time': None, 'report_last_run_date': datetime.min, 'active_view': None, 
        'simon_status': 'start', 'chamado_guide_step': 0, 'auxilio_ativo': False
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = data.get(k, v)
    
    st.session_state['status_texto'] = data.get('status_texto', {n: 'Indisponível' for n in CONSULTORES}).copy()
    st.session_state['bastao_queue'] = data.get('bastao_queue', []).copy()
    st.session_state['skip_flags'] = data.get('skip_flags', {}).copy()
    st.session_state['priority_return_queue'] = data.get('priority_return_queue', []).copy()
    st.session_state['current_status_starts'] = data.get('current_status_starts', {n: datetime.now() for n in CONSULTORES}).copy()
    st.session_state['bastao_counts'] = data.get('bastao_counts', {n: 0 for n in CONSULTORES}).copy()
    st.session_state['daily_logs'] = data.get('daily_logs', []).copy()
    st.session_state['simon_ranking'] = data.get('simon_ranking', []).copy()

    for n in CONSULTORES:
        st.session_state.setdefault(f'check_{n}', (st.session_state.status_texto.get(n) in ['', 'Bastão']))

def check_and_assume_baton():
    q = st.session_state.bastao_queue; skips = st.session_state.skip_flags
    curr_h = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    eligible = [c for c in q if not skips.get(c) and st.session_state.get(f'check_{c}')]
    
    should = curr_h if (curr_h and curr_h in eligible) else (eligible[0] if eligible else None)
    changed = False

    for c in CONSULTORES:
        if st.session_state.status_texto.get(c) == 'Bastão' and c != should:
            duration = datetime.now() - st.session_state.current_status_starts.get(c, datetime.now())
            log_status_change(c, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[c] = 'Indisponível'; changed = True

    if should and st.session_state.status_texto.get(should) != 'Bastão':
        old = st.session_state.status_texto.get(should, '')
        log_status_change(should, old, 'Bastão', timedelta(0))
        st.session_state.status_texto[should] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        st.session_state.play_sound = True; send_chat_notification_internal(should, 'Bastão'); changed = True
    
    if changed: save_state()
    return changed

def rotate_bastao():
    sel = st.session_state.consultor_selectbox
    cur = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if sel != cur: st.session_state.gif_warning = True; return
    
    q = st.session_state.bastao_queue; skips = st.session_state.skip_flags
    idx = q.index(cur) if cur in q else -1
    nxt_idx = -1
    for i in range(1, len(q) + 1):
        t_idx = (idx + i) % len(q)
        if not skips.get(q[t_idx]) and st.session_state.get(f'check_{q[t_idx]}'): nxt_idx = t_idx; break
            
    if nxt_idx != -1:
        nxt = q[nxt_idx]
        log_status_change(cur, 'Bastão', '', datetime.now() - st.session_state.bastao_start_time)
        st.session_state.status_texto[cur] = ''; st.session_state.status_texto[nxt] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now(); st.session_state.rotation_gif_start_time = datetime.now()
        st.session_state.play_sound = True; send_chat_notification_internal(nxt, 'Bastão'); save_state()

def update_status(status):
    sel = st.session_state.consultor_selectbox
    if not sel or sel == 'Selecione um nome': return
    st.session_state[f'check_{sel}'] = False
    was = (st.session_state.status_texto.get(sel) == 'Bastão')
    log_status_change(sel, st.session_state.status_texto.get(sel, ''), status, timedelta(0))
    st.session_state.status_texto[sel] = status
    if sel in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(sel)
    if status == 'Saída rápida': st.session_state.priority_return_queue.append(sel)
    if was: check_and_assume_baton()
    else: save_state()

def update_queue(name):
    st.session_state.status_texto[name] = '' if st.session_state[f'check_{name}'] else 'Indisponível'
    if st.session_state[f'check_{name}']:
        if name not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(name)
        if name in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(name)
    else:
        if name in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(name)
    check_and_assume_baton()

# ============================================
# 3. INTERFACE PRINCIPAL
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
render_fireworks()

# --- Topo ---
c_top1, c_top2 = st.columns([2, 1], vertical_alignment="bottom")
with c_top1:
    img_data = get_img_as_base64(PUG2026_FILENAME); src = f"data:image/png;base64,{img_data}" if img_data else GIF_BASTAO_HOLDER
    st.markdown(f'<div style="display: flex; align-items: center; gap: 15px;"><h1 style="color: #FFD700;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{src}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;"></div>', unsafe_allow_html=True)

with c_top2:
    # Botão rápido de entrada
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_sub1: novo_responsavel = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
    with c_sub2:
        if st.button("🚀 Entrar"):
            if novo_responsavel and novo_responsavel != "Selecione":
                st.session_state[f'check_{novo_responsavel}'] = True; update_queue(novo_responsavel); st.session_state.consultor_selectbox = novo_responsavel; st.success("Na fila!"); st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

st_autorefresh(interval=8000, key='refresh')
if st.session_state.get('play_sound'): st.components.v1.html(play_sound_html(), height=0); st.session_state.play_sound = False
if st.session_state.get('rotation_gif_start_time') and (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 20:
    st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')
if st.session_state.get('gif_warning'): st.error('🚫 Ação inválida!'); st.image(GIF_URL_WARNING, width=150)

col_main, col_side = st.columns([1.5, 1])

with col_main:
    resp = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if resp:
        st.markdown(f'<div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%); border: 3px solid #FFD700; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255,215,0,0.3);"><img src="{GIF_BASTAO_HOLDER}" style="width: 80px; height: 80px; border-radius: 50%; margin-right: 20px;"><div><span style="font-size: 14px; font-weight: bold;">COM O BASTÃO:</span><br><span style="font-size: 38px; font-weight: 800; color: #000080;">{resp}</span></div></div>', unsafe_allow_html=True)
        dur = datetime.now() - st.session_state.bastao_start_time if st.session_state.bastao_start_time else timedelta(0)
        st.caption(f"⏱️ Tempo: {format_time_duration(dur)}")

    st.header("Ações do Consultor")
    st.selectbox('Selecione seu nome:', ['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    # Grid de Ações (8 colunas - INCLUINDO PROJETOS)
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    c2.button('⏭️ Pular', on_click=lambda: setattr(st.session_state, 'skip_flags', {**st.session_state.skip_flags, st.session_state.consultor_selectbox: True}), use_container_width=True)
    c3.button('📋 Ativ.', on_click=lambda: setattr(st.session_state, 'active_view', 'menu_atividades'), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=lambda: update_status('Almoço'), use_container_width=True)
    c5.button('👤 Ausent', on_click=lambda: update_status('Ausente'), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=lambda: update_status('Sessão'), use_container_width=True)
    c7.button('🚶 Saída', on_click=lambda: update_status('Saída rápida'), use_container_width=True)
    c8.button('🚀 Projeto', on_click=lambda: setattr(st.session_state, 'active_view', 'menu_projetos'), use_container_width=True)

    st.markdown("---")
    # Grid de Ferramentas (5 colunas - SEM Erro/Novidade)
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.button("📑 Checklist", on_click=lambda: setattr(st.session_state, 'active_view', 'checklist'), use_container_width=True)
    t2.button("🆘 Chamados", on_click=lambda: setattr(st.session_state, 'active_view', 'chamados'), use_container_width=True)
    t3.button("📝 Atend.", on_click=lambda: setattr(st.session_state, 'active_view', 'atendimentos'), use_container_width=True)
    t4.button("⏰ H.Extras", on_click=lambda: setattr(st.session_state, 'active_view', 'hextras'), use_container_width=True)
    t5.button("🧠 Descanso", on_click=lambda: setattr(st.session_state, 'active_view', 'descanso'), use_container_width=True)

    # --- RENDERIZAÇÃO DAS TELAS ---
    if st.session_state.active_view == 'menu_projetos':
        with st.container(border=True):
            st.subheader("🚀 Projetos")
            p_sel = st.selectbox("Selecione o Projeto:", PROJETOS_OPCOES)
            if st.button("Confirmar Projeto"): update_status(f"Projeto: {p_sel}"); st.session_state.active_view = None; st.rerun()

    elif st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            st.subheader("📋 Atividades")
            ats = st.multiselect("Selecione:", OPCOES_ATIVIDADES_STATUS)
            if st.button("Confirmar"): update_status(f"Atividade: {', '.join(ats)}"); st.session_state.active_view = None; st.rerun()

    elif st.session_state.active_view == 'descanso':
        with st.container(border=True):
            # SIMON GAME
            COLORS = ["🔴", "🔵", "🟢", "🟡"]
            st.markdown("### 🧠 Simon Game"); st.caption("Repita a sequência!")
            if st.session_state.simon_status == 'start':
                if st.button("▶️ Iniciar Jogo", use_container_width=True):
                    st.session_state.simon_sequence = [random.choice(COLORS)]; st.session_state.simon_user_input = []; st.session_state.simon_level = 1; st.session_state.simon_status = 'showing'; st.rerun()
            elif st.session_state.simon_status == 'showing':
                st.info(f"Nível {st.session_state.simon_level}: Memorize!"); cols = st.columns(len(st.session_state.simon_sequence))
                for i, color in enumerate(st.session_state.simon_sequence):
                    with cols[i]: st.markdown(f"<h1 style='text-align: center;'>{color}</h1>", unsafe_allow_html=True)
                if st.button("🙈 Responder", type="primary", use_container_width=True): st.session_state.simon_status = 'playing'; st.rerun()
            elif st.session_state.simon_status == 'playing':
                st.markdown(f"**Nível {st.session_state.simon_level}**"); c1, c2, c3, c4 = st.columns(4); pressed = None
                if c1.button("🔴", use_container_width=True): pressed = "🔴"
                if c2.button("🔵", use_container_width=True): pressed = "🔵"
                if c3.button("🟢", use_container_width=True): pressed = "🟢"
                if c4.button("🟡", use_container_width=True): pressed = "🟡"
                if pressed:
                    st.session_state.simon_user_input.append(pressed); current_idx = len(st.session_state.simon_user_input) - 1
                    if st.session_state.simon_user_input[current_idx] != st.session_state.simon_sequence[current_idx]: st.session_state.simon_status = 'lost'; st.rerun()
                    elif len(st.session_state.simon_user_input) == len(st.session_state.simon_sequence):
                        st.success("Correto!"); time.sleep(0.5); st.session_state.simon_sequence.append(random.choice(COLORS)); st.session_state.simon_user_input = []; st.session_state.simon_level += 1; st.session_state.simon_status = 'showing'; st.rerun()
                if st.session_state.simon_user_input: st.markdown(f"Resposta: {' '.join(st.session_state.simon_user_input)}")
            elif st.session_state.simon_status == 'lost':
                st.error(f"❌ Nível {st.session_state.simon_level}"); st.markdown(f"Correto: {' '.join(st.session_state.simon_sequence)}")
                consultor = st.session_state.consultor_selectbox
                if consultor and consultor != 'Selecione um nome':
                    score = st.session_state.simon_level; ranking = st.session_state.simon_ranking; found = False
                    for entry in ranking:
                        if entry['nome'] == consultor:
                            if score > entry['score']: entry['score'] = score
                            found = True; break
                    if not found: ranking.append({'nome': consultor, 'score': score})
                    st.session_state.simon_ranking = sorted(ranking, key=lambda x: x['score'], reverse=True)[:5]; save_state()
                if st.button("Tentar Novamente"): st.session_state.simon_status = 'start'; st.rerun()
            st.markdown("---"); st.subheader("🏆 Ranking Global"); ranking = st.session_state.simon_ranking
            if not ranking: st.markdown("_Sem recordes._")
            else: st.table(pd.DataFrame(ranking))

    elif st.session_state.active_view == 'checklist':
        with st.container(border=True):
            st.header("Gerador Checklist"); data_ep = st.date_input("Data Sessão:"); cam_ep = st.selectbox("Câmara:", CAMARAS_OPCOES)
            if st.button("Gerar/Enviar"):
                # Simplificação da função handle_sessao para caber no bloco
                if st.session_state.consultor_selectbox != 'Selecione um nome':
                     df = data_ep.strftime("%d/%m/%Y"); dfa = data_ep.strftime("%d-%m-%Y")
                     msg = f"Sessão {cam_ep} dia {df}."
                     threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_SESSAO, {'text': msg})).start()
                     st.session_state.html_content_cache = f"<html>Checklist {df}</html>"; st.session_state.html_download_ready = True
                     st.download_button("Baixar HTML", st.session_state.html_content_cache, f"Checklist_{dfa}.html", "text/html")

    elif st.session_state.active_view == 'chamados':
        with st.container(border=True):
             st.subheader("Guia Chamados"); st.info("Siga os passos padronizados."); st.text_area("Rascunho:"); st.button("Simular Envio")
             
    elif st.session_state.active_view == 'atendimentos':
        with st.container(border=True):
            st.markdown("### Novo Atendimento"); at_u = st.selectbox("Usuário:", REG_USUARIO_OPCOES); at_s = st.text_input("Setor:"); at_sys = st.selectbox("Sistema:", REG_SISTEMA_OPCOES); at_desc = st.text_input("Descrição:"); at_c = st.selectbox("Canal:", REG_CANAL_OPCOES); at_d = st.selectbox("Desfecho:", REG_DESFECHO_OPCOES); at_j = st.text_input("Jira:")
            if st.button("Enviar"): send_atendimento_to_chat(st.session_state.consultor_selectbox, date.today(), at_u, at_s, at_sys, at_desc, at_c, at_d, at_j); st.success("Enviado!"); st.session_state.active_view=None; st.rerun()

    elif st.session_state.active_view == 'hextras':
        with st.container(border=True):
            st.markdown("### Horas Extras"); he_d = st.date_input("Data:"); he_i = st.time_input("Início:"); he_t = st.text_input("Tempo Total:"); he_m = st.text_input("Motivo:")
            if st.button("Enviar"): send_horas_extras_to_chat(st.session_state.consultor_selectbox, he_d, he_i, he_t, he_m); st.success("Enviado!"); st.session_state.active_view=None; st.rerun()

with col_side:
    st.header("Status da Equipe")
    ui = {'fila': [], 'projeto': [], 'atividade': [], 'outros': []}
    for n in CONSULTORES:
        s = st.session_state.status_texto.get(n, 'Indisponível')
        if s in ['', 'Bastão']: ui['fila'].append(n)
        elif 'Projeto:' in s: ui['projeto'].append((n, s.replace('Projeto: ', '')))
        elif 'Atividade:' in s: ui['atividade'].append((n, s.replace('Atividade: ', '')))
        else: ui['outros'].append((n, s))

    st.subheader(f"✅ Fila ({len(ui['fila'])})")
    for n in ui['fila']:
        cn, cc = st.columns([0.8, 0.2]); cc.checkbox(' ', key=f'check_{n}', on_change=update_queue, args=(n,), label_visibility='collapsed')
        if st.session_state.status_texto.get(n) == 'Bastão': cn.markdown(f"🥂 **{n}**")
        else: cn.markdown(n)

    st.markdown("---")
    st.subheader(f"🚀 Projetos ({len(ui['projeto'])})")
    for n, p in ui['projeto']: st.markdown(f"**{n}** :blue-background[{p}]")

    st.markdown("---")
    st.subheader(f"📋 Atividades ({len(ui['atividade'])})")
    for n, a in ui['atividade']: st.markdown(f"**{n}** :orange-background[{a}]")
    
    st.markdown("---")
    st.subheader(f"📌 Outros ({len(ui['outros'])})")
    for n, s in ui['outros']: st.markdown(f"**{n}** :grey-background[{s}]")

now_br = datetime.utcnow() - timedelta(hours=3)
if now_br.hour >= 20 and now_br.date() > (st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()):
    send_daily_report()
