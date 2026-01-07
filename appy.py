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
    "Alex Paulo da Silva", "Dirceu Gonçalves Siqueira Neto", "Douglas de Souza Gonçalves",
    "Farley Leandro de Oliveira Juliano", "Gleis da Silva Rodrigues", "Hugo Leonardo Murta",
    "Igor Dayrell Gonçalves Correa", "Jerry Marcos dos Santos Neto", "Jonatas Gomes Saraiva",
    "Leandro Victor Catharino", "Luiz Henrique Barros Oliveira", "Marcelo dos Santos Dutra",
    "Marina Silva Marques", "Marina Torres do Amaral", "Vanessa Ligiane Pimenta Santos"
])

# --- FUNÇÃO DE CACHE GLOBAL (Persistência entre todos os usuários) ---
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

# Listas de Opções
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

OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "Whatsapp/Plantão", "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"]
ATIVIDADES_EXIGEM_DETALHE = ["Treinamento", "Homologação", "Redação Documentos", "Outros"]

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

def date_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    if isinstance(obj, timedelta): return obj.total_seconds()
    if isinstance(obj, (date, dt_time)): return obj.isoformat()
    return str(obj)

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
        global_data['daily_logs'] = json.loads(json.dumps(st.session_state.daily_logs, default=date_serializer))
        if 'simon_ranking' in st.session_state: global_data['simon_ranking'] = st.session_state.simon_ranking.copy()
    except: pass

def load_state():
    global_data = get_global_state_cache()
    logs = global_data.get('daily_logs', [])
    final_logs = []
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
    st.session_state.daily_logs.append({
        'timestamp': datetime.now(), 'consultor': consultor, 'old_status': old_status, 
        'new_status': new_status, 'duration': duration, 'duration_s': duration.total_seconds()
    })
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

def send_atendimento_to_chat(consultor, data, usuario, setor, sistema, desc, canal, desf, jira=""):
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO: return False
    j_str = f"\n🔢 **Jira:** CESUPE-{jira}" if jira else ""
    msg = {"text": f"📋 **Registro**\n👤 **Resp:** {consultor}\n👥 **Usuário:** {usuario}\n🏢 **Setor:** {setor}\n💻 **Sist:** {sistema}\n📝 **Desc:** {desc}\n📞 **Canal:** {canal}\n✅ **Desf:** {desf}{j_str}"}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_REGISTRO, msg)).start()
    return True

def send_daily_report(): 
    logs = st.session_state.daily_logs; counts = st.session_state.bastao_counts.copy()
    agg = {n: {} for n in CONSULTORES}
    for l in logs:
        try:
            c = l['consultor']; s = l['old_status']; d = l.get('duration', timedelta(0))
            if s and c in agg: agg[c][s] = agg[c].get(s, timedelta(0)) + d
        except: pass
    rep = f"📊 **Relatório Diário - {datetime.now().strftime('%d/%m/%Y')}** 📊\n\n"
    for n in CONSULTORES:
        if counts.get(n, 0) > 0 or agg.get(n):
            rep += f"**👤 {n}**\n- Bastão: {counts.get(n,0)}x | Tempo: {format_time_duration(agg[n].get('Bastão', timedelta(0)))}\n"
    if GOOGLE_CHAT_WEBHOOK_BACKUP: threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_BACKUP, {'text': rep})).start()
    st.session_state.daily_logs = []; st.session_state.bastao_counts = {nome: 0 for nome in CONSULTORES}; save_state()

def render_fireworks():
    css = """<style>@keyframes firework {0% { transform: translate(var(--x), var(--initialY)); width: var(--initialSize); opacity: 1; } 50% { width: 0.5vmin; opacity: 1; } 100% { width: var(--finalSize); opacity: 0; }} .firework, .firework::before, .firework::after { --initialSize: 0.5vmin; --finalSize: 45vmin; --particleSize: 0.2vmin; --color1: #ff0000; --color2: #ffd700; --y: -30vmin; --x: -50%; --initialY: 60vmin; content: ""; animation: firework 2s infinite; position: absolute; top: 50%; left: 50%; transform: translate(-50%, var(--y)); width: var(--initialSize); aspect-ratio: 1; background: radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%; background-size: var(--initialSize) var(--initialSize); background-repeat: no-repeat; }</style><div class="firework"></div><div class="firework"></div>"""
    st.markdown(css, unsafe_allow_html=True)

