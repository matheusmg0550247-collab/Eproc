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
from docx.shared import Pt, Cm
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

BASTAO_EMOJI = "🥂" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
PUG2026_FILENAME = "pug2026.png"

# --- CONEXÃO COM SUPABASE ---
def get_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None

# ============================================
# 2. LÓGICA DE CERTIDÕES (WORD & DUPLICIDADE)
# ============================================

def verificar_duplicidade_certidao(tipo, n_processo=None, data_evento=None, hora_periodo=None):
    sb = get_supabase()
    if not sb: return False
    try:
        # Busca por tipo
        query = sb.table("certidoes_registro").select("*").eq("tipo", tipo)
        
        if tipo in ['Física', 'Eletrônica'] and n_processo:
            # LIMPEZA: Remove pontos e espaços para comparar de forma inteligente
            proc_limpo = str(n_processo).strip().replace(".", "").replace("-", "").replace("/", "")
            # No banco os processos podem estar com ou sem ponto. Usamos ilike para capturar ambos.
            # O símbolo % é o coringa do SQL
            response = query.ilike("n_processo", f"%{n_processo.strip().rstrip('.')}%").execute()
            return len(response.data) > 0
            
        elif tipo == 'Geral' and data_evento:
            data_str = data_evento.isoformat() if hasattr(data_evento, 'isoformat') else str(data_evento)
            query = query.eq("data_evento", data_str)
            if hora_periodo:
                query = query.eq("hora_periodo", hora_periodo)
            response = query.execute()
            return len(response.data) > 0
    except:
        return False
    return False

def salvar_certidao_db(dados):
    sb = get_supabase()
    if not sb: return False
    try:
        sb.table("certidoes_registro").insert(dados).execute()
        return True
    except:
        return False

def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado=""):
    try:
        doc = Document()
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Arial'
        font.size = Pt(11)

        # Cabeçalho
        head = doc.add_paragraph()
        head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = head.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        run.bold = True
        head.add_run("Rua Ouro Preto, Nº 1564 - Bairro Santo Agostinho - CEP 30170-041\nBelo Horizonte - MG - www.tjmg.jus.br\nAndar: 3º e 4º PV")
        
        doc.add_paragraph("\n")
        
        # Título / Parecer
        p_num = doc.add_paragraph("Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2025.")
        p_num.runs[0].bold = True
        
        doc.add_paragraph(f"Assunto: Notifica erro no \"JPe - 2ª Instância\" ao peticionar.")
        
        data_extenso = datetime.now().strftime("%d de %B de %Y")
        doc.add_paragraph(f"\nExmo(a). Senhor(a) Relator(a),\n\nBelo Horizonte, {data_extenso}")
        
        # Corpo do Texto
        corpo = doc.add_paragraph()
        corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if tipo == 'Geral':
            corpo.add_run(f"Para fins de cumprimento dos artigos 13 e 14 da Resolução nº 780/2014 do TJMG, informamos que em {data} houve indisponibilidade do portal JPe, superior a uma hora, {motivo}.\n\n")
        else:
            corpo.add_run(f"Informamos que no dia {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}.\n\n")
            corpo.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC.\n\n")
            
            if tipo == 'Física':
                corpo.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.\n\n")
            else:
                corpo.add_run("Informamos a indisponibilidade para fins de restituição de prazo ou providências que V.Exa julgar necessárias, nos termos da legislação vigente.\n\n")
        
        corpo.add_run("Colocamo-nos à disposição para outras informações.")
        
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
# 3. LÓGICA DE FILA E STATUS (ROBUSTO)
# ============================================

def save_state():
    try:
        last_run = st.session_state.report_last_run_date
        state_to_save = {
            'status_texto': st.session_state.status_texto, 
            'bastao_queue': st.session_state.bastao_queue,
            'skip_flags': st.session_state.skip_flags, 
            'current_status_starts': st.session_state.current_status_starts,
            'bastao_counts': st.session_state.bastao_counts, 
            'priority_return_queue': st.session_state.priority_return_queue,
            'bastao_start_time': st.session_state.bastao_start_time, 
            'report_last_run_date': last_run.isoformat() if last_run else datetime.min.isoformat(),
            'daily_logs': st.session_state.daily_logs
        }
        save_state_to_db(state_to_save)
    except: pass

def log_status_change(consultor, old_status, new_status, duration):
    now_br = get_brazil_time()
    entry = {'timestamp': now_br, 'consultor': consultor, 'old_status': old_status, 'new_status': new_status, 'duration': duration}
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

