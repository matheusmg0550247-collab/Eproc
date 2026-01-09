# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from streamlit_autorefresh import st_autorefresh
import threading

# --- URLS DE INTEGRAÇÃO (WEBHOOKS) ---
URL_GOOGLE_SHEETS = "https://script.google.com/macros/s/AKfycbxRP77Ie-jbhjEDk3F6Za_QWxiIEcEqwRHQ0vQPk63ExLm0JCR24n_nqkWbqdVWT5lhJg/exec"
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"
GOOGLE_CHAT_WEBHOOK_REGISTRO = ""
CHAT_WEBHOOK_BASTAO = ""
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

# --- CONFIGURAÇÕES DE UI ---
BASTAO_EMOJI = "🥂"
# URL do Pug Holder (GIF Animado)
GIF_PUG_URL = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"

CONSULTORES = sorted([
    "Alex Paulo da Silva", "Dirceu Gonçalves Siqueira Neto", "Douglas de Souza Gonçalves",
    "Farley Leandro de Oliveira Juliano", "Gleis da Silva Rodrigues", "Hugo Leonardo Murta",
    "Igor Dayrell Gonçalves Correa", "Jerry Marcos dos Santos Neto", "Jonatas Gomes Saraiva",
    "Leandro Victor Catharino", "Luiz Henrique Barros Oliveira", "Marcelo dos Santos Dutra",
    "Marina Silva Marques", "Marina Torres do Amaral", "Vanessa Ligiane Pimenta Santos"
])

LISTA_PROJETOS = ["Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", "IA nos Cartórios", "Notebook Lm"]

# ============================================
# 2. INTEGRAÇÃO E UTILITÁRIOS
# ============================================

def disparar_chat(webhook_url, mensagem):
    threading.Thread(target=lambda: requests.post(webhook_url, json={"text": mensagem}, timeout=10)).start()

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
    
    # Log Sheets e Registro Chat
    payload = {"consultor": nome, "old_status": old_status, "new_status": novo_status, "duration": dur_str}
    threading.Thread(target=lambda: requests.post(URL_GOOGLE_SHEETS, json=payload, timeout=15)).start()
    disparar_chat(GOOGLE_CHAT_WEBHOOK_REGISTRO, f"📝 *Status:* {nome} ➔ {novo_status} (Anterior durou: {dur_str})")

@st.cache_resource
def get_global_state():
    return {
        'status_texto': {n: 'Ausente' for n in CONSULTORES},
        'bastao_queue': [],
        'current_status_starts': {n: datetime.now() for n in CONSULTORES},
        'bastao_start_time': None,
        'report_last_run_date': date.min
    }

# ============================================
# 3. LÓGICA DO BASTÃO E FILA
# ============================================

def check_and_assume_baton():
    q = st.session_state.bastao_queue
    dono_atual = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    
    # Se ninguém tem o bastão e há fila, o primeiro assume
    if not dono_atual and q:
        novo_dono = q[0]
        st.session_state.status_texto[novo_dono] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        disparar_chat(CHAT_WEBHOOK_BASTAO, f"🥂 *Novo Responsável:* {novo_dono}")
        st.balloons() # Fogos de artifício ao assumir

def update_queue(nome):
    is_active = st.session_state[f"chk_{nome}"]
    if is_active:
        if nome not in st.session_state.bastao_queue:
            st.session_state.bastao_queue.append(nome)
            registrar_mudanca(nome, "")
    else:
        if nome in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(nome)
        registrar_mudanca(nome, "Ausente")
    check_and_assume_baton()

# ============================================
# 4. INTERFACE
# ============================================

st.set_page_config(page_title="Controle Bastão 2026", layout="wide", page_icon="🥂")

if 'status_texto' not in st.session_state:
    for k, v in get_global_state().items(): st.session_state[k] = v
    st.session_state.active_view = None

st_autorefresh(interval=8000, key="refresh")

# --- CABEÇALHO COM O PUG ---
c_head, c_enter = st.columns([2, 1])
with c_head:
    st.markdown(f'''
        <div style="display: flex; align-items: center; gap: 15px;">
            <h1 style="color: #FFD700; margin: 0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>
            <img src="{GIF_PUG_URL}" style="width: 60px; height: 60px; border-radius: 50%; border: 2px solid #FFD700;">
        </div>
    ''', unsafe_allow_html=True)

with c_enter:
    ce1, ce2 = st.columns([2, 1])
    sel_rapido = ce1.selectbox("Assumir Rápido", ["Selecione"] + CONSULTORES, label_visibility="collapsed")
    if ce2.button("🚀 Entrar"):
        if sel_rapido != "Selecione":
            st.session_state[f"chk_{sel_rapido}"] = True
            update_queue(sel_rapido); st.rerun()

