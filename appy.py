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
# 1. CONFIGURAÇÕES E CONSTANTES
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

# ============================================
# 2. LÓGICA DE BANCO E CERTIDÕES
# ============================================

def verificar_duplicidade_certidao(tipo, n_processo=None, data_evento=None, hora_periodo=None):
    sb = get_supabase()
    if not sb: return False
    try:
        query = sb.table("certidoes_registro").select("*").eq("tipo", tipo)
        if tipo in ['Física', 'Eletrônica'] and n_processo:
            # Limpa input para busca (remove ponto e espaços)
            proc_limpo = str(n_processo).strip().rstrip('.')
            # Busca usando ILIKE para ignorar se o banco tem ponto ou não
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
    except Exception as e:
        print(f"Erro ao salvar: {e}")
        return False

def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado=""):
    try:
        doc = Document()
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Arial'
        font.size = Pt(11)

        # Cabeçalho Centralizado
        head = doc.add_paragraph()
        head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_head = head.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        run_head.bold = True
        head.add_run("Rua Ouro Preto, Nº 1564 - Bairro Santo Agostinho - CEP 30170-041\nBelo Horizonte - MG - www.tjmg.jus.br\nAndar: 3º e 4º PV")
        
        doc.add_paragraph("\n")
        
        # Título do Parecer
        p_num = doc.add_paragraph("Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2025.")
        p_num.runs[0].bold = True
        
        doc.add_paragraph("Assunto: Notifica erro no \"JPe - 2ª Instância\" ao peticionar.")
        
        data_atual = datetime.now().strftime("%d de %B de %Y")
        doc.add_paragraph(f"\nExmo(a). Senhor(a) Relator(a),\n\nBelo Horizonte, {data_atual}")
        
        # Corpo do Texto Justificado
        corpo = doc.add_paragraph()
        corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        corpo.add_run(f"Informamos que na data de {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}.\n\n")
        
        c_ref = chamado if chamado else "de número informado no registro"
        corpo.add_run(f"O Chamado {c_ref}, foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
        
        if tipo == 'Física':
            corpo.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.\n\n")
        else:
            corpo.add_run("Informamos a indisponibilidade para fins de restituição de prazo ou providências que V.Exa julgar necessárias, nos termos da legislação vigente.\n\n")
            
        corpo.add_run("Colocamo-nos à disposição para outras informações que se fizerem necessárias.")
        
        doc.add_paragraph("\nRespeitosamente,")
        
        # Assinatura
        doc.add_paragraph("\n\n___________________________________\nWaner Andrade Silva\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD\nDiretoria Executiva de Tecnologia da Informação e Comunicação - DIRTEC")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(e)
        return None

# ============================================
# 3. LÓGICA DE FILA E ESTADO
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

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    now_br = get_brazil_time()
    entry = {'timestamp': now_br, 'consultor': consultor, 'old_status': old_status, 'new_status': new_status, 'duration': duration, 'duration_s': duration.total_seconds()}
    st.session_state.daily_logs.append(entry)
    st.session_state.current_status_starts[consultor] = now_br

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue)
    start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        if not skips.get(queue[idx], False): return idx
    return (current_index + 1) % n if n > 1 else -1

def check_and_assume_baton(forced_successor=None, immune_consultant=None):
    queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    is_valid = (current_holder and current_holder in queue)
    target = forced_successor if forced_successor else (current_holder if is_valid else None)
    
    if not target and queue:
        curr_idx = queue.index(current_holder) if current_holder in queue else -1
        idx = find_next_holder_index(curr_idx, queue, skips)
        target = queue[idx] if idx != -1 else None

    now = get_brazil_time()
    for c in CONSULTORES:
        if c != immune_consultant and c != target and 'Bastão' in st.session_state.status_texto.get(c, ''):
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
    save_state()

def toggle_skip():
    sel = st.session_state.consultor_selectbox
    if sel == 'Selecione um nome': return
    novo = not st.session_state.skip_flags.get(sel, False)
    st.session_state.skip_flags[sel] = novo
    if novo and sel in st.session_state.bastao_queue:
        st.session_state.bastao_queue.remove(sel)
        st.session_state.bastao_queue.append(sel)
    save_state()

