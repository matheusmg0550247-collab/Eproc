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
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "Whatsapp/Plantão", "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"]
ATIVIDADES_EXIGEM_DETALHE = ["Treinamento", "Homologação", "Redação Documentos", "Outros"]

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
# 2. FUNÇÕES AUXILIARES GLOBAIS
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
        fields = ['status_texto', 'bastao_queue', 'skip_flags', 'current_status_starts', 'bastao_counts', 
                  'priority_return_queue', 'bastao_start_time', 'report_last_run_date', 
                  'rotation_gif_start_time', 'lunch_warning_info', 'auxilio_ativo', 'daily_logs', 'simon_ranking']
        for f in fields:
            if f in st.session_state:
                if f == 'daily_logs':
                    global_data[f] = json.loads(json.dumps(st.session_state[f], default=date_serializer))
                else:
                    global_data[f] = st.session_state[f]
    except: pass

def load_state():
    gd = get_global_state_cache()
    logs = gd.get('daily_logs', [])
    final_logs = []
    for l in logs:
        if isinstance(l, dict):
            if 'duration' in l and not isinstance(l['duration'], timedelta):
                try: l['duration'] = timedelta(seconds=float(l['duration']))
                except: l['duration'] = timedelta(0)
            if 'timestamp' in l and isinstance(l['timestamp'], str):
                try: l['timestamp'] = datetime.fromisoformat(l['timestamp'])
                except: l['timestamp'] = datetime.min
            final_logs.append(l)
    data = {k: v for k, v in gd.items() if k != 'daily_logs'}
    data['daily_logs'] = final_logs
    return data