# ============================================
# 3. LÓGICA DO BASTÃO E FILA
# ============================================

def init_session_state():
    p = load_state()
    defaults = {
        'active_view': None, 'play_sound': False, 'gif_warning': False, 'chamado_guide_step': 0,
        'html_download_ready': False, 'html_content_cache': "", 'last_jira_number': "",
        'simon_status': 'start', 'simon_sequence': [], 'simon_user_input': []
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v
    
    # Sincronização Global
    keys = ['status_texto', 'bastao_queue', 'skip_flags', 'current_status_starts', 'bastao_counts', 'priority_return_queue', 'bastao_start_time', 'report_last_run_date', 'daily_logs', 'auxilio_ativo', 'simon_ranking']
    for k in keys: st.session_state[k] = p.get(k, [] if 'logs' in k or 'queue' in k or 'ranking' in k else {})

    for n in CONSULTORES:
        st.session_state.bastao_counts.setdefault(n, 0); st.session_state.skip_flags.setdefault(n, False)
        status = st.session_state.status_texto.get(n, 'Ausente')
        st.session_state[f'check_{n}'] = (status == 'Bastão' or status == '')
        if n not in st.session_state.current_status_starts: st.session_state.current_status_starts[n] = datetime.now()
    check_and_assume_baton()

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    num = len(queue); next_idx = (current_index + 1) % num
    for _ in range(num):
        c = queue[next_idx]
        if not skips.get(c, False) and st.session_state.get(f'check_{c}'): return next_idx
        next_idx = (next_idx + 1) % num
    return -1

def check_and_assume_baton():
    q = st.session_state.bastao_queue; s = st.session_state.skip_flags
    curr = next((c for c, stt in st.session_state.status_texto.items() if stt == 'Bastão'), None)
    is_v = (curr and curr in q and st.session_state.get(f'check_{curr}'))
    f_idx = find_next_holder_index(-1, q, s)
    should = curr if is_v else (q[f_idx] if f_idx != -1 else None)
    
    chg = False
    for c in CONSULTORES:
        if c != should and st.session_state.status_texto.get(c) == 'Bastão':
            log_status_change(c, 'Bastão', 'Ausente', datetime.now() - st.session_state.current_status_starts.get(c, datetime.now()))
            st.session_state.status_texto[c] = 'Ausente'; chg = True
    if should and st.session_state.status_texto.get(should) != 'Bastão':
        st.session_state.status_texto[should] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        send_chat_notification_internal(should, 'Bastão'); chg = True
    if chg: save_state()

def update_queue(consultor):
    chk = st.session_state.get(f'check_{consultor}')
    old = st.session_state.status_texto.get(consultor, 'Ausente')
    dur = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())
    if chk:
        log_status_change(consultor, old or 'Ausente', '', dur)
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    else:
        # CORREÇÃO: Leva para 'Ausente' ao desmarcar
        log_status_change(consultor, old, 'Ausente', dur)
        st.session_state.status_texto[consultor] = 'Ausente'
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
        st.session_state.skip_flags.pop(consultor, None)
    check_and_assume_baton(); save_state()

def rotate_bastao():
    sel = st.session_state.consultor_selectbox
    if sel == 'Selecione um nome': return
    curr = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if sel != curr: st.session_state.gif_warning = True; return
    q = st.session_state.bastao_queue
    try: i = q.index(curr)
    except: return
    nxt = find_next_holder_index(i, q, st.session_state.skip_flags)
    if nxt != -1:
        nh = q[nxt]; log_status_change(curr, 'Bastão', '', datetime.now() - st.session_state.bastao_start_time)
        st.session_state.status_texto[curr] = ''; st.session_state.status_texto[nh] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now(); st.session_state.bastao_counts[curr] += 1
        st.session_state.rotation_gif_start_time = datetime.now(); send_chat_notification_internal(nh, 'Bastão'); save_state()

def update_status(stt_txt):
    sel = st.session_state.consultor_selectbox
    if sel == 'Selecione um nome': return
    st.session_state[f'check_{sel}'] = False
    log_status_change(sel, st.session_state.status_texto.get(sel, ''), stt_txt, datetime.now() - st.session_state.current_status_starts.get(sel, datetime.now()))
    st.session_state.status_texto[sel] = stt_txt
    if sel in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(sel)
    check_and_assume_baton(); save_state()

