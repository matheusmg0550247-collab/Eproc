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
        'auxilio_ativo': False, 
        'daily_logs': [],
        'simon_ranking': []
    }

# --- Webhooks e URLs ---
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQA5CyNolU/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zolqmc0YfJ5bPzsqLrefwn8yBbNQLLfFBzLTwIkr7W4"
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "Whatsapp/Plantão", "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"]
ATIVIDADES_EXIGEM_DETALHE = ["Treinamento", "Homologação", "Redação Documentos", "Outros"]

GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
BASTAO_EMOJI = "🥂"

# ============================================
# 2. FUNÇÕES AUXILIARES
# ============================================

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

def save_state():
    gd = get_global_state_cache()
    for k in gd.keys(): 
        if k in st.session_state: gd[k] = st.session_state[k]

def log_status_change(c, old, new, dur):
    if not isinstance(dur, timedelta): dur = timedelta(0)
    st.session_state.daily_logs.append({'timestamp': datetime.now(), 'consultor': c, 'old_status': old, 'new_status': new, 'duration': dur})
    st.session_state.current_status_starts[c] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '00:00:00'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

# ============================================
# 3. LÓGICA CORE (BASTÃO E FILA)
# ============================================

def init_session_state():
    gd = get_global_state_cache()
    defaults = {
        'active_view': None, 'play_sound': False, 'gif_warning': False, 
        'simon_status': 'start', 'simon_sequence': [], 'simon_user_input': [],
        'consultor_selectbox': 'Selecione um nome'
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v
    for k, v in gd.items():
        if k not in st.session_state: st.session_state[k] = v
    for n in CONSULTORES:
        st.session_state[f'check_{n}'] = (st.session_state.status_texto.get(n) in ['Bastão', ''])
    check_and_assume_baton()

def find_next_eligible(curr_idx, q, skips):
    if not q: return -1
    num = len(q)
    start = (curr_idx + 1) % num
    for i in range(num):
        idx = (start + i) % num
        name = q[idx]
        if st.session_state.get(f'check_{name}') and not skips.get(name): return idx
    return -1

def check_and_assume_baton():
    q = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    curr_holder = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    
    if curr_holder:
        if not st.session_state.get(f'check_{curr_holder}') or curr_holder not in q:
            dur = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
            log_status_change(curr_holder, 'Bastão', st.session_state.status_texto[curr_holder] or 'Ausente', dur)
            curr_holder = None

    if not curr_holder:
        idx = find_next_eligible(-1, q, skips)
        if idx != -1:
            nh = q[idx]
            st.session_state.status_texto[nh] = 'Bastão'
            st.session_state.bastao_start_time = datetime.now()
            threading.Thread(target=lambda: requests.post(CHAT_WEBHOOK_BASTAO, json={"text": f"🥂 Bastão com: {nh}"}, timeout=5)).start()
    save_state()

def update_queue(name):
    """Callback para o Checkbox - CORREÇÃO: Removido st.rerun() pois é callback"""
    is_checked = st.session_state[f'check_{name}']
    old_status = st.session_state.status_texto.get(name, 'Ausente')
    dur = datetime.now() - st.session_state.current_status_starts.get(name, datetime.now())

    if is_checked:
        st.session_state.status_texto[name] = ''
        if name not in st.session_state.bastao_queue: 
            st.session_state.bastao_queue.append(name)
        log_status_change(name, old_status, '', dur)
    else:
        st.session_state.status_texto[name] = 'Ausente'
        if name in st.session_state.bastao_queue: 
            st.session_state.bastao_queue.remove(name)
        st.session_state.skip_flags.pop(name, None)
        log_status_change(name, old_status, 'Ausente', dur)
    
    check_and_assume_baton()

def rotate_bastao():
    sel = st.session_state.consultor_selectbox
    curr = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if sel != curr:
        st.session_state.gif_warning = True
        return
    q = st.session_state.bastao_queue
    try:
        idx = find_next_eligible(q.index(curr), q, st.session_state.skip_flags)
        if idx != -1:
            nh = q[idx]
            dur = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
            log_status_change(curr, 'Bastão', '', dur)
            st.session_state.status_texto[curr] = ''
            st.session_state.status_texto[nh] = 'Bastão'
            st.session_state.bastao_start_time = datetime.now()
            st.session_state.rotation_gif_start_time = datetime.now()
            st.session_state.bastao_counts[curr] += 1
            save_state()
            st.rerun()
    except: pass

def update_manual_status(txt):
    sel = st.session_state.consultor_selectbox
    if sel and sel != "Selecione um nome":
        st.session_state[f'check_{sel}'] = False
        # Remove da fila internamente
        if sel in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(sel)
        st.session_state.status_texto[sel] = txt
        check_and_assume_baton()
        st.rerun()

# ============================================
# 4. INTERFACE (UI)
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()

# --- Refresh e GIFs ---
refresh_ms = 8000
rot_time = st.session_state.get('rotation_gif_start_time')
if rot_time and (datetime.now() - rot_time).total_seconds() < 20:
    st.image(GIF_URL_ROTATION, width=300, caption="Bastão Passado!")
    refresh_ms = 2000

if st.session_state.get('gif_warning'):
    st.error("Ação Inválida! Verifique as regras de rotação.")
    st.image(GIF_URL_WARNING, width=150)
    st.session_state.gif_warning = False

st_autorefresh(interval=refresh_ms, key="ref_key")

# --- Cabeçalho (Painel Identico ao Primeiro Código) ---
c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")

with c_topo_esq:
    b64_pug = get_img_as_base64("pug2026.png")
    header_img = f"data:image/png;base64,{b64_pug}" if b64_pug else GIF_BASTAO_HOLDER
    st.markdown(f'''
        <div style="display: flex; align-items: center; gap: 20px;">
            <h1 style="color: #FFD700; margin: 0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>
            <img src="{header_img}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;">
        </div>
    ''', unsafe_allow_html=True)

with c_topo_dir:
    # --- MENU "ASSUMIR BASTÃO" IGUAL AO PRIMEIRO CÓDIGO ---
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_sub1:
        novo_responsavel = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
    with c_sub2:
        if st.button("🚀 Entrar", help="Ficar disponível na fila imediatamente"):
            if novo_responsavel and novo_responsavel != "Selecione":
                st.session_state[f'check_{novo_responsavel}'] = True
                update_queue(novo_responsavel)
                st.session_state.consultor_selectbox = novo_responsavel
                st.success(f"{novo_responsavel} entrou!")
                st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700;'>", unsafe_allow_html=True)

col_main, col_side = st.columns([1.6, 1])

with col_main:
    # Card do Responsável Atual
    resp_atual = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável Atual")
    if resp_atual:
        st.markdown(f'''
            <div style="background: #FFF8DC; border: 4px solid #FFD700; padding: 25px; border-radius: 20px; display: flex; align-items: center; box-shadow: 4px 4px 12px rgba(0,0,0,0.1);">
                <img src="{GIF_BASTAO_HOLDER}" style="width: 80px; height: 80px; margin-right: 25px; border-radius: 50%; object-fit: cover; border: 2px solid #FFD700;">
                <div>
                    <span style="font-size: 14px; color: #666; font-weight: bold; text-transform: uppercase;">Atualmente com:</span><br>
                    <span style="font-size: 38px; font-weight: bold; color: #000080;">{resp_atual}</span>
                </div>
            </div>
        ''', unsafe_allow_html=True)
        dur_b = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        st.caption(f"⏱️ Tempo com o bastão: {format_time_duration(dur_b)}")
    else: st.info("Ninguém com o bastão no momento.")

    st.subheader("Consultor(a)")
    st.selectbox("Selecione seu nome:", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox", label_visibility="collapsed")
    
    st.markdown("**Ações Rápidas:**")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    def v_toggle(name): st.session_state.active_view = name if st.session_state.active_view != name else None
    
    c1.button("🎯 Passar", on_click=rotate_bastao, use_container_width=True)
    c2.button("⏭️ Pular", on_click=lambda: st.session_state.skip_flags.update({st.session_state.consultor_selectbox: True}) or rotate_bastao(), use_container_width=True)
    c3.button("📋 Atividades", on_click=lambda: v_toggle("atv"), use_container_width=True)
    c4.button("🍽️ Almoço", on_click=lambda: update_manual_status("Almoço"), use_container_width=True)
    c5.button("👤 Ausente", on_click=lambda: update_manual_status("Ausente"), use_container_width=True)
    c6.button("🎙️ Sessão", on_click=lambda: v_toggle("ses"), use_container_width=True)
    c7.button("🚶 Saída", on_click=lambda: update_manual_status("Saída rápida"), use_container_width=True)

    if st.session_state.active_view == "atv":
        with st.container(border=True):
            st.markdown("### Registrar Atividades")
            esc = st.multiselect("Escolha as opções:", OPCOES_ATIVIDADES_STATUS, placeholder="Escolha as opções")
            det = st.text_input("Tipo/Setor/Descrição (Obrigatório):") if any(x in ATIVIDADES_EXIGEM_DETALHE for x in esc) else ""
            if st.button("Confirmar Atividade", type="primary"):
                if esc and (not any(x in ATIVIDADES_EXIGEM_DETALHE for x in esc) or det.strip()):
                    update_manual_status(f"Atividade: {', '.join(esc)}" + (f" [{det}]" if det else ""))
                    st.session_state.active_view = None; st.rerun()
                else: st.error("Preencha o campo obrigatório.")

    if st.session_state.active_view == "ses":
        with st.container(border=True):
            st.markdown("### Registrar Sessão")
            s_setor = st.text_input("Setor da Sessão (Obrigatório):")
            if st.button("Confirmar Sessão", type="primary"):
                if s_setor.strip():
                    update_manual_status(f"Sessão: {s_setor}")
                    st.session_state.active_view = None; st.rerun()
                else: st.error("O setor é obrigatório.")

    st.markdown("---")
    # Barra de Ferramentas
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.button("📑 Checklist", on_click=lambda: v_toggle("chk"), use_container_width=True)
    t2.button("🆘 Chamados", on_click=lambda: v_toggle("cha"), use_container_width=True)
    t3.button("📝 Atendimento", on_click=lambda: v_toggle("reg"), use_container_width=True)
    t4.button("⏰ H. Extras", on_click=lambda: v_toggle("hex"), use_container_width=True)
    t5.button("🧠 Descanso", on_click=lambda: v_toggle("sim"), use_container_width=True)

    if st.session_state.active_view == "sim":
        with st.container(border=True): st.write("### Jogo Simon"); st.button("Iniciar Novo Jogo")

with col_side:
    st.header("Status dos Consultores")
    st.toggle("Auxílio HP/Emails/Whatsapp", key="auxilio_ativo", on_change=save_state)
    if st.session_state.auxilio_ativo:
        st.warning("Auxílio Ativo"); st.image(GIF_URL_NEDRY, width=250)
    
    st.markdown("---")
    ui = {'fila': [], 'atv': [], 'ses': [], 'alm': [], 'sai': [], 'aus': []}
    for n in CONSULTORES:
        s_val = st.session_state.status_texto.get(n, 'Ausente')
        if s_val in ['Bastão', '']: ui['fila'].append(n)
        elif 'Atividade:' in s_val: ui['atv'].append((n, s_val.replace('Atividade: ', '')))
        elif 'Sessão:' in s_val: ui['ses'].append((n, s_val.replace('Sessão: ', '')))
        elif s_val == 'Almoço': ui['alm'].append(n)
        elif s_val == 'Saída rápida': ui['sai'].append(n)
        else: ui['aus'].append(n)

    def render_cat(label, items, color, is_t=False):
        st.subheader(f"{label} ({len(items)})")
        if not items: st.caption(f"Ninguém em {label.lower()}.")
        for i in items:
            name = i[0] if is_t else i
            info = i[1] if is_t else label
            cn, cc = st.columns([0.7, 0.3])
            cc.checkbox(" ", key=f"check_{name}", on_change=update_queue, args=(name,), label_visibility="collapsed")
            if name == resp_atual: cn.markdown(f"🥂 **{name}**")
            else: cn.markdown(f"**{name}** :{color}-background[{info}]", unsafe_allow_html=True)
        st.markdown("---")

    render_cat("Na Fila", ui['fila'], "blue")
    render_cat("Em Atividade", ui['atv'], "orange", True)
    render_cat("Sessão", ui['ses'], "green", True)
    render_cat("Almoço", ui['alm'], "red")
    render_cat("Ausente", ui['aus'], "grey")

# Relatório 20h
if datetime.now().hour >= 20 and datetime.now().date() > st.session_state.report_last_run_date:
    pass
