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

# --- Constantes de Consultores (Mantendo sua lista original) ---
CONSULTORES = sorted([
  "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

# --- NOVAS CONSTANTES ---
LISTA_PROJETOS = ["Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", "IA nos Cartórios", "Notebook Lm"]
TEMPLATE_ERRO = """TITULO: 
OBJETIVO: 
RELATO DO ERRO/TESTE: 
RESULTADO: 
OBSERVAÇÃO (SE TIVER): """

EXEMPLO_TEXTO = """**TITULO** - Melhoria na Gestão das Procuradorias
**OBJETIVO**
Permitir que os perfis de Procurador Chefe e Gerente de Procuradoria possam gerenciar os usuários das procuradorias...
**RELATO DO TESTE**
Foram realizados testes no menu “Gerenciar Procuradores”...
**RESULTADO**
O teste não foi bem-sucedido: erro ao cadastrar novos usuários."""

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
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"

# Opções...
REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]
OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"]

# Estilo e GIFs
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
PUG2026_FILENAME = "pug2026.png"
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
STATUSES_DE_SAIDA = ['Atendimento', 'Almoço', 'Saída rápida', 'Ausente', 'Sessão', 'Projeto']

# ============================================
# 2. FUNÇÕES AUXILIARES (Mantidas Originais)
# ============================================

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception: return None

def date_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    if isinstance(obj, timedelta): return obj.total_seconds()
    return str(obj)

def save_state():
    global_data = get_global_state_cache()
    try:
        for k in global_data.keys():
            if k in st.session_state: global_data[k] = st.session_state[k]
        global_data['daily_logs'] = json.loads(json.dumps(st.session_state.daily_logs, default=date_serializer))
    except Exception as e: print(f'Erro save: {e}')

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
        msg = {"text": f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}"}
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, msg)).start()

def render_fireworks():
    st.markdown("""<style>@keyframes firework { 0% { transform: translate(var(--x), 60vmin); width: 0.5vmin; opacity: 1; } 100% { width: 45vmin; opacity: 0; } } .firework { --color1: #ff0000; --color2: #ffd700; position: absolute; top: 50%; left: 50%; animation: firework 2s infinite; background: radial-gradient(circle, var(--color1) 0.2vmin, #0000 0) 50% 0%; background-size: 0.5vmin 0.5vmin; background-repeat: no-repeat; }</style><div class="firework"></div>""", unsafe_allow_html=True)

# ============================================
# 3. LÓGICA DE NEGÓCIO (Revisada)
# ============================================

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    num = len(queue)
    next_idx = (current_index + 1) % num
    attempts = 0
    while attempts < num:
        c = queue[next_idx]
        if not skips.get(c, False) and st.session_state.get(f'check_{c}'): return next_idx
        next_idx = (next_idx + 1) % num
        attempts += 1
    return -1

def check_and_assume_baton():
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    is_current_valid = (current_holder and current_holder in queue and st.session_state.get(f'check_{current_holder}'))
    
    if not current_holder and queue:
        idx = find_next_holder_index(-1, queue, skips)
        if idx != -1:
            target = queue[idx]
            st.session_state.status_texto[target] = 'Bastão'
            st.session_state.bastao_start_time = datetime.now()
            send_chat_notification_internal(target, 'Bastão')
            save_state()

def update_queue(consultor):
    is_checked = st.session_state.get(f'check_{consultor}')
    old_s = st.session_state.status_texto.get(consultor, '')
    dur = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())
    
    if is_checked:
        log_status_change(consultor, old_s, '', dur)
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    else:
        if old_s not in STATUSES_DE_SAIDA and old_s != 'Bastão': 
            log_status_change(consultor, old_s, 'Indisponível', dur)
            st.session_state.status_texto[consultor] = 'Indisponível'
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
    
    check_and_assume_baton()
    save_state()