def rotate_bastao():
    queue = st.session_state.bastao_queue
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if not current_holder: return
    
    curr_idx = queue.index(current_holder) if current_holder in queue else -1
    nxt_idx = find_next_holder_index(curr_idx, queue, st.session_state.skip_flags)
    
    if nxt_idx != -1:
        check_and_assume_baton(forced_successor=queue[nxt_idx])
    st.rerun()

# ============================================
# 4. INTERFACE E EXECUÇÃO
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

# Inicialização do Estado
if 'db_loaded' not in st.session_state:
    db_data = load_state_from_db()
    if db_data:
        for k, v in db_data.items(): st.session_state[k] = v
    st.session_state['db_loaded'] = True

defaults = {
    'status_texto': {n: 'Indisponível' for n in CONSULTORES}, 'bastao_queue': [], 'skip_flags': {},
    'current_status_starts': {n: datetime.now() for n in CONSULTORES}, 'daily_logs': [],
    'bastao_start_time': None, 'report_last_run_date': datetime.now(), 'active_view': None,
    'bastao_counts': {n: 0 for n in CONSULTORES}, 'priority_return_queue': []
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

st_autorefresh(interval=10000, key='auto_refresh')

st.title(f"Controle Bastão Cesupe 2026 {BASTAO_EMOJI}")

col_principal, col_status = st.columns([1.5, 1])

with col_principal:
    st.selectbox("Consultor(a):", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox")
    
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    if r1c1.button("🎯 Passar Bastão", use_container_width=True): rotate_bastao()
    if r1c2.button("🥂 Entrar/Sair Fila", use_container_width=True): toggle_queue(st.session_state.consultor_selectbox)
    if r1c3.button("⏭️ Pular Vez", use_container_width=True): toggle_skip()
    if r1c4.button("🖨️ Certidão", use_container_width=True): st.session_state.active_view = "certidao"

    if st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.subheader("🖨️ Registro de Certidão")
            tipo = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"])
            c_data = st.date_input("Data do Evento:", value=get_brazil_time().date())
            c_proc = st.text_input("Nº Processo (obrigatório para Física/Eletrônica):")
            c_cham = st.text_input("Nº Chamado:")
            c_mot = st.text_area("Descrição/Motivo:")
            
            c_act1, c_act2 = st.columns(2)
            with c_act1:
                if st.button("📄 Gerar Word (Sem Salvar)", use_container_width=True):
                    if not c_proc and tipo != 'Geral': st.error("O processo é obrigatório.")
                    else:
                        doc = gerar_docx_certidao_internal(tipo, c_proc, c_data.strftime("%d/%m/%Y"), st.session_state.consultor_selectbox, c_mot, c_cham)
                        if doc: st.download_button("⬇️ Baixar DOCX", doc, f"certidao_{c_proc}.docx")
            
            with c_act2:
                if st.button("💾 Salvar Registro", type="primary", use_container_width=True):
                    if st.session_state.consultor_selectbox == "Selecione um nome":
                        st.error("Selecione seu nome no topo.")
                    elif verificar_duplicidade_certidao(tipo, c_proc, c_data):
                        st.warning("⚠️ Atenção: Já existe registro!")
                        with st.popover("🚨 LER AVISO"):
                            st.error("Já existe uma certidão registrada. Por favor, procure Matheus ou Gilberto.")
                    else:
                        # Limpa processo (remove ponto final do registro novo)
                        proc_final = c_proc.strip().rstrip('.') if c_proc else ""
                        payload = {"tipo": tipo, "data_evento": c_data.isoformat(), "consultor": st.session_state.consultor_selectbox, "n_processo": proc_final, "n_chamado": c_cham, "motivo": c_mot}
                        if salvar_certidao_db(payload):
                            st.success("✅ Salvo!"); time.sleep(1); st.session_state.active_view = None; st.rerun()
                        else: st.error("Erro ao salvar no banco.")

    if st.button("🍽️ Almoço"): update_status("Almoço", True)

with col_status:
    st.header("Fila e Status")
    responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if responsavel:
        st.success(f"👑 **Bastão:** {responsavel}")
    
    for n in CONSULTORES:
        status = st.session_state.status_texto.get(n, "Indisponível")
        is_skipping = st.session_state.skip_flags.get(n, False)
        if n in st.session_state.bastao_queue or "Bastão" in status:
            color = "#FFD700" if "Bastão" in status else "#F0F2F6"
            label = f"{n} - {status}" + (" (⏭️ Pulando)" if is_skipping else "")
            st.markdown(f"<div style='background:{color}; padding:8px; border-radius:10px; margin-bottom:5px; color:black;'>{label}</div>", unsafe_allow_html=True)
