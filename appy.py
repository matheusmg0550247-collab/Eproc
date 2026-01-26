# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json
import base64
import io
import altair as alt
from supabase import create_client
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Importação condicional
try:
    from streamlit_javascript import st_javascript
except ImportError:
    st_javascript = None

# Importações de utilitários
from utils import (get_brazil_time, get_secret, send_to_chat)

# ============================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ============================================
CONSULTORES = sorted([
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", 
    "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", 
    "Michael Douglas", "Morôni", "Pablo Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]
OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]

GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
PUG2026_FILENAME = "pug2026.png"
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'

# Secrets
CHAT_WEBHOOK_BASTAO = get_secret("chat", "bastao")
WEBHOOK_STATE_DUMP = get_secret("webhook", "test_state")

# ============================================
# 2. BANCO DE DADOS & CACHE
# ============================================

def get_supabase():
    try: 
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.error(f"Erro Conexão DB: {e}") 
        return None

@st.cache_data(ttl=86400, show_spinner=False)
def carregar_dados_grafico():
    sb = get_supabase()
    if not sb: return None, None
    try:
        res = sb.table("atendimentos_resumo").select("data").eq("id", 2).execute()
        if res.data:
            json_data = res.data[0]['data']
            if 'totais_por_relatorio' in json_data:
                df = pd.DataFrame(json_data['totais_por_relatorio'])
                return df, json_data.get('gerado_em', '-')
    except: return None, None

@st.cache_data
def get_img_as_base64_cached(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return None

# --- SERIALIZADOR SEGURO (FIM DOS ERROS DE DATA) ---
def safe_serialize(obj):
    """Converte datas e durações para texto/número antes de salvar"""
    if isinstance(obj, dict):
        return {k: safe_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_serialize(i) for i in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return obj.total_seconds()
    return obj

def load_state_from_db():
    sb = get_supabase()
    if not sb: return {}
    try:
        # Busca ID 1 (padrão limpo)
        response = sb.table("app_state").select("data").eq("id", 1).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("data", {})
        return {}
    except Exception as e:
        st.error(f"Erro Leitura DB: {e}")
        return {}

def save_state_to_db(state_data):
    sb = get_supabase()
    if not sb: return
    try:
        # Limpa dados antes de enviar
        clean_data = safe_serialize(state_data)
        sb.table("app_state").upsert({"id": 1, "data": clean_data}).execute()
    except Exception as e:
        st.error(f"🔥 ERRO SALVAR: {e}")

# ============================================
# 3. UTILITÁRIOS
# ============================================
def get_browser_id():
    if st_javascript is None: return "no_js"
    js_code = """(function(){let id=localStorage.getItem("device_id");if(!id){id="id_"+Math.random().toString(36).substr(2,9);localStorage.setItem("device_id",id);}return id;})();"""
    try: return st_javascript(js_code, key="device_tag")
    except: return "unknown"

def get_remote_ip():
    try:
        from streamlit.web.server.websocket_headers import ClientWebSocketRequest
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and ctx.session_id:
            session_info = st.runtime.get_instance().get_client(ctx.session_id)
            if session_info:
                req = session_info.request
                if isinstance(req, ClientWebSocketRequest):
                    if 'X-Forwarded-For' in req.headers: return req.headers['X-Forwarded-For'].split(',')[0]
                    return req.remote_ip
    except: pass
    return "Unknown"

# Lógica Visual da Fila
def get_ordered_visual_queue(queue, status_dict):
    if not queue: return []
    current = next((c for c, s in status_dict.items() if 'Bastão' in (s or '')), None)
    if not current or current not in queue: return list(queue)
    try:
        idx = queue.index(current)
        return queue[idx:] + queue[:idx]
    except: return list(queue)

# ============================================
# 4. LÓGICA DE NEGÓCIO (BASTÃO)
# ============================================
def init_session_state():
    dev_id = get_browser_id()
    if dev_id: st.session_state['device_id_val'] = dev_id

    if 'db_loaded' not in st.session_state:
        db_data = load_state_from_db()
        if db_data:
            for k, v in db_data.items(): st.session_state[k] = v
        st.session_state['db_loaded'] = True
    
    # Conversão de volta para datetime ao carregar (se necessário)
    if 'report_last_run_date' in st.session_state and isinstance(st.session_state['report_last_run_date'], str):
        try: st.session_state['report_last_run_date'] = datetime.fromisoformat(st.session_state['report_last_run_date'])
        except: st.session_state['report_last_run_date'] = datetime.min
        
    now = get_brazil_time()
    defaults = {
        'bastao_start_time': None, 'report_last_run_date': datetime.min,
        'consultor_selectbox': "Selecione um nome", 
        'status_texto': {n: 'Indisponível' for n in CONSULTORES},
        'bastao_queue': [], 'skip_flags': {}, 
        'current_status_starts': {n: now for n in CONSULTORES},
        'bastao_counts': {n: 0 for n in CONSULTORES}, 
        'priority_return_queue': [], 'daily_logs': [], 'previous_states': {},
        'active_view': None, 'chamado_guide_step': 0
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v
    
    # Restaura status lógicos
    for n in CONSULTORES:
        st.session_state.bastao_counts.setdefault(n, 0)
        st.session_state.skip_flags.setdefault(n, False)
        status = st.session_state.status_texto.get(n, 'Indisponível')
        is_avail = (n in st.session_state.bastao_queue)
        st.session_state[f'check_{n}'] = is_avail
        
        # Converte strings de data de volta para datetime se vieram do banco
        if n in st.session_state.current_status_starts:
            val = st.session_state.current_status_starts[n]
            if isinstance(val, str):
                try: st.session_state.current_status_starts[n] = datetime.fromisoformat(val)
                except: st.session_state.current_status_starts[n] = now

def save_state():
    # Prepara o estado para salvar
    state = {
        'status_texto': st.session_state.status_texto,
        'bastao_queue': st.session_state.bastao_queue,
        'skip_flags': st.session_state.skip_flags,
        'current_status_starts': st.session_state.current_status_starts,
        'bastao_counts': st.session_state.bastao_counts,
        'priority_return_queue': st.session_state.priority_return_queue,
        'bastao_start_time': st.session_state.bastao_start_time,
        'report_last_run_date': st.session_state.report_last_run_date,
        'daily_logs': st.session_state.daily_logs,
        'previous_states': st.session_state.previous_states
    }
    save_state_to_db(state)

def log_change(consultor, old, new):
    now = get_brazil_time()
    # Calcula duração segura (mesmo se data inicial estiver zuada)
    start = st.session_state.current_status_starts.get(consultor, now)
    if not isinstance(start, datetime): start = now
    duration = (now - start).total_seconds()
    
    st.session_state.daily_logs.append({
        'timestamp': now, 'consultor': consultor,
        'old': old, 'new': new, 'duration_sec': duration,
        'ip': st.session_state.get('device_id_val', 'unknown')
    })
    st.session_state.current_status_starts[consultor] = now

def check_and_assume_baton(forced_successor=None):
    queue = st.session_state.bastao_queue
    holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    target = None
    if forced_successor: target = forced_successor
    elif holder and holder in queue: target = holder # Mantém se válido
    else:
        # Procura o próximo disponível
        idx = -1
        if holder in queue: idx = queue.index(holder)
        
        # Lógica Circular que aceita 2 pessoas
        if queue:
            start = (idx + 1) % len(queue)
            for i in range(len(queue)):
                curr = (start + i) % len(queue)
                cand = queue[curr]
                if not st.session_state.skip_flags.get(cand, False):
                    target = cand
                    break
    
    changed = False
    now = get_brazil_time()

    # Limpa bastão de quem não é o alvo
    for c in CONSULTORES:
        if c != target and 'Bastão' in st.session_state.status_texto.get(c, ''):
            log_change(c, 'Bastão', 'Indisponível')
            st.session_state.status_texto[c] = 'Indisponível'
            changed = True
            
    # Atribui ao novo alvo
    if target:
        curr_s = st.session_state.status_texto.get(target, '')
        if 'Bastão' not in curr_s:
            new_s = f"Bastão | {curr_s}" if curr_s and curr_s != "Indisponível" else "Bastão"
            log_change(target, curr_s, new_s)
            st.session_state.status_texto[target] = new_s
            st.session_state.bastao_start_time = now
            st.session_state.skip_flags[target] = False
            
            # Notifica se mudou de pessoa
            if holder != target:
                send_chat_notification_internal(target, 'Bastão')
                st.toast(f"Bastão com {target}!", icon="🥂")
            
            changed = True

    if changed: save_state()

def update_status(new_status, indisponivel=False, manter_fila=False):
    sel = st.session_state.consultor_selectbox
    if not sel or sel == 'Selecione um nome': return
    
    curr = st.session_state.status_texto.get(sel, '')
    
    # Memoriza estado para almoço
    if new_status == 'Almoço':
        st.session_state.previous_states[sel] = {'status': curr, 'in_queue': sel in st.session_state.bastao_queue}
    
    # Lógica de Sair da Fila/Indisponível
    if indisponivel:
        st.session_state.skip_flags[sel] = True
        if sel in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(sel)
            # Se era o dono do bastão, força passar para o próximo
            if 'Bastão' in curr:
                check_and_assume_baton()
    elif not manter_fila:
        if sel not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(sel)
        st.session_state.skip_flags[sel] = False

    # Constrói texto final
    final = new_status
    if sel in st.session_state.bastao_queue:
        holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        if holder == sel:
            final = f"Bastão | {new_status}".strip(" |")
    
    if not final:
        final = '' if sel in st.session_state.bastao_queue else 'Indisponível'
        
    log_change(sel, curr, final)
    st.session_state.status_texto[sel] = final
    save_state()

def rotate():
    sel = st.session_state.consultor_selectbox
    holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    if sel != holder:
        st.error("Só quem está com o bastão pode passar!")
        return

    # Passa o bastão
    st.session_state.bastao_counts[holder] = st.session_state.bastao_counts.get(holder, 0) + 1
    
    # Logica para forçar o próximo (ignora o atual na busca)
    queue = st.session_state.bastao_queue
    if not queue: return
    
    curr_idx = queue.index(holder) if holder in queue else -1
    next_idx = (curr_idx + 1) % len(queue)
    
    # Procura alguém que não pulou
    found = False
    for i in range(len(queue)):
        idx = (next_idx + i) % len(queue)
        cand = queue[idx]
        if not st.session_state.skip_flags.get(cand, False):
             # Força o check_baton a pegar esse cara
             check_and_assume_baton(forced_successor=cand)
             found = True
             break
    
    if not found: st.warning("Todos pularam! O bastão continua aqui.")

def toggle_skip_btn():
    sel = st.session_state.consultor_selectbox
    if sel and sel in st.session_state.bastao_queue:
        st.session_state.skip_flags[sel] = not st.session_state.skip_flags.get(sel, False)
        save_state()
        st.rerun()

def toggle_presence():
    sel = st.session_state.consultor_selectbox
    if not sel or sel == 'Selecione um nome': return
    
    if sel in st.session_state.bastao_queue:
        # Sai da fila
        st.session_state.bastao_queue.remove(sel)
        update_status('Indisponível', indisponivel=True)
    else:
        # Entra na fila
        st.session_state.bastao_queue.append(sel)
        update_status('')

def manual_refresh():
    st.session_state.db_loaded = False # Força recarga do banco
    st.rerun()

# ============================================
# 5. INTERFACE
# ============================================
st.set_page_config(page_title="Bastão 2026", layout="wide", page_icon="🥂")
st.markdown("""<style>div.stButton > button {width: 100%; white-space: nowrap; height: 3rem;}</style>""", unsafe_allow_html=True)

init_session_state()
# Auto-refresh visual
if st.session_state.active_view is None: st_autorefresh(interval=10000, key='auto')

# Topo
c1, c2 = st.columns([3, 1])
with c1:
    img = get_img_as_base64_cached(PUG2026_FILENAME)
    src = f"data:image/png;base64,{img}" if img else GIF_BASTAO_HOLDER
    st.markdown(f"### Controle Bastão Cesupe 2026 {BASTAO_EMOJI}")
with c2:
    st.caption(f"ID: {st.session_state.get('device_id_val','...')[-4:]}")

st.divider()

# Layout Principal
col_main, col_list = st.columns([1.5, 1])

with col_main:
    # Quem está com bastão
    holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), "Ninguém")
    st.info(f"**Bastão Atual:** {holder}")
    
    # Próximos
    q = st.session_state.bastao_queue
    vis_q = get_ordered_visual_queue(q, st.session_state.status_texto)
    prox = [p for p in vis_q if p != holder and not st.session_state.skip_flags.get(p)]
    pularam = [p for p in q if st.session_state.skip_flags.get(p)]
    
    st.markdown(f"**Próximo:** {prox[0] if prox else '---'}")
    if pularam: st.caption(f"Pulando: {', '.join(pularam)}")

    st.divider()
    
    # Controles
    st.selectbox("Consultor:", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox", label_visibility="collapsed")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.button("🥂 Entrar/Sair", on_click=toggle_presence, use_container_width=True)
    c2.button("🎯 Passar", on_click=rotate, use_container_width=True)
    c3.button("⏭️ Pular", on_click=toggle_skip_btn, use_container_width=True)
    c4.button("🔄 Atualizar", on_click=manual_refresh, use_container_width=True)
    
    # Grid de Ações
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    if r1c1.button("📋 Atividades"): st.session_state.active_view = 'ativ'
    if r1c2.button("🏗️ Projeto"): st.session_state.active_view = 'proj'
    if r1c3.button("🎓 Treino"): st.session_state.active_view = 'treino'
    r1c4.button("🍽️ Almoço", on_click=update_status, args=('Almoço', True))
    
    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    if r2c1.button("🎙️ Sessão"): st.session_state.active_view = 'sessao'
    r2c2.button("🚶 Saída", on_click=update_status, args=('Saída rápida', True))
    r2c3.button("🏃 Sair Bastão", on_click=update_status, args=('Ausente', True))
    if r2c4.button("🤝 Presencial"): st.session_state.active_view = 'pres'
    
    # Menus Expansíveis
    if st.session_state.active_view == 'ativ':
        with st.container(border=True):
            tipo = st.multiselect("Tipo", OPCOES_ATIVIDADES_STATUS)
            det = st.text_input("Detalhe")
            c1, c2 = st.columns(2)
            if c1.button("Gravar", type="primary"):
                update_status(f"Atividade: {','.join(tipo)} {det}", manter_fila=True)
                st.session_state.active_view = None
                st.rerun()
            if c2.button("Sair de atividades"):
                update_status("", manter_fila=True)
                st.session_state.active_view = None
                st.rerun()
                
    if st.session_state.active_view == 'sessao':
        with st.container(border=True):
            cam = st.text_input("Câmara/Sessão")
            obs = st.text_input("Obs")
            if st.button("Confirmar", type="primary"):
                update_status(f"Sessão: {cam} {obs}", indisponivel=True)
                st.session_state.active_view = None
                st.rerun()
                
    # Ferramentas extras (Checklist, Certidão, etc) mantidas simplificadas
    with st.expander("🛠️ Ferramentas"):
        t1, t2 = st.tabs(["Certidão", "Chamado"])
        with t1:
            st.write("Gerador de Certidão")
            if st.button("Salvar Certidão"):
                salvar_certidao_db({'tipo':'Teste', 'consultor': st.session_state.consultor_selectbox})
                st.success("Salvo!")
        with t2:
            st.write("Gerador de Chamado")

with col_list:
    st.markdown("### Status")
    
    # Renderiza Fila
    st.markdown("#### ✅ Fila")
    for p in vis_q:
        if p == holder:
            st.markdown(f"**🥂 {p}** (Bastão)")
        elif st.session_state.skip_flags.get(p):
            st.markdown(f"⏭️ {p} (Pulando)")
        else:
            st.markdown(f"🔹 {p}")
            
    st.divider()
    
    # Renderiza os demais status agrupados
    grupos = {}
    for c in CONSULTORES:
        if c in q: continue # Já mostrou na fila
        s = st.session_state.status_texto.get(c, 'Indisponível')
        if s == '' or s is None: s = 'Indisponível'
        
        # Simplifica status para agrupamento
        key = s.split(':')[0].split('|')[-1].strip()
        if key not in grupos: grupos[key] = []
        grupos[key].append(c)
        
    for k, lista in grupos.items():
        if k == 'Indisponível': icon = '❌'
        elif 'Almoço' in k: icon = '🍽️'
        elif 'Sessão' in k: icon = '🎙️'
        else: icon = '🔸'
        
        st.markdown(f"**{icon} {k}**")
        for p in lista:
            st.caption(f"{p}")

# Gráfico
st.divider()
df_chart, dt = carregar_dados_grafico()
if df_chart is not None:
    st.caption(f"Dados atualizados em: {dt}")
    st.bar_chart(df_chart, x='relatorio', y='Qtd', color='Sistema')