def rotate_bastao():
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if not current_holder: return
    queue = st.session_state.bastao_queue
    idx = queue.index(current_holder)
    next_idx = find_next_holder_index(idx, queue, st.session_state.skip_flags)
    if next_idx != -1:
        new_h = queue[next_idx]
        dur = datetime.now() - st.session_state.bastao_start_time
        log_status_change(current_holder, 'Bastão', '', dur)
        st.session_state.status_texto[current_holder] = ''
        st.session_state.status_texto[new_h] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.rotation_gif_start_time = datetime.now()
        st.balloons()
        save_state()

# ============================================
# 4. EXECUÇÃO PRINCIPAL (Interface Unificada)
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
if 'status_texto' not in st.session_state:
    for k, v in load_state().items(): st.session_state[k] = v
    st.session_state.active_view = None

st_autorefresh(interval=8000, key="refresh")
render_fireworks()

# Cabeçalho Lado a Lado
c_top_l, c_top_r = st.columns([2, 1], vertical_alignment="bottom")
with c_top_l:
    img_b64 = get_img_as_base64(PUG2026_FILENAME)
    src = f"data:image/png;base64,{img_b64}" if img_b64 else GIF_BASTAO_HOLDER
    st.markdown(f'<div style="display:flex;align-items:center;gap:15px;"><h1 style="color:#FFD700;margin:0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{src}" style="width:100px;height:100px;border-radius:50%;border:3px solid #FFD700;object-fit:cover;"></div>', unsafe_allow_html=True)

with c_top_r:
    ce1, ce2 = st.columns([2, 1], vertical_alignment="bottom")
    nv = ce1.selectbox("Assumir Rápido", options=["Selecione"] + CONSULTORES, label_visibility="collapsed")
    if ce2.button("🚀 Entrar"):
        if nv != "Selecione":
            st.session_state[f'check_{nv}'] = True
            update_queue(nv); st.rerun()

st.markdown("<hr style='border:1px solid #FFD700;margin:5px 0 20px 0;'>", unsafe_allow_html=True)

col_p, col_d = st.columns([1.5, 1])

