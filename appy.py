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
import os

# --- CONFIGURAÇÃO GOOGLE SHEETS (Sua URL integrada) ---
URL_GOOGLE_SHEETS_LOG = "https://script.google.com/macros/s/AKfycby4gt0lWWWGs2jasJ7tBpVVCABq8RUNwggxvMHqRqv55SwMOAnXzn7xFN5S_vKiS3envg/exec"

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

# --- Webhooks (Google Chat) ---
CHAT_WEBHOOK_BASTAO = ""
GOOGLE_CHAT_WEBHOOK_REGISTRO = ""

OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "Whatsapp/Plantão", "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"]
ATIVIDADES_EXIGEM_DETALHE = ["Treinamento", "Homologação", "Redação Documentos", "Outros"]

# URLs de GIFs
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
BASTAO_EMOJI = "🥂"

# ============================================
# 2. FUNÇÕES DE SUPORTE E PERSISTÊNCIA
# ============================================

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
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
                  'rotation_gif_start_time', 'lunch_warning_info', 'auxilio_ativo', 'simon_ranking']
        for f in fields:
            if f in st.session_state: global_data[f] = st.session_state[f]
        global_data['daily_logs'] = json.loads(json.dumps(st.session_state.daily_logs, default=date_serializer))
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

def log_to_google_sheets(consultor, old_s, new_s, duration_str):
    payload = {
        "consultor": consultor,
        "old_status": old_s if old_s else "Disponível",
        "new_status": new_s if new_s else "Disponível",
        "duration": duration_str
    }
    threading.Thread(target=lambda: requests.post(URL_GOOGLE_SHEETS_LOG, json=payload, timeout=10)).start()

def log_status_change(c, old, new, dur):
    if not isinstance(dur, timedelta): dur = timedelta(0)
    dur_str = format_time_duration(dur)
    st.session_state.daily_logs.append({'timestamp': datetime.now(), 'consultor': c, 'old_status': old, 'new_status': new, 'duration': dur})
    st.session_state.current_status_starts[c] = datetime.now()
    log_to_google_sheets(c, old, new, dur_str)

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '00:00:00'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

# ============================================
# 3. LÓGICA DO BASTÃO E FILA
# ============================================

