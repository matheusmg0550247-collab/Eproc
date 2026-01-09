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
import base64

# --- URLS DE INTEGRAÇÃO (WEBHOOKS) ---
URL_GOOGLE_SHEETS = "https://script.google.com/macros/s/AKfycbxRP77Ie-jbhjEDk3F6Za_QWxiIEcEqwRHQ0vQPk63ExLm0JCR24n_nqkWbqdVWT5lhJg/exec"
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"
GOOGLE_CHAT_WEBHOOK_BACKUP = ""
CHAT_WEBHOOK_BASTAO = ""
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

CONSULTORES = sorted([
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", 
    "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", 
    "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", 
    "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

LISTA_PROJETOS = ["Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", "IA nos Cartórios", "Notebook Lm"]
PUG2026_FILENAME = "pug2026.png"
BASTAO_EMOJI = "🥂"
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'

TEMPLATE_ERRO = """TITULO: 
OBJETIVO: 
RELATO DO ERRO/TESTE: 
RESULTADO: 
OBSERVAÇÃO (SE TIVER): """

# ============================================
# 2. INTEGRAÇÃO E UTILITÁRIOS
# ============================================

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except: return None

def disparar_chat(webhook_url, mensagem):
    threading.Thread(target=lambda: requests.post(webhook_url, json={"text": mensagem}, timeout=10)).start()

def render_fireworks():
    # Fogos nas cores Vermelho e Dourado
    st.markdown("""
    <style>
    @keyframes firework { 0% { transform: translate(var(--x), 60vmin); width: 0.5vmin; opacity: 1; } 100% { width: 45vmin; opacity: 0; } }
    .firework { --color1: #ff0000; --color2: #ffd700; position: absolute; top: 50%; left: 50%; animation: firework 2s infinite; background: radial-gradient(circle, var(--color1) 0.2vmin, #0000 0) 50% 0%; background-size: 0.5vmin 0.5vmin; background-repeat: no-repeat; }
    </style>
    <div class="firework"></div><div class="firework" style="left:30%; animation-delay:-0.5s;"></div><div class="firework" style="left:70%; animation-delay:-1s;"></div>
    """, unsafe_allow_html=True)

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
    payload = {"consultor": nome, "old_status": old_status, "new_status": novo_status, "duration": dur_str}
    threading.Thread(target=lambda: requests.post(URL_GOOGLE_SHEETS, json=payload, timeout=15)).start()
    disparar_chat(GOOGLE_CHAT_WEBHOOK_REGISTRO, f"📝 *Status:* {nome} ➔ {novo_status} (Anterior: {dur_str})")
    save_state()

@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    return {
        'status_texto': {nome: 'Ausente' for nome in CONSULTORES},
        'bastao_queue': [],
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': date.min,
        'bastao_start_time': None,
        'rotation_gif_start_time': None,
        'auxilio_ativo': False
    }

def save_state():
    cache = get_global_state_cache()
    for k in cache.keys():
        if k in st.session_state: cache[k] = st.session_state[k]

# ============================================
# 3. LÓGICA DO BASTÃO
# ============================================

def check_and_assume_baton():
    q = st.session_state.bastao_queue
    curr = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if not curr and q:
        novo = q[0]
        st.session_state.status_texto[novo] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        disparar_chat(CHAT_WEBHOOK_BASTAO, f"🥂 *Novo Responsável:* {novo}")
        st.balloons() # Fogos de artifício ao assumir
        save_state()

def update_queue_callback(nome):
    is_checked = st.session_state[f"chk_{nome}"]
    if is_checked:
        if nome not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(nome)
        registrar_mudanca(nome, "")
    else:
        if nome in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(nome)
        registrar_mudanca(nome, "Ausente")
    check_and_assume_baton()

# ============================================
# 4. INTERFACE PRINCIPAL
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

if 'status_texto' not in st.session_state:
    for k, v in get_global_state_cache().items(): st.session_state[k] = v
    st.session_state.active_view = None

st_autorefresh(interval=8000, key="global_refresh")
render_fireworks()

# --- CABEÇALHO COM O PUG ---
c_head, c_enter = st.columns([2, 1])
with c_head:
    pug_b64 = get_img_as_base64(PUG2026_FILENAME)
    pug_src = f"data:image/png;base64,{pug_b64}" if pug_b64 else GIF_BASTAO_HOLDER
    st.markdown(f'''<div style="display: flex; align-items: center; gap: 15px;">
        <h1 style="color: #FFD700; margin: 0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>
        <img src="{pug_src}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;">
    </div>''', unsafe_allow_html=True)

with c_enter:
    c1, c2 = st.columns([2, 1])
    n_assumir = c1.selectbox("Assumir Rápido", ["Selecione"] + CONSULTORES, label_visibility="collapsed")
    if c2.button("🚀 Entrar"):
        if n_assumir != "Selecione":
            st.session_state[f"chk_{n_assumir}"] = True
            update_queue_callback(n_assumir); st.rerun()

st.divider()

if st.session_state.get('rotation_gif_start_time'):
    if (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 12:
        st.image(GIF_URL_ROTATION, width=250)

col_m, col_s = st.columns([1.6, 1])

with col_m:
    # --- RESPONSÁVEL ATUAL COM PUG ---
    dono = next((n for n, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável Atual")
    if dono:
        st.markdown(f'''<div style="background: #FFF8DC; border: 4px solid #FFD700; padding: 25px; border-radius: 20px; display: flex; align-items: center;">
            <img src="{pug_src}" style="width: 70px; height: 70px; margin-right: 20px; border-radius: 50%;">
            <span style="font-size: 36px; font-weight: bold; color: #000080;">{dono}</span>
        </div>''', unsafe_allow_html=True)
        dur = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        st.caption(f"⏱️ Tempo: {format_dur(dur)}")
    else: st.warning("Ninguém com o bastão.")

    st.subheader("Consultor(a)")
    sel_u = st.selectbox("Seu nome:", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox", label_visibility="collapsed")
    
    st.markdown("**Ações Principais:**")
    btns = st.columns(8) 
    if btns[0].button("🎯 Passar", use_container_width=True):
        if sel_u == dono:
            registrar_mudanca(dono, "")
            if dono in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(dono)
            st.session_state.rotation_gif_start_time = datetime.now()
            st.balloons(); check_and_assume_baton(); st.rerun()
    if btns[1].button("⏭️ Pular", use_container_width=True): pass
    if btns[2].button("📋 Atividades", use_container_width=True): st.session_state.active_view = "atv"
    if btns[3].button("🍽️ Almoço", use_container_width=True): registrar_mudanca(sel_u, "Almoço"); st.rerun()
    if btns[4].button("👤 Ausente", use_container_width=True): registrar_mudanca(sel_u, "Ausente"); st.rerun()
    if btns[5].button("🎙️ Sessão", use_container_width=True): st.session_state.active_view = "ses"
    if btns[6].button("🚶 Saída", use_container_width=True): registrar_mudanca(sel_u, "Saída rápida"); st.rerun()
    if btns[7].button("📁 Projetos", use_container_width=True): st.session_state.active_view = "prj" # Botão Projetos

    # Views Dinâmicas (Projetos, Erros, etc.)
    if st.session_state.active_view == "prj":
        with st.container(border=True):
            p_sel = st.selectbox("Escolha o projeto:", LISTA_PROJETOS)
            if st.button("Gravar Projeto"):
                registrar_mudanca(sel_u, f"Projeto: {p_sel}"); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "err":
        with st.container(border=True):
            st.subheader("⚠️ Relatar Erro ou Novidade")
            tf, te = st.tabs(["📝 Preencher", "📖 Exemplo"])
            with tf:
                tipo = st.radio("Tipo:", ["Erro", "Novidade"], horizontal=True)
                txt = st.text_area("Detalhes:", value=(TEMPLATE_ERRO if tipo == "Erro" else ""), height=200)
                if st.button("Enviar"):
                    if enviar_webhook_erro(tipo, sel_u, txt):
                        st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
            with te: st.info("Siga o padrão:"); st.markdown("...Exemplo de Procuradorias...")

    st.markdown("---")
    # Barra de Ferramentas (Erro/Novidade por extenso)
    tcols = st.columns(6)
    tcols[0].button("📑 Checklist", use_container_width=True)
    tcols[1].button("🆘 Chamados", use_container_width=True)
    tcols[2].button("📝 Atendimento", use_container_width=True)
    tcols[3].button("⏰ H. Extras", use_container_width=True)
    tcols[4].button("🧠 Descanso", use_container_width=True)
    if tcols[5].button("⚠️ Erro/Novidade", use_container_width=True): # NOME EXTENSO
        st.session_state.active_view = "err"; st.rerun()

with col_s:
    st.header("Status da Equipe")
    st.toggle("Auxílio Ativado", key="auxilio_ativo", on_change=save_state)
    st.markdown("---")
    
    # --- FILA NUMERADA ---
    st.subheader(f"✅ Na Fila ({len(st.session_state.bastao_queue)})")
    for idx, n in enumerate(st.session_state.bastao_queue):
        cn, cc = st.columns([0.8, 0.2])
        pref = "🥂 " if st.session_state.status_texto[n] == "Bastão" else f"{idx+1}º "
        cn.markdown(f"**{pref}{n}**")
        cc.checkbox(" ", key=f"chk_{n}", value=True, on_change=update_queue_callback, args=(n,))

    # --- SEÇÃO PROJETOS ---
    prjs = [n for n, s in st.session_state.status_texto.items() if "Projeto:" in s]
    st.subheader(f"📁 Projetos ({len(prjs)})")
    for n in prjs:
        st.markdown(f"**{n}** :violet-background[{st.session_state.status_texto[n].replace('Projeto: ', '')}]", unsafe_allow_html=True)

# RESET 20:00
if datetime.now().hour >= 20 and st.session_state.report_last_run_date < date.today():
    st.session_state.status_texto = {n: 'Ausente' for n in CONSULTORES}
    st.session_state.bastao_queue = []
    st.session_state.report_last_run_date = date.today(); save_state(); st.rerun()