with col_p:
    # Banner Responsável
    resp = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável pelo Bastão")
    if resp:
        st.markdown(f'<div style="background:linear-gradient(135deg,#FFF8DC 0%,#FFFFFF 100%);border:3px solid #FFD700;padding:20px;border-radius:15px;display:flex;align-items:center;"><img src="{GIF_BASTAO_HOLDER}" style="width:80px;height:80px;border-radius:50%;margin-right:25px;"><span style="font-size:38px;font-weight:bold;color:#000080;">{resp}</span></div>', unsafe_allow_html=True)
    
    st.subheader("Consultor(a)")
    st.selectbox('Selecione seu nome:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    st.markdown("**Ações Principais:**")
    # EXPANDIDO PARA 8 COLUNAS PARA INCLUIR PROJETOS
    c_btn = st.columns(8)
    c_btn[0].button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    c_btn[1].button('⏭️ Pular', on_click=lambda: st.session_state.skip_flags.update({st.session_state.consultor_selectbox: True}), use_container_width=True)
    c_btn[2].button('📋 Atividades', on_click=lambda: st.session_state.update({'active_view': 'atv'}), use_container_width=True)
    c_btn[3].button('🍽️ Almoço', on_click=lambda: st.session_state.update({'status_texto': {**st.session_state.status_texto, st.session_state.consultor_selectbox: 'Almoço'}}), use_container_width=True)
    c_btn[4].button('👤 Ausente', on_click=lambda: st.session_state.update({'status_texto': {**st.session_state.status_texto, st.session_state.consultor_selectbox: 'Ausente'}}), use_container_width=True)
    c_btn[5].button('🎙️ Sessão', on_click=lambda: st.session_state.update({'active_view': 'ses'}), use_container_width=True)
    c_btn[6].button('🚶 Saída', on_click=lambda: st.session_state.update({'status_texto': {**st.session_state.status_texto, st.session_state.consultor_selectbox: 'Saída rápida'}}), use_container_width=True)
    # BOTÃO PROJETOS
    if c_btn[7].button('📁 Projetos', use_container_width=True): st.session_state.active_view = 'prj'

    # Views Dinâmicas
    if st.session_state.active_view == 'prj':
        with st.container(border=True):
            p_sel = st.selectbox("Escolha o Projeto:", LISTA_PROJETOS)
            if st.button("Confirmar Projeto"):
                st.session_state.status_texto[st.session_state.consultor_selectbox] = f"Projeto: {p_sel}"
                st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'err':
        with st.container(border=True):
            st.subheader("⚠️ Relatar Erro ou Novidade")
            t1, t2 = st.tabs(["📝 Preencher", "📖 Exemplo"])
            with t1:
                tipo = st.radio("Tipo:", ["Erro", "Novidade"], horizontal=True)
                txt = st.text_area("Descreva:", value=(TEMPLATE_ERRO if tipo == "Erro" else ""), height=200)
                if st.button("Enviar"):
                    threading.Thread(target=_send_webhook_thread, args=(WEBHOOK_ERROS, {"text": f"🚨 {tipo} por {st.session_state.consultor_selectbox}\n{txt}"})).start()
                    st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
            with t2: st.markdown(EXEMPLO_TEXTO)

    st.markdown("---")
    # FERRAMENTAS INFERIORES (6 COLUNAS)
    t_cols = st.columns(6)
    t_cols[0].button("📑 Checklist", use_container_width=True)
    t_cols[1].button("🆘 Chamados", use_container_width=True)
    t_cols[2].button("📝 Atendimento", use_container_width=True)
    t_cols[3].button("⏰ H. Extras", use_container_width=True)
    t_cols[4].button("🧠 Descanso", use_container_width=True)
    # BOTÃO ERRO/NOVIDADE POR EXTENSO
    if t_cols[5].button("⚠️ Erro/Novidade", use_container_width=True): 
        st.session_state.active_view = 'err'; st.rerun()

with col_d:
    st.toggle("Auxílio Ativado", key='auxilio_ativo', on_change=save_state)
    st.markdown("---")
    st.header('Status da Equipe')
    
    # Lógica de categorização lateral
    ui = {'fila': [], 'prj': [], 'demanda': []}
    for n in CONSULTORES:
        s = st.session_state.status_texto.get(n, 'Indisponível')
        if s == 'Bastão' or s == '': ui['fila'].append(n)
        elif s.startswith('Projeto:'): ui['prj'].append((n, s.replace('Projeto: ', '')))
        else: ui['demanda'].append(n)

    # ✅ NA FILA (ESTRUTURA ORIGINAL PRESERVADA)
    st.subheader(f'✅ Na Fila ({len(ui["fila"])})')
    for n in ui['fila']:
        cn, cc = st.columns([0.8, 0.2])
        cc.checkbox(' ', key=f'check_{n}', value=True, on_change=update_queue, args=(n,))
        if n == resp: cn.markdown(f'<span style="background-color:#FFD700;padding:2px 5px;border-radius:5px;">🥂 {n}</span>', unsafe_allow_html=True)
        elif st.session_state.skip_flags.get(n): cn.write(f"**{n}** :orange-background[Pulando ⏭️]")
        else: cn.write(f"**{n}** :blue-background[Aguardando]")

    # 📁 EM PROJETO (NOVA SEÇÃO SOLICITADA)
    st.divider()
    st.subheader(f'📁 Em Projeto ({len(ui["prj"])})')
    for n, p in ui['prj']:
        cn, cc = st.columns([0.8, 0.2])
        cc.checkbox(' ', key=f'check_{n}', value=False, on_change=update_queue, args=(n,))
        cn.markdown(f"**{n}** :violet-background[{p}]", unsafe_allow_html=True)

    st.divider()
    st.subheader(f'📋 Demanda/Outros ({len(ui["demanda"])})')
    for n in ui['demanda']:
        cn, cc = st.columns([0.8, 0.2])
        cc.checkbox(' ', key=f'check_{n}', value=False, on_change=update_queue, args=(n,))
        cn.caption(f"{n}: {st.session_state.status_texto[n]}")