def update_status(new_status, force_exit=False):
    sel = st.session_state.consultor_selectbox
    if sel == 'Selecione um nome': return
    if force_exit and sel in st.session_state.bastao_queue:
        st.session_state.bastao_queue.remove(sel)
    st.session_state.status_texto[sel] = new_status
    check_and_assume_baton()

# ============================================
# 4. INTERFACE E EXECUÇÃO
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

if 'db_loaded' not in st.session_state:
    db_data = load_state_from_db()
    if db_data:
        for k, v in db_data.items(): st.session_state[k] = v
    st.session_state['db_loaded'] = True

# Inicialização de variáveis padrão
if 'status_texto' not in st.session_state: st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
if 'bastao_queue' not in st.session_state: st.session_state.bastao_queue = []
if 'skip_flags' not in st.session_state: st.session_state.skip_flags = {}
if 'daily_logs' not in st.session_state: st.session_state.daily_logs = []
if 'current_status_starts' not in st.session_state: st.session_state.current_status_starts = {n: datetime.now() for n in CONSULTORES}
if 'report_last_run_date' not in st.session_state: st.session_state.report_last_run_date = datetime.min
if 'active_view' not in st.session_state: st.session_state.active_view = None

st_autorefresh(interval=10000, key='auto_refresh')

st.title(f"Controle Bastão Cesupe 2026 {BASTAO_EMOJI}")

col_principal, col_status = st.columns([1.8, 1])

with col_principal:
    st.selectbox("Consultor(a):", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox")
    
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    if r1c1.button("🥂 Assumir / Fila", use_container_width=True): toggle_queue(st.session_state.consultor_selectbox)
    if r1c2.button("⏭️ Pular", use_container_width=True): toggle_skip()
    if r1c3.button("🍽️ Almoço", use_container_width=True): update_status("Almoço", True)
    if r1c4.button("🖨️ Certidão", use_container_width=True): st.session_state.active_view = "certidao"

    if st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.subheader("🖨️ Registro de Certidão")
            tipo = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"])
            c_data = st.date_input("Data do Evento:", value=get_brazil_time().date())
            c_proc = st.text_input("Nº Processo:")
            c_cham = st.text_input("Nº Chamado:")
            c_mot = st.text_area("Motivo/Descrição:")
            
            act1, act2 = st.columns(2)
            with act1:
                if st.button("📄 Gerar Word (Sem Salvar)", use_container_width=True):
                    if not c_proc and tipo != 'Geral': st.error("Informe o processo.")
                    else:
                        doc = gerar_docx_certidao_internal(tipo, c_proc, c_data.strftime("%d/%m/%Y"), st.session_state.consultor_selectbox, c_mot, c_cham)
                        if doc: st.download_button("⬇️ Baixar DOCX", doc, f"certidao_{c_proc}.docx")
            
            with act2:
                if st.button("💾 Salvar no Banco", type="primary", use_container_width=True):
                    if st.session_state.consultor_selectbox == "Selecione um nome":
                        st.error("Selecione seu nome antes.")
                    elif verificar_duplicidade_certidao(tipo, c_proc, c_data):
                        st.warning("⚠️ Certidão já existe para este processo!")
                        with st.popover("🚨 AVISO"):
                            st.error("Não registre novamente. Fale com Matheus ou Gilberto.")
                    else:
                        proc_final = c_proc.strip().rstrip('.') if c_proc else ""
                        payload = {"tipo": tipo, "data_evento": c_data.isoformat(), "consultor": st.session_state.consultor_selectbox, "n_processo": proc_final, "n_chamado": c_cham, "motivo": c_mot}
                        if salvar_certidao_db(payload):
                            st.success("✅ Registrado!"); time.sleep(1); st.session_state.active_view = None; st.rerun()
                        else:
                            st.error("Erro ao salvar. Fale com Matheus ou Gilberto.")

with col_status:
    st.header("Fila e Status")
    for n in CONSULTORES:
        status = st.session_state.status_texto.get(n, "Indisponível")
        if n in st.session_state.bastao_queue or "Bastão" in status:
            bg = "#FFD700" if "Bastão" in status else "#E0E0E0"
            st.markdown(f"<div style='background:{bg}; padding:8px; border-radius:10px; margin-bottom:5px; color:black;'><strong>{n}</strong>: {status}</div>", unsafe_allow_html=True)

    if st.button("❌ Fechar View Ativa"):
        st.session_state.active_view = None
        st.rerun()