st.divider()

col_main, col_status = st.columns([1.6, 1])

with col_main:
    # --- RESPONSÁVEL ATUAL ---
    dono = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.subheader("Responsável Atual")
    if dono:
        st.markdown(f'''
            <div style="background: #FFF8DC; border: 3px solid #FFD700; padding: 20px; border-radius: 15px; display: flex; align-items: center;">
                <img src="{GIF_PUG_URL}" style="width: 50px; height: 50px; margin-right: 15px; border-radius: 50%;">
                <span style="font-size: 28px; font-weight: bold; color: #000080;">{dono}</span>
            </div>
        ''', unsafe_allow_html=True)
        dur = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        st.caption(f"⏱️ Tempo no Bastão: {format_dur(dur)}")
    else: st.warning("Ninguém com o bastão no momento.")

    st.selectbox("Selecione seu nome para ações:", ["Selecione um nome"] + CONSULTORES, key="user_sel")
    
    # BOTÕES DE AÇÃO
    st.markdown("**Ações Principais:**")
    b1, b2, b3, b4, b5 = st.columns(5)
    if b1.button("🎯 Passar", use_container_width=True):
        if st.session_state.user_sel == dono:
            registrar_mudanca(dono, "")
            if dono in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(dono)
            st.balloons() # Fogos de artifício ao passar o bastão
            check_and_assume_baton(); st.rerun()
    
    if b2.button("📋 Atividades", use_container_width=True): st.session_state.active_view = "atv"
    if b3.button("🎙️ Sessão", use_container_width=True): st.session_state.active_view = "ses"
    if b4.button("📁 Projetos", use_container_width=True): st.session_state.active_view = "prj"
    if b5.button("👤 Ausente", use_container_width=True): registrar_mudanca(st.session_state.user_sel, "Ausente"); st.rerun()

    # --- BARRA DE FERRAMENTAS ---
    st.markdown("---")
    t1, t2, t3, t4 = st.columns(4)
    if t1.button("📑 Checklist", use_container_width=True): disparar_chat(GOOGLE_CHAT_WEBHOOK_REGISTRO, f"📑 Checklist por {st.session_state.user_sel}")
    if t2.button("🆘 Chamados", use_container_width=True): disparar_chat(GOOGLE_CHAT_WEBHOOK_CHAMADO, f"🆘 APOIO: {st.session_state.user_sel}")
    if t3.button("⏰ H. Extras", use_container_width=True): disparar_chat(GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS, f"⏰ Hora Extra: {st.session_state.user_sel}")
    if t4.button("⚠️ Erro/Novidade", use_container_width=True): st.session_state.active_view = "err"

with col_status:
    st.header("Status da Equipe")
    st.toggle("Auxílio Ativado", key="aux_atv")
    
    # --- ORGANIZAÇÃO DA FILA E STATUS ---
    ui = {'fila': st.session_state.bastao_queue, 'atv': [], 'prj': [], 'aus': []}
    for n in CONSULTORES:
        s = st.session_state.status_texto.get(n, 'Ausente')
        if 'Atividade:' in s: ui['atv'].append((n, s))
        elif 'Projeto:' in s: ui['prj'].append((n, s))
        elif s == 'Ausente' and n not in st.session_state.bastao_queue: ui['aus'].append(n)

    # RENDERIZAR "NA FILA" COM ORDEM
    st.subheader(f"Na Fila ({len(ui['fila'])})")
    for idx, nome in enumerate(ui['fila']):
        c_n, c_c = st.columns([0.8, 0.2])
        # Primeiro da fila ganha o emoji de bastão se ele for o dono
        prefix = "🥂 " if st.session_state.status_texto[nome] == "Bastão" else f"{idx+1}º "
        c_n.write(f"**{prefix}{nome}**")
        c_c.checkbox(" ", key=f"chk_{nome}", value=True, on_change=update_queue, args=(nome,), label_visibility="collapsed")
    
    st.divider()
    # Outras seções simplificadas para o status
    for cat, lista in [("Em Atividade", ui['atv']), ("Projetos", ui['prj']), ("Ausentes", ui['aus'])]:
        st.write(f"**{cat} ({len(lista)})**")
        for item in lista:
            nome = item[0] if isinstance(item, tuple) else item
            st.caption(f"• {nome}")

# RESET DIÁRIO
if datetime.now().hour >= 20 and st.session_state.report_last_run_date < date.today():
    st.session_state.status_texto = {n: 'Ausente' for n in CONSULTORES}
    st.session_state.bastao_queue = []
    st.session_state.report_last_run_date = date.today()
    st.rerun()