# ============================================
# 4. INTERFACE E COMPONENTES
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
render_fireworks()
st_autorefresh(interval=8000, key='auto_ref')

# Cabeçalho
c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img_data = get_img_as_base64(PUG2026_FILENAME)
    img_src = f"data:image/png;base64,{img_data}" if img_data else GIF_BASTAO_HOLDER
    st.markdown(f'<div style="display: flex; align-items: center; gap: 15px;"><h1 style="color: #FFD700;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>'
                f'<img src="{img_src}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700;"></div>', unsafe_allow_html=True)
with c_topo_dir:
    novo_r = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed")
    if st.button("🚀 Entrar"):
        if novo_r != "Selecione": st.session_state[f'check_{novo_r}'] = True; update_queue(novo_r); st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700;'>", unsafe_allow_html=True)

col_principal, col_disponibilidade = st.columns([1.5, 1])

with col_principal:
    responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável Atual")
    if responsavel:
        st.markdown(f'<div style="background: #FFF8DC; border: 3px solid #FFD700; padding: 25px; border-radius: 15px; font-size: 32px; font-weight: bold; color: #000080; text-align: center;">🥂 {responsavel}</div>', unsafe_allow_html=True)
        st.caption(f"⏱️ Tempo: {format_time_duration(datetime.now() - (st.session_state.bastao_start_time or datetime.now()))}")
    else: st.subheader("(Ninguém com o bastão)")

    st.markdown("### Consultor(a)")
    st.selectbox('Selecione seu nome:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    st.markdown("**Ações:**")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    def v(name): st.session_state.active_view = name if st.session_state.active_view != name else None

    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    c2.button('⏭️ Pular', on_click=lambda: st.session_state.skip_flags.update({st.session_state.consultor_selectbox: True}) or rotate_bastao(), use_container_width=True)
    c3.button('📋 Atividades', on_click=lambda: v('atividades'), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=lambda: update_status('Almoço'), use_container_width=True)
    c5.button('👤 Ausente', on_click=lambda: update_status('Ausente'), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=lambda: v('sessao'), use_container_width=True)
    c7.button('🚶 Saída', on_click=lambda: update_status('Saída rápida'), use_container_width=True)

    # Sub-menus
    if st.session_state.active_view == 'atividades':
        with st.container(border=True):
            st.markdown("### Registrar Atividades")
            esc = st.multiselect("Escolha as opções:", OPCOES_ATIVIDADES_STATUS, placeholder="Escolha as opções")
            det = ""
            if any(x in ATIVIDADES_EXIGEM_DETALHE for x in esc):
                det = st.text_input("Tipo/Setor/Descrição (Obrigatório):")
            if st.button("Confirmar", type="primary"):
                if esc and (not any(x in ATIVIDADES_EXIGEM_DETALHE for x in esc) or det.strip()):
                    txt = f"Atividade: {', '.join(esc)}" + (f" [{det}]" if det else "")
                    update_status(txt); st.session_state.active_view = None; st.rerun()
                else: st.error("Preencha os campos obrigatórios.")

    if st.session_state.active_view == 'sessao':
        with st.container(border=True):
            st.markdown("### Registrar Sessão")
            setor_s = st.text_input("Setor (Obrigatório):")
            if st.button("Confirmar Sessão", type="primary"):
                if setor_s.strip(): update_status(f"Sessão: {setor_s}"); st.session_state.active_view = None; st.rerun()
                else: st.error("O Setor é obrigatório.")

    st.markdown("---")
    # Imagem 2: Ferramentas
    c_t1, c_t2, c_t3, c_t4, c_t5 = st.columns(5)
    c_t1.button("📑 Checklist", use_container_width=True, on_click=lambda: v('checklist'))
    c_t2.button("🆘 Chamados", use_container_width=True, on_click=lambda: v('chamados'))
    c_t3.button("📝 Atendimento", use_container_width=True, on_click=lambda: v('reg_atendimento'))
    c_t4.button("⏰ H. Extras", use_container_width=True, on_click=lambda: v('hextras'))
    c_t5.button("🧠 Descanso", use_container_width=True, on_click=lambda: v('simon'))

    # Renderização das ferramentas originais
    if st.session_state.active_view == 'simon':
        COLORS = ["🔴", "🔵", "🟢", "🟡"]
        if st.session_state.simon_status == 'start':
            if st.button("▶️ Jogar"): st.session_state.simon_sequence = [random.choice(COLORS)]; st.session_state.simon_status = 'showing'; st.rerun()
        elif st.session_state.simon_status == 'showing':
            st.write("Memorize:")
            st.write(" ".join(st.session_state.simon_sequence))
            if st.button("Responder"): st.session_state.simon_status = 'playing'; st.rerun()
        elif st.session_state.simon_status == 'playing':
            cols = st.columns(4)
            for i, color in enumerate(COLORS):
                if cols[i].button(color):
                    st.session_state.simon_user_input.append(color)
                    if st.session_state.simon_user_input[-1] != st.session_state.simon_sequence[len(st.session_state.simon_user_input)-1]:
                        st.error("Perdeu!"); st.session_state.simon_status = 'start'; st.rerun()
                    elif len(st.session_state.simon_user_input) == len(st.session_state.simon_sequence):
                        st.session_state.simon_sequence.append(random.choice(COLORS)); st.session_state.simon_user_input = []; st.session_state.simon_status = 'showing'; st.rerun()

    if st.session_state.active_view == 'reg_atendimento':
        with st.container(border=True):
            st.markdown("### Registro de Atendimento")
            u = st.selectbox("Usuário:", REG_USUARIO_OPCOES); s = st.text_input("Setor:"); sis = st.selectbox("Sistema:", REG_SISTEMA_OPCOES)
            d = st.text_input("Desc:"); can = st.selectbox("Canal:", REG_CANAL_OPCOES); desf = st.selectbox("Desfecho:", REG_DESFECHO_OPCOES)
            if st.button("Enviar"):
                if send_atendimento_to_chat(st.session_state.consultor_selectbox, date.today(), u, s, sis, d, can, desf):
                    st.success("Registrado!"); st.session_state.active_view = None; st.rerun()

with col_disponibilidade:
    st.header("Status dos Consultores")
    st.toggle("Auxílio HP/Emails/Whatsapp", key='auxilio_ativo', on_change=save_state)
    st.markdown("---")
    
    # Imagem 1 e 3: Listas
    ui = {'fila': [], 'atv': [], 'ses': [], 'alm': [], 'sai': [], 'aus': []}
    for n in CONSULTORES:
        status = st.session_state.status_texto.get(n, 'Ausente')
        if status in ['Bastão', '']: ui['fila'].append(n)
        elif 'Atividade:' in status: ui['atv'].append((n, status.replace('Atividade: ', '')))
        elif 'Sessão:' in status: ui['ses'].append((n, status.replace('Sessão: ', '')))
        elif status == 'Almoço': ui['alm'].append(n)
        elif status == 'Saída rápida': ui['sai'].append(n)
        else: ui['aus'].append(n)

    def render(title, items, color, is_tup=False):
        st.subheader(f"{title} ({len(items)})")
        if not items: st.caption(f"Ninguém em {title.lower()}.")
        for i in items:
            nome = i[0] if is_tup else i; info = i[1] if is_tup else title
            c_n, c_c = st.columns([0.7, 0.3])
            c_c.checkbox(" ", key=f"c_{nome}", value=st.session_state.get(f"check_{nome}"), on_change=update_queue, args=(nome,), label_visibility="collapsed")
            if nome == responsavel: c_n.markdown(f"🥂 **{nome}**")
            else: c_n.markdown(f"**{nome}** :{color}-background[{info}]", unsafe_allow_html=True)
        st.markdown("---")

    render("Na Fila", ui['fila'], "blue")
    render("Em Atividade", ui['atv'], "orange", True)
    render("Sessão", ui['ses'], "green", True)
    render("Almoço", ui['alm'], "red")
    render("Saída Rápida", ui['sai'], "red")
    render("Ausente", ui['aus'], "grey")

# Relatório 20h
now_br = datetime.utcnow() - timedelta(hours=3)
if now_br.hour >= 20 and now_br.date() > st.session_state.report_last_run_date.date(): send_daily_report()
