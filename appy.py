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
import random
import base64

# --- URL DA SUA PLANILHA (Atualizada) ---
URL_GOOGLE_SHEETS = "https://script.google.com/macros/s/AKfycbxRP77Ie-jbhjEDk3F6Za_QWxiIEcEqwRHQ0vQPk63ExLm0JCR24n_nqkWbqdVWT5lhJg/exec"

CONSULTORES = sorted([
    "Alex Paulo da Silva", "Dirceu Gonçalves Siqueira Neto", "Douglas de Souza Gonçalves",
    "Farley Leandro de Oliveira Juliano", "Gleis da Silva Rodrigues", "Hugo Leonardo Murta",
    "Igor Dayrell Gonçalves Correa", "Jerry Marcos dos Santos Neto", "Jonatas Gomes Saraiva",
    "Leandro Victor Catharino", "Luiz Henrique Barros Oliveira", "Marcelo dos Santos Dutra",
    "Marina Silva Marques", "Marina Torres do Amaral", "Vanessa Ligiane Pimenta Santos"
])

# --- CACHE DE ESTADO GLOBAL ---
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    return {
        'status_texto': {nome: 'Ausente' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': date.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'rotation_gif_start_time': None,
        'auxilio_ativo': False, 
        'daily_logs': [],
        'simon_ranking': []
    }

# GIFs e Emojis
BASTAO_EMOJI = "🥂"
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
ATIVIDADES_DETALHE = ["Treinamento", "Homologação", "Redação Documentos", "Outros"]

# ============================================
# 2. INTEGRAÇÃO GOOGLE SHEETS E RESET
# ============================================

def log_to_google_sheets(consultor, status_antigo, status_novo, duracao):
    payload = {
        "consultor": consultor,
        "old_status": status_antigo if status_antigo else "Disponível",
        "new_status": status_novo if status_novo else "Disponível",
        "duration": duracao
    }
    threading.Thread(target=lambda: requests.post(URL_GOOGLE_SHEETS, json=payload, timeout=15)).start()

def format_dur(td):
    if not isinstance(td, timedelta): return "00:00:00"
    s = int(td.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f"{h:02}:{m:02}:{s:02}"

def registrar_mudanca(nome, novo_status):
    if nome == "Selecione um nome" or not nome: return
    old_status = st.session_state.status_texto.get(nome, "Ausente")
    start_time = st.session_state.current_status_starts.get(nome, datetime.now())
    duracao = datetime.now() - start_time
    dur_str = format_dur(duracao)

    st.session_state.status_texto[nome] = novo_status
    st.session_state.current_status_starts[nome] = datetime.now()
    log_to_google_sheets(nome, old_status, novo_status, dur_str)
    save_state()

def reset_diario_sistema():
    """Limpa a fila e status para o próximo dia no Streamlit"""
    st.session_state.status_texto = {nome: 'Ausente' for nome in CONSULTORES}
    st.session_state.bastao_queue = []
    st.session_state.skip_flags = {}
    st.session_state.bastao_counts = {nome: 0 for nome in CONSULTORES}
    st.session_state.daily_logs = []
    st.session_state.report_last_run_date = date.today()
    save_state()
    st.toast("Sistema resetado para o próximo dia!", icon="🧹")

# ============================================
# 3. LÓGICA DO BASTÃO
# ============================================

def save_state():
    cache = get_global_state_cache()
    for k in cache.keys():
        if k in st.session_state: cache[k] = st.session_state[k]

def check_and_assume_baton():
    q = st.session_state.bastao_queue
    curr = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if curr and (curr not in q or st.session_state.status_texto[curr] == 'Ausente'):
        registrar_mudanca(curr, 'Ausente')
        curr = None
    if not curr and q:
        for nome in q:
            if not st.session_state.skip_flags.get(nome):
                st.session_state.status_texto[nome] = 'Bastão'
                st.session_state.bastao_start_time = datetime.now()
                save_state()
                break

def update_queue_callback(nome):
    is_checked = st.session_state[f"chk_{nome}"]
    if is_checked:
        if nome not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(nome)
        registrar_mudanca(nome, "")
    else:
        if nome in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(nome)
        st.session_state.skip_flags.pop(nome, None)
        registrar_mudanca(nome, "Ausente")
    check_and_assume_baton()

# ============================================
# 4. INTERFACE
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

if 'status_texto' not in st.session_state:
    cache = get_global_state_cache()
    for k, v in cache.items(): st.session_state[k] = v
    st.session_state.active_view = None
    st.session_state.consultor_selectbox = "Selecione um nome"

st_autorefresh(interval=8000, key="global_refresh")

# Cabeçalho
c_esq, c_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_esq:
    st.markdown(f'''<div style="display: flex; align-items: center; gap: 20px;">
        <h1 style="color: #FFD700; margin: 0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>
        <img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;">
    </div>''', unsafe_allow_html=True)

with c_dir:
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_sub1:
        n_resp = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
    with c_sub2:
        if st.button("🚀 Entrar"):
            if n_resp != "Selecione":
                st.session_state[f"chk_{n_resp}"] = True
                update_queue_callback(n_resp)
                st.session_state.consultor_selectbox = n_resp
                st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

# Lógica de GIFs
if st.session_state.get('rotation_gif_start_time'):
    if (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 12:
        st.image(GIF_URL_ROTATION, width=250)

col_m, col_s = st.columns([1.6, 1])

with col_m:
    dono = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável Atual")
    if dono:
        st.markdown(f'''<div style="background: #FFF8DC; border: 4px solid #FFD700; padding: 25px; border-radius: 20px; display: flex; align-items: center; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
            <img src="{GIF_BASTAO_HOLDER}" style="width: 70px; height: 70px; margin-right: 20px; border-radius: 50%;">
            <span style="font-size: 36px; font-weight: bold; color: #000080;">{dono}</span>
        </div>''', unsafe_allow_html=True)
        dur_b = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        st.caption(f"⏱️ Tempo: {format_dur(dur_b)}")
    else: st.warning("Ninguém com o bastão.")

    st.subheader("Consultor(a)")
    st.selectbox("Selecione seu nome:", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox", label_visibility="collapsed")
    
    st.markdown("**Ações:**")
    btns = st.columns(7)
    if btns[0].button("🎯 Passar", use_container_width=True):
        if st.session_state.consultor_selectbox == dono:
            registrar_mudanca(dono, "")
            st.session_state.rotation_gif_start_time = datetime.now()
            check_and_assume_baton()
            st.rerun()
    if btns[1].button("⏭️ Pular", use_container_width=True):
        sel = st.session_state.consultor_selectbox
        if sel != "Selecione um nome":
            st.session_state.skip_flags[sel] = True
            if sel == dono: registrar_mudanca(sel, "")
            check_and_assume_baton()
            st.rerun()
    if btns[2].button("📋 Atividades", use_container_width=True): st.session_state.active_view = "atv"
    if btns[3].button("🍽️ Almoço", use_container_width=True): registrar_mudanca(st.session_state.consultor_selectbox, "Almoço"); st.rerun()
    if btns[4].button("👤 Ausente", use_container_width=True): registrar_mudanca(st.session_state.consultor_selectbox, "Ausente"); st.rerun()
    if btns[5].button("🎙️ Sessão", use_container_width=True): st.session_state.active_view = "ses"
    if btns[6].button("🚶 Saída", use_container_width=True): registrar_mudanca(st.session_state.consultor_selectbox, "Saída rápida"); st.rerun()

    if st.session_state.active_view == "atv":
        with st.container(border=True):
            esc = st.multiselect("Opções:", ["HP", "E-mail", "Whatsapp/Plantão", "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"])
            det = st.text_input("Detalhes:") if any(x in ATIVIDADES_DETALHE for x in esc) else ""
            if st.button("Confirmar"):
                registrar_mudanca(st.session_state.consultor_selectbox, f"Atividade: {', '.join(esc)}" + (f" [{det}]" if det else ""))
                st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "ses":
        with st.container(border=True):
            setor = st.text_input("Setor:")
            if st.button("Gravar"):
                registrar_mudanca(st.session_state.consultor_selectbox, f"Sessão: {setor}")
                st.session_state.active_view = None; st.rerun()

    st.markdown("---")
    # Barra de Ferramentas
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.button("📑 Checklist", use_container_width=True)
    t2.button("🆘 Chamados", use_container_width=True)
    t3.button("📝 Atendimento", use_container_width=True)
    t4.button("⏰ H. Extras", use_container_width=True)
    t5.button("🧠 Descanso", use_container_width=True)

with col_s:
    st.header("Status dos Consultores")
    aux = st.toggle("Auxílio HP/Emails/Whatsapp", key="auxilio_ativo", on_change=save_state)
    if aux:
        st.warning("Auxílio Ativado!"); st.image(GIF_URL_NEDRY, width=220)
    
    st.markdown("---")
    ui = {'fila': [], 'atv': [], 'ses': [], 'alm': [], 'sai': [], 'aus': []}
    for n in CONSULTORES:
        s = st.session_state.status_texto.get(n, 'Ausente')
        if s in ['Bastão', '']: ui['fila'].append(n)
        elif 'Atividade:' in s: ui['atv'].append((n, s.replace('Atividade: ', '')))
        elif 'Sessão:' in s: ui['ses'].append((n, s.replace('Sessão: ', '')))
        elif s == 'Almoço': ui['alm'].append(n)
        elif s == 'Saída rápida': ui['sai'].append(n)
        else: ui['aus'].append(n)

    def render_section(label, items, color, is_tup=False):
        st.subheader(f"{label} ({len(items)})")
        if not items: st.caption(f"Ninguém.")
        for i in items:
            name = i[0] if is_tup else i; info = i[1] if is_tup else label
            cn, cc = st.columns([0.7, 0.3])
            cc.checkbox(" ", key=f"chk_{name}", value=(st.session_state.status_texto[name] in ['Bastão', '']), on_change=update_queue_callback, args=(name,), label_visibility="collapsed")
            if name == dono: cn.markdown(f"🥂 **{name}**")
            else: cn.markdown(f"**{name}** :{color}-background[{info}]", unsafe_allow_html=True)
        st.markdown("---")

    render_section("Na Fila", ui['fila'], "blue")
    render_section("Em Atividade", ui['atv'], "orange", True)
    render_section("Sessão", ui['ses'], "green", True)
    render_section("Almoço", ui['alm'], "red")
    render_section("Saída Rápida", ui['sai'], "red")
    render_section("Ausente", ui['aus'], "grey")

# TRIGGER DE RESET AUTOMÁTICO (Reset às 20:00 se ainda não foi feito hoje)
now = datetime.now()
if now.hour >= 20 and st.session_state.report_last_run_date < date.today():
    reset_diario_sistema()