def log_status_change(consultor, old_s, new_s, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    st.session_state.daily_logs.append({
        'timestamp': datetime.now(), 'consultor': consultor, 'old_status': old_s, 
        'new_status': new_s, 'duration': duration, 'duration_s': duration.total_seconds()
    })
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        msg = {"text": f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Responsável:** {consultor}\n- **Painel:** {APP_URL_CLOUD}"}
        threading.Thread(target=lambda: requests.post(CHAT_WEBHOOK_BASTAO, json=msg, timeout=5)).start()

def render_fireworks():
    css = """<style>@keyframes firework {0% { transform: translate(var(--x), var(--initialY)); width: var(--initialSize); opacity: 1; } 50% { width: 0.5vmin; opacity: 1; } 100% { width: var(--finalSize); opacity: 0; }} .firework, .firework::before, .firework::after { --initialSize: 0.5vmin; --finalSize: 45vmin; --particleSize: 0.2vmin; --color1: #ff0000; --color2: #ffd700; --y: -30vmin; --x: -50%; --initialY: 60vmin; content: ""; animation: firework 2s infinite; position: absolute; top: 50%; left: 50%; transform: translate(-50%, var(--y)); width: var(--initialSize); aspect-ratio: 1; background: radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%; background-size: var(--initialSize) var(--initialSize); background-repeat: no-repeat; }</style><div class="firework"></div><div class="firework"></div>"""
    st.markdown(css, unsafe_allow_html=True)

# ============================================
# 3. LÓGICA DO BASTÃO E FILA
# ============================================

def init_session_state():
    p = load_state()
    defaults = {'active_view': None, 'play_sound': False, 'gif_warning': False, 'simon_status': 'start', 'simon_sequence': [], 'simon_user_input': []}
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v
    for k, v in p.items(): st.session_state[k] = v
    for n in CONSULTORES:
        status = st.session_state.status_texto.get(n, 'Ausente')
        st.session_state[f'check_{n}'] = (status == 'Bastão' or status == '')
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
        log_status_change(consultor, old, '', dur)
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    else:
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

def update_status(stt):
    sel = st.session_state.consultor_selectbox
    if sel == 'Selecione um nome': return
    st.session_state[f'check_{sel}'] = False
    log_status_change(sel, st.session_state.status_texto.get(sel, ''), stt, datetime.now() - st.session_state.current_status_starts.get(sel, datetime.now()))
    st.session_state.status_texto[sel] = stt
    if sel in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(sel)
    check_and_assume_baton(); save_state()

# ============================================
# 4. INTERFACE E RENDERIZAÇÃO
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
render_fireworks()

# --- LÓGICA DE REFRESH E GIFS ---
refresh_int = 8000
gif_time = st.session_state.get('rotation_gif_start_time')
if gif_time:
    if (datetime.now() - gif_time).total_seconds() < 20:
        st.image(GIF_URL_ROTATION, width=300)
        refresh_int = 2000
    else:
        st.session_state.rotation_gif_start_time = None; save_state()

if st.session_state.get('gif_warning'):
    st.error("Ação Inválida!"); st.image(GIF_URL_WARNING, width=150)
    st.session_state.gif_warning = False

st_autorefresh(interval=refresh_int, key='auto_ref')

# --- TOPO ---
c_t_e, c_t_d = st.columns([2, 1], vertical_alignment="bottom")
with c_t_e:
    img_b64 = get_img_as_base64(PUG2026_FILENAME)
    src = f"data:image/png;base64,{img_b64}" if img_b64 else GIF_BASTAO_HOLDER
    st.markdown(f'<div style="display: flex; align-items: center; gap: 15px;"><h1 style="color: #FFD700;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>'
                f'<img src="{src}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700;"></div>', unsafe_allow_html=True)
with c_t_d:
    sel_entrar = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed")
    if st.button("🚀 Entrar"):
        if sel_entrar != "Selecione": st.session_state[f'check_{sel_entrar}'] = True; update_queue(sel_entrar); st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700;'>", unsafe_allow_html=True)

col_p, col_d = st.columns([1.5, 1])

with col_p:
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
    def v(n): st.session_state.active_view = n if st.session_state.active_view != n else None

    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    c2.button('⏭️ Pular', on_click=lambda: st.session_state.skip_flags.update({st.session_state.consultor_selectbox: True}) or rotate_bastao(), use_container_width=True)
    c3.button('📋 Atividades', on_click=lambda: v('atv'), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=lambda: update_status('Almoço'), use_container_width=True)
    c5.button('👤 Ausente', on_click=lambda: update_status('Ausente'), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=lambda: v('ses'), use_container_width=True)
    c7.button('🚶 Saída', on_click=lambda: update_status('Saída rápida'), use_container_width=True)

    if st.session_state.active_view == 'atv':
        with st.container(border=True):
            esc = st.multiselect("Atividades:", OPCOES_ATIVIDADES_STATUS, placeholder="Escolha as opções")
            det = st.text_input("Tipo/Setor/Descrição (Obrigatório):") if any(x in ATIVIDADES_EXIGEM_DETALHE for x in esc) else ""
            if st.button("Confirmar Atividade", type="primary"):
                if esc and (not any(x in ATIVIDADES_EXIGEM_DETALHE for x in esc) or det.strip()):
                    update_status(f"Atividade: {', '.join(esc)}" + (f" [{det}]" if det else "")); st.session_state.active_view = None; st.rerun()
                else: st.error("Preencha os campos obrigatórios.")

    if st.session_state.active_view == 'ses':
        with st.container(border=True):
            setor_s = st.text_input("Setor (Obrigatório):")
            if st.button("Confirmar Sessão", type="primary"):
                if setor_s.strip(): update_status(f"Sessão: {setor_s}"); st.session_state.active_view = None; st.rerun()
                else: st.error("O Setor é obrigatório.")

    st.markdown("---")
    c_t1, c_t2, c_t3, c_t4, c_t5 = st.columns(5)
    c_t1.button("📑 Checklist", on_click=lambda: v('chk'), use_container_width=True)
    c_t2.button("🆘 Chamados", on_click=lambda: v('cha'), use_container_width=True)
    c_t3.button("📝 Atendimento", on_click=lambda: v('reg'), use_container_width=True)
    c_t4.button("⏰ H. Extras", on_click=lambda: v('hex'), use_container_width=True)
    c_t5.button("🧠 Descanso", on_click=lambda: v('sim'), use_container_width=True)

    if st.session_state.active_view == 'sim':
        cols = st.columns(4); p = None
        for i, c in enumerate(["🔴", "🔵", "🟢", "🟡"]):
            if cols[i].button(c, use_container_width=True): p = c
        if st.button("Zerar/Iniciar"): st.session_state.simon_status = 'start'; st.rerun()

with col_d:
    st.header("Status dos Consultores")
    st.toggle("Auxílio HP/Emails/Whatsapp", key='auxilio_ativo', on_change=save_state)
    if st.session_state.auxilio_ativo:
        st.warning("Auxílio Ativo"); st.image(GIF_URL_NEDRY, width=250)
    st.markdown("---")
    
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
