# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json
import base64
import io
from supabase import create_client
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Importações locais
from repository import load_state_from_db, save_state_to_db
from utils import (get_brazil_time, get_secret, send_to_chat, get_img_as_base64)

# ============================================
# 1. CONFIGURAÇÕES
# ============================================
CONSULTORES = sorted([
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
    "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
    "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
])

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
OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]
OPCOES_PROJETOS = ["Soma", "Treinamentos Eproc", "Manuais Eproc", "Cartilhas Gabinetes", "Notebook Lm", "Inteligência artifical cartórios"]

GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
PUG2026_FILENAME = "pug2026.png"

GOOGLE_CHAT_WEBHOOK_BACKUP = get_secret("chat", "backup")
CHAT_WEBHOOK_BASTAO = get_secret("chat", "bastao")
GOOGLE_CHAT_WEBHOOK_REGISTRO = get_secret("chat", "registro")
SHEETS_WEBHOOK_URL = get_secret("sheets", "url")

# --- CONEXÃO SUPABASE ---
def get_supabase():
    try: return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except: return None

# --- LÓGICA DE BANCO PARA CERTIDÕES ---
def verificar_duplicidade_certidao(tipo, n_processo=None, data_evento=None, hora_periodo=None):
    sb = get_supabase()
    if not sb: return False
    try:
        query = sb.table("certidoes_registro").select("*").eq("tipo", tipo)
        if tipo in ['Física', 'Eletrônica'] and n_processo:
            proc_limpo = str(n_processo).strip().rstrip('.')
            response = query.ilike("n_processo", f"%{proc_limpo}%").execute()
            return len(response.data) > 0
        elif tipo == 'Geral' and data_evento:
            data_str = data_evento.isoformat() if hasattr(data_evento, 'isoformat') else str(data_evento)
            query = query.eq("data_evento", data_str)
            if hora_periodo: query = query.eq("hora_periodo", hora_periodo)
            response = query.execute()
            return len(response.data) > 0
    except: return False
    return False

def salvar_certidao_db(dados):
    sb = get_supabase()
    if not sb: return False
    try:
        sb.table("certidoes_registro").insert(dados).execute()
        return True
    except: return False

# --- GERADOR DE WORD OFICIAL ---
def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado=""):
    try:
        doc = Document()
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Arial'
        font.size = Pt(11)

        head = doc.add_paragraph()
        head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = head.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        run.bold = True
        head.add_run("Rua Ouro Preto, Nº 1564 - Bairro Santo Agostinho - CEP 30170-041\nBelo Horizonte - MG - www.tjmg.jus.br\nAndar: 3º e 4º PV")
        
        doc.add_paragraph("\n")
        p_num = doc.add_paragraph("Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2025.")
        p_num.runs[0].bold = True
        
        doc.add_paragraph("Assunto: Notifica erro no \"JPe - 2ª Instância\" ao peticionar.")
        
        data_atual = datetime.now().strftime("%d de %B de %Y")
        doc.add_paragraph(f"\nExmo(a). Senhor(a) Relator(a),\n\nBelo Horizonte, {data_atual}")
        
        corpo = doc.add_paragraph()
        corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        corpo.add_run(f"Informamos que na data de {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}.\n\n")
        
        ref_chamado = chamado if chamado else "de número informado no registro"
        corpo.add_run(f"O Chamado {ref_chamado}, foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
        
        if tipo == 'Física':
            corpo.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.\n\n")
        else:
            corpo.add_run("Informamos a indisponibilidade para fins de restituição de prazo ou providências que V.Exa julgar necessárias, nos termos da legislação vigente.\n\n")
            
        corpo.add_run("Colocamo-nos à disposição para outras informações que se fizerem necessárias.")
        doc.add_paragraph("\nRespeitosamente,")
        doc.add_paragraph("\n\n___________________________________\nWaner Andrade Silva\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD\nDiretoria Executiva de Tecnologia da Informação e Comunicação - DIRTEC")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erro ao gerar Word: {e}")
        return None

# ============================================
# 3. LÓGICA DE ESTADO (FILA/BASTÃO)
# ============================================
def save_state():
    try:
        last_run = st.session_state.report_last_run_date
        last_run_iso = last_run.isoformat() if isinstance(last_run, datetime) else datetime.min.isoformat()
        state_to_save = {
            'status_texto': st.session_state.status_texto, 'bastao_queue': st.session_state.bastao_queue,
            'skip_flags': st.session_state.skip_flags, 'current_status_starts': st.session_state.current_status_starts,
            'bastao_counts': st.session_state.bastao_counts, 'priority_return_queue': st.session_state.priority_return_queue,
            'bastao_start_time': st.session_state.bastao_start_time, 'report_last_run_date': last_run_iso, 
            'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'), 'daily_logs': st.session_state.daily_logs
        }
        save_state_to_db(state_to_save)
    except: pass

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def log_status_change(consultor, old_status, new_status, duration):
    now_br = get_brazil_time()
    entry = {'timestamp': now_br, 'consultor': consultor, 'old_status': old_status, 'new_status': new_status, 'duration': duration}
    st.session_state.daily_logs.append(entry)
    st.session_state.current_status_starts[consultor] = now_br