def init_session_state():
    p = load_state()
    defaults = {
        'active_view': None, 'play_sound': False, 'gif_warning': False, 
        'simon_status': 'start', 'simon_sequence': [], 'simon_user_input': [],
        'consultor_selectbox': 'Selecione um nome'
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v
    for k, v in p.items(): st.session_state[k] = v
    for n in CONSULTORES:
        st.session_state[f'check_{n}'] = (st.session_state.status_texto.get(n) in ['Bastão', ''])
    check_and_assume_baton()

def find_next_eligible(curr_idx, q, skips):
    if not q: return -1
    num = len(q); start = (curr_idx + 1) % num
    for i in range(num):
        idx = (start + i) % num
        name = q[idx]
        if st.session_state.get(f'check_{name}') and not skips.get(name): return idx
    return -1

def check_and_assume_baton():
    q = st.session_state.bastao_queue; s = st.session_state.skip_flags
    curr = next((n for n, stt in st.session_state.status_texto.items() if stt == 'Bastão'), None)
    if curr:
        if not st.session_state.get(f'check_{curr}') or curr not in q:
            dur = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
            log_status_change(curr, 'Bastão', st.session_state.status_texto[curr] or 'Ausente', dur)
            curr = None
    if not curr:
        idx = find_next_eligible(-1, q, s)
        if idx != -1:
            nh = q[idx]; st.session_state.status_texto[nh] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
            threading.Thread(target=lambda: requests.post(CHAT_WEBHOOK_BASTAO, json={"text": f"🥂 Bastão com: {nh}"}, timeout=5)).start()
    save_state()

def update_queue(name):
    # Callback sem st.rerun() para evitar aviso no-op
    is_checked = st.session_state[f'check_{name}']
    old = st.session_state.status_texto.get(name, 'Ausente')
    dur = datetime.now() - st.session_state.current_status_starts.get(name, datetime.now())
    if is_checked:
        st.session_state.status_texto[name] = ''
        if name not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(name)
        log_status_change(name, old, 'Disponível', dur)
    else:
        st.session_state.status_texto[name] = 'Ausente'
        if name in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(name)
        st.session_state.skip_flags.pop(name, None)
        log_status_change(name, old, 'Ausente', dur)
    check_and_assume_baton()

def rotate_bastao():
    sel = st.session_state.consultor_selectbox
    curr = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if sel != curr:
        st.session_state.gif_warning = True; return
    q = st.session_state.bastao_queue
    try:
        idx = find_next_eligible(q.index(curr), q, st.session_state.skip_flags)
        if idx != -1:
            nh = q[idx]; dur = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
            log_status_change(curr, 'Bastão', 'Disponível', dur)
            st.session_state.status_texto[curr] = ''; st.session_state.status_texto[nh] = 'Bastão'
            st.session_state.bastao_start_time = datetime.now(); st.session_state.rotation_gif_start_time = datetime.now()
            st.session_state.bastao_counts[curr] += 1; st.rerun()
    except: pass

def update_manual_status(txt):
    sel = st.session_state.consultor_selectbox
    if sel and sel != "Selecione um nome":
        old = st.session_state.status_texto.get(sel, 'Ausente'); dur = datetime.now() - st.session_state.current_status_starts.get(sel, datetime.now())
        st.session_state[f'check_{sel}'] = False
        if sel in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(sel)
        st.session_state.status_texto[sel] = txt; log_status_change(sel, old, txt, dur)
        check_and_assume_baton(); st.rerun()

# ============================================
# 4. INTERFACE (UI)
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()

# --- Refresh e Gifs ---
refresh_ms = 8000
rot_time = st.session_state.get('rotation_gif_start_time')
if rot_time and (datetime.now() - rot_time).total_seconds() < 20:
    st.image(GIF_URL_ROTATION, width=300, caption="Bastão Passado!"); refresh_ms = 2000

if st.session_state.get('gif_warning'):
    st.error("Ação Inválida!"); st.image(GIF_URL_WARNING, width=150); st.session_state.gif_warning = False

st_autorefresh(interval=refresh_ms, key="ref_key")

# --- Cabeçalho ---
c_t_e, c_t_d = st.columns([2, 1], vertical_alignment="bottom")
with c_t_e:
    b64_pug = get_img_as_base64("pug2026.png")
    header_src = f"data:image/png;base64,{b64_pug}" if b64_pug else GIF_BASTAO_HOLDER
    st.markdown(f'''<div style="display: flex; align-items: center; gap: 20px;"><h1 style="color: #FFD700; margin: 0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{header_src}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;"></div>''', unsafe_allow_html=True)
with c_t_d:
    c_s1, c_s2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_s1: n_resp = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
    with c_s2:
        if st.button("🚀 Entrar"):
            if n_resp != "Selecione":
                st.session_state[f'check_{n_resp}'] = True; update_queue(n_resp); st.session_state.consultor_selectbox = n_resp; st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700;'>", unsafe_allow_html=True)

col_m, col_s = st.columns([1.6, 1])

with col_m:
    r_a = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável Atual")
    if r_a:
        st.markdown(f'''<div style="background: #FFF8DC; border: 4px solid #FFD700; padding: 25px; border-radius: 20px; display: flex; align-items: center;"><img src="{GIF_BASTAO_HOLDER}" style="width: 80px; height: 80px; margin-right: 25px; border-radius: 50%; object-fit: cover; border: 2px solid #FFD700;"><div><span style="font-size: 38px; font-weight: bold; color: #000080;">{r_a}</span></div></div>''', unsafe_allow_html=True)
        st.caption(f"⏱️ Tempo: {format_time_duration(datetime.now() - (st.session_state.bastao_start_time or datetime.now()))}")
    else: st.info("Ninguém com o bastão.")

    st.subheader("Consultor(a)")
    st.selectbox("Selecione seu nome:", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox", label_visibility="collapsed")
    
    st.markdown("**Ações Rápidas:**")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    def vt(n): st.session_state.active_view = n if st.session_state.active_view != n else None
    c1.button("🎯 Passar", on_click=rotate_bastao, use_container_width=True)
    c2.button("⏭️ Pular", on_click=lambda: st.session_state.skip_flags.update({st.session_state.consultor_selectbox: True}) or rotate_bastao(), use_container_width=True)
    c3.button("📋 Atividades", on_click=lambda: vt("atv"), use_container_width=True)
    c4.button("🍽️ Almoço", on_click=lambda: update_manual_status("Almoço"), use_container_width=True)
    c5.button("👤 Ausente", on_click=lambda: update_manual_status("Ausente"), use_container_width=True)
    c6.button("🎙️ Sessão", on_click=lambda: vt("ses"), use_container_width=True)
    c7.button("🚶 Saída", on_click=lambda: update_manual_status("Saída rápida"), use_container_width=True)

    if st.session_state.active_view == "atv":
        with st.container(border=True):
            es = st.multiselect("Escolha:", OPCOES_ATIVIDADES_STATUS); de = st.text_input("Tipo/Setor/Descrição (Obrigatório):") if any(x in ATIVIDADES_EXIGEM_DETALHE for x in es) else ""
            if st.button("Confirmar"):
                if es and (not any(x in ATIVIDADES_EXIGEM_DETALHE for x in es) or de.strip()):
                    update_manual_status(f"Atividade: {', '.join(es)}" + (f" [{de}]" if de else "")); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "ses":
        with st.container(border=True):
            ss = st.text_input("Setor da Sessão (Obrigatório):")
            if st.button("Gravar"):
                if ss.strip(): update_manual_status(f"Sessão: {ss}"); st.session_state.active_view = None; st.rerun()

    st.markdown("---")
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.button("📑 Checklist", on_click=lambda: vt("chk"), use_container_width=True)
    t2.button("🆘 Chamados", on_click=lambda: vt("cha"), use_container_width=True)
    t3.button("📝 Atendimento", on_click=lambda: vt("reg"), use_container_width=True)
    t4.button("⏰ H. Extras", on_click=lambda: vt("hex"), use_container_width=True)
    t5.button("🧠 Descanso", on_click=lambda: vt("sim"), use_container_width=True)

with col_s:
    st.header("Status dos Consultores")
    st.toggle("Auxílio HP/Emails/Whatsapp", key="auxilio_ativo", on_change=save_state)
    if st.session_state.auxilio_ativo:
        st.warning("Auxílio Ativo"); st.image(GIF_URL_NEDRY, width=250)
    st.markdown("---")
    ui = {'fila': [], 'atv': [], 'ses': [], 'alm': [], 'sai': [], 'aus': []}
    for n in CONSULTORES:
        s_v = st.session_state.status_texto.get(n, 'Ausente')
        if s_v in ['Bastão', '']: ui['fila'].append(n)
        elif 'Atividade:' in s_v: ui['atv'].append((n, s_v.replace('Atividade: ', '')))
        elif 'Sessão:' in s_v: ui['ses'].append((n, s_v.replace('Sessão: ', '')))
        elif s_v == 'Almoço': ui['alm'].append(n)
        elif s_v == 'Saída rápida': ui['sai'].append(n)
        else: ui['aus'].append(n)

    def render_l(lab, items, col, istu=False):
        st.subheader(f"{lab} ({len(items)})")
        if not items: st.caption(f"Ninguém em {lab.lower()}.")
        for i in items:
            nm = i[0] if istu else i; inf = i[1] if istu else lab; cn, cc = st.columns([0.7, 0.3])
            cc.checkbox(" ", key=f"ch_{nm}", on_change=update_queue, args=(nm,), label_visibility="collapsed")
            if nm == r_a: cn.markdown(f"🥂 **{nm}**")
            else: cn.markdown(f"**{nm}** :{col}-background[{inf}]", unsafe_allow_html=True)
        st.markdown("---")

    render_l("Na Fila", ui['fila'], "blue")
    render_l("Em Atividade", ui['atv'], "orange", True)
    render_l("Sessão", ui['ses'], "green", True)
    render_l("Almoço", ui['alm'], "red")
    render_l("Ausente", ui['aus'], "grey")

# Relatório 20h
if datetime.now().hour >= 20 and datetime.now().date() > st.session_state.report_last_run_date:
    pass