# --- FILA BLINDADA ---
def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue)
    start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        if not skips.get(queue[idx], False): return idx
    return (current_index + 1) % n if n > 1 else -1

def check_and_assume_baton(forced_successor=None):
    queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    target = forced_successor if forced_successor else (current_holder if current_holder in queue else None)
    if not target and queue:
        curr_idx = queue.index(current_holder) if current_holder in queue else -1
        idx = find_next_holder_index(curr_idx, queue, skips)
        target = queue[idx] if idx != -1 else None
    now = get_brazil_time()
    for c in CONSULTORES:
        if c != target and 'Bastão' in st.session_state.status_texto.get(c, ''):
            st.session_state.status_texto[c] = 'Indisponível'
    if target and 'Bastão' not in st.session_state.status_texto.get(target, ''):
        st.session_state.status_texto[target] = 'Bastão'
        st.session_state.bastao_start_time = now
    save_state()

def toggle_queue(consultor):
    if consultor in st.session_state.bastao_queue:
        st.session_state.bastao_queue.remove(consultor)
        st.session_state.status_texto[consultor] = 'Indisponível'
    else:
        st.session_state.bastao_queue.append(consultor)
        st.session_state.status_texto[consultor] = ''
    check_and_assume_baton()
    st.rerun()

def update_status(new_status, exit_queue=False):
    selected = st.session_state.consultor_selectbox
    if selected == 'Selecione um nome': return
    if exit_queue and selected in st.session_state.bastao_queue:
        st.session_state.bastao_queue.remove(selected)
    st.session_state.status_texto[selected] = new_status
    check_and_assume_baton()
    st.rerun()

def init_session_state():
    if 'db_loaded' not in st.session_state:
        db_data = load_state_from_db()
        if db_data:
            for k, v in db_data.items(): st.session_state[k] = v
        st.session_state['db_loaded'] = True
    defaults = {
        'status_texto': {n: 'Indisponível' for n in CONSULTORES}, 'bastao_queue': [], 'skip_flags': {},
        'current_status_starts': {n: get_brazil_time() for n in CONSULTORES}, 'daily_logs': [],
        'bastao_start_time': None, 'report_last_run_date': datetime.min, 'active_view': None
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

# ============================================
# 4. INTERFACE
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
st_autorefresh(interval=10000, key='auto')

st.title(f"Controle Bastão Cesupe 2026 {BASTAO_EMOJI}")

col_main, col_side = st.columns([2, 1])

with col_main:
    st.header("Ações do Consultor")
    st.selectbox("Selecione seu nome:", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox")
    
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🥂 Assumir/Fila", use_container_width=True): toggle_queue(st.session_state.consultor_selectbox)
    if c2.button("🍽️ Almoço", use_container_width=True): update_status("Almoço", True)
    if c3.button("📋 Atividades", use_container_width=True): st.session_state.active_view = "atividades"
    if c4.button("🖨️ Certidão", use_container_width=True): st.session_state.active_view = "certidao"

    if st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.subheader("Gerador de Certidões")
            tipo = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"])
            c_proc = st.text_input("Nº Processo:")
            c_cham = st.text_input("Nº Chamado:")
            c_mot = st.text_area("Descrição do Erro:")
            
            c_act1, c_act2 = st.columns(2)
            if c_act1.button("📄 Gerar Word (Sem Salvar)", use_container_width=True):
                if not c_proc: st.error("Informe o processo.")
                else:
                    doc = gerar_docx_certidao_internal(tipo, c_proc, get_brazil_time().strftime("%d/%m/%Y"), st.session_state.consultor_selectbox, c_mot, c_cham)
                    if doc: st.download_button("⬇️ Baixar DOCX", doc, "certidao.docx")
            
            if c_act2.button("💾 Salvar no Banco", type="primary", use_container_width=True):
                if verificar_duplicidade_certidao(tipo, c_proc):
                    st.error("⚠️ Certidão já existe! Falar com Matheus ou Gilberto.")
                else:
                    payload = {"tipo": tipo, "n_processo": c_proc.strip().rstrip('.'), "n_chamado": c_cham, "motivo": c_mot, "consultor": st.session_state.consultor_selectbox, "data_evento": get_brazil_time().isoformat()}
                    if salvar_certidao_db(payload):
                        st.success("Salvo com sucesso!")
                        st.session_state.active_view = None
                        st.rerun()

with col_side:
    st.header("Status Atual")
    for n in CONSULTORES:
        status = st.session_state.status_texto.get(n, "Indisponível")
        cor = "gold" if "Bastão" in status else "white"
        st.markdown(f"<div style='background:{cor}; padding:5px; border-radius:5px; color:black; margin-bottom:5px;'><strong>{n}</strong>: {status}</div>", unsafe_allow_html=True)
