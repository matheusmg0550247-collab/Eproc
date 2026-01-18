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

# --- CONEXÃO COM SUPABASE ---
def get_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None

# --- FUNÇÕES DE BANCO PARA CERTIDÕES ---
def verificar_duplicidade_certidao(tipo, n_processo=None, data_evento=None, hora_periodo=None):
    sb = get_supabase()
    if not sb: return False
    try:
        query = sb.table("certidoes_registro").select("*").eq("tipo", tipo)
        
        if tipo in ['Física', 'Eletrônica'] and n_processo:
            # Limpa o processo para garantir a busca (sem pontos finais)
            proc_limpo = str(n_processo).strip().rstrip('.')
            if not proc_limpo: return False
            response = query.ilike("n_processo", f"%{proc_limpo}%").execute()
            return len(response.data) > 0
            
        elif tipo == 'Geral' and data_evento:
            data_str = data_evento.isoformat() if hasattr(data_evento, 'isoformat') else str(data_evento)
            query = query.eq("data_evento", data_str)
            if hora_periodo:
                query = query.eq("hora_periodo", hora_periodo)
            response = query.execute()
            return len(response.data) > 0
            
    except Exception as e:
        print(f"Erro duplicidade: {e}")
        return False
    return False

def salvar_certidao_db(dados):
    sb = get_supabase()
    if not sb: return False
    try:
        sb.table("certidoes_registro").insert(dados).execute()
        return True
    except Exception as e:
        raise e

# --- GERADOR DE WORD OFICIAL (CONFORME MODELO) ---
def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, hora=""):
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
        
        # Título
        p_num = doc.add_paragraph("Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2025.")
        p_num.runs[0].bold = True
        doc.add_paragraph("Assunto: Notifica erro no \"JPe - 2ª Instância\" ao peticionar.")
        
        data_extenso = datetime.now().strftime("%d de %B de %Y")
        doc.add_paragraph(f"\nExmo(a). Senhor(a) Relator(a),\n\nBelo Horizonte, {data_extenso}")
        
        # Corpo do Texto
        corpo = doc.add_paragraph()
        corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if tipo == 'Geral':
            corpo.add_run(f"Para fins de cumprimento dos artigos 13 e 14 da Resolução nº 780/2014 do Tribunal de Justiça do Estado de Minas Gerais, informamos que em {data} houve indisponibilidade do portal JPe, superior a uma hora, {hora}, que impossibilitou o peticionamento eletrônico de recursos em processos que já tramitavam no sistema.\n\n")
        else:
            corpo.add_run(f"Informamos que no dia {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}.\n\n")
            corpo.add_run(f"O Chamado de número informado no registro foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
            
            if tipo == 'Física':
                corpo.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.\n\n")
            else:
                corpo.add_run("Informamos a indisponibilidade para fins de restituição de prazo ou providências que V.Exa julgar necessárias, nos termos da legislação vigente.\n\n")
            
        corpo.add_run("Colocamo-nos à disposição para outras informações que se fizerem necessárias.")
        doc.add_paragraph("\nRespeitosamente,")
        
        # Assinatura Fixa
        doc.add_paragraph("\n\n___________________________________\nWaner Andrade Silva\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD\nDiretoria Executiva de Tecnologia da Informação e Comunicação - DIRTEC")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(f"Erro docx: {e}")
        return None

# ============================================
# 2. LÓGICA DO APP (FILA/STATUS)
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
            'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'), 'lunch_warning_info': st.session_state.get('lunch_warning_info'),
            'auxilio_ativo': st.session_state.get('auxilio_ativo', False), 'daily_logs': st.session_state.daily_logs,
            'simon_ranking': st.session_state.get('simon_ranking', [])
        }
        save_state_to_db(state_to_save)
    except Exception as e: print(f"Erro save: {e}")

def load_logs(): return st.session_state.daily_logs
def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    now_br = get_brazil_time()
    old_lbl = old_status if old_status else 'Fila Bastão'
    new_lbl = new_status if new_status else 'Fila Bastão'
    if consultor in st.session_state.bastao_queue:
        if 'Bastão' not in new_lbl and new_lbl != 'Fila Bastão': new_lbl = f"Fila | {new_lbl}"
    entry = {'timestamp': now_br, 'consultor': consultor, 'old_status': old_lbl, 'new_status': new_lbl, 'duration': duration, 'duration_s': duration.total_seconds()}
    st.session_state.daily_logs.append(entry)
    st.session_state.current_status_starts[consultor] = now_br

# --- LÓGICA DE FILA BLINDADA (AGRESSIVA) ---
def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue)
    start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        consultor = queue[idx]
        if consultor == queue[current_index] and n > 1: continue
        if not skips.get(consultor, False): return idx
    if n > 1:
        proximo_imediato_idx = (current_index + 1) % n
        nome_escolhido = queue[proximo_imediato_idx]
        st.session_state.skip_flags[nome_escolhido] = False 
        return proximo_imediato_idx
    return -1

def check_and_assume_baton(forced_successor=None, immune_consultant=None):
    queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    is_valid = (current_holder and current_holder in queue)
    target = forced_successor if forced_successor else (current_holder if is_valid else None)
    if not target:
        curr_idx = queue.index(current_holder) if (current_holder and current_holder in queue) else -1
        idx = find_next_holder_index(curr_idx, queue, skips)
        target = queue[idx] if idx != -1 else None
    changed = False; now = get_brazil_time()
    for c in CONSULTORES:
        if c != immune_consultant: 
            if c != target and 'Bastão' in st.session_state.status_texto.get(c, ''):
                log_status_change(c, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(c, now))
                st.session_state.status_texto[c] = 'Indisponível'; changed = True
    if target:
        curr_s = st.session_state.status_texto.get(target, '')
        if 'Bastão' not in curr_s:
            old_s = curr_s; new_s = f"Bastão | {old_s}" if old_s and old_s != "Indisponível" else "Bastão"
            log_status_change(target, old_s, new_s, now - st.session_state.current_status_starts.get(target, now))
            st.session_state.status_texto[target] = new_s; st.session_state.bastao_start_time = now
            if current_holder != target: 
                st.session_state.play_sound = True
            st.session_state.skip_flags[target] = False
            changed = True
            
    elif not target and current_holder:
        if current_holder != immune_consultant:
            log_status_change(current_holder, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(current_holder, now))
            st.session_state.status_texto[current_holder] = 'Indisponível'; changed = True

    if changed: save_state()
    return changed

def init_session_state():
    if 'db_loaded' not in st.session_state:
        try:
            db_data = load_state_from_db()
            if db_data:
                for key, value in db_data.items(): st.session_state[key] = value
        except: pass
        st.session_state['db_loaded'] = True
    if 'report_last_run_date' in st.session_state and isinstance(st.session_state['report_last_run_date'], str):
        try: st.session_state['report_last_run_date'] = datetime.fromisoformat(st.session_state['report_last_run_date'])
        except: st.session_state['report_last_run_date'] = datetime.min
    now = get_brazil_time()
    defaults = {
        'bastao_start_time': None, 'report_last_run_date': datetime.min, 'rotation_gif_start_time': None,
        'play_sound': False, 'gif_warning': False, 'lunch_warning_info': None, 'last_reg_status': None,
        'auxilio_ativo': False, 'active_view': None,
        'consultor_selectbox': "Selecione um nome",
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [], 'skip_flags': {}, 'current_status_starts': {nome: now for nome in CONSULTORES},
        'bastao_counts': {nome: 0 for nome in CONSULTORES}, 'priority_return_queue': [], 'daily_logs': []
    }
    for key, default in defaults.items():
        if key not in st.session_state: st.session_state[key] = default

def ensure_daily_reset():
    now_br = get_brazil_time(); last_run = st.session_state.report_last_run_date
    if now_br.date() > last_run.date():
        st.session_state.bastao_queue = []; st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
        st.session_state.report_last_run_date = now_br
        save_state()

def toggle_queue(consultor):
    if consultor == 'Selecione um nome': return
    ensure_daily_reset()
    if consultor in st.session_state.bastao_queue:
        st.session_state.bastao_queue.remove(consultor)
        st.session_state.status_texto[consultor] = 'Indisponível'
    else:
        st.session_state.bastao_queue.append(consultor)
        st.session_state.status_texto[consultor] = ''
    check_and_assume_baton()
    st.rerun()

def manual_rerun(): st.rerun()
def toggle_view(v): st.session_state.active_view = v if st.session_state.active_view != v else None

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
st_autorefresh(interval=10000, key='auto_rerun')

st.title(f"Controle Bastão Cesupe 2026 {BASTAO_EMOJI}")

col_principal, col_disponibilidade = st.columns([1.5, 1])

with col_principal:
    st.selectbox('Selecione seu nome:', ['Selecione um nome'] + CONSULTORES, key='consultor_selectbox')
    
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    if r1c1.button('🎯 Passar Bastão', use_container_width=True):
        holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        if st.session_state.consultor_selectbox == holder:
            idx = st.session_state.bastao_queue.index(holder)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: check_and_assume_baton(forced_successor=st.session_state.bastao_queue[nxt])
            st.rerun()
        else: st.warning("Apenas quem está com o bastão pode passar.")

    if r1c2.button('🥂 Entrar/Sair Fila', use_container_width=True): toggle_queue(st.session_state.consultor_selectbox)
    if r1c3.button('🍽️ Almoço', use_container_width=True): 
        if st.session_state.consultor_selectbox != 'Selecione um nome':
            if st.session_state.consultor_selectbox in st.session_state.bastao_queue:
                st.session_state.bastao_queue.remove(st.session_state.consultor_selectbox)
            st.session_state.status_texto[st.session_state.consultor_selectbox] = 'Almoço'
            check_and_assume_baton()
            st.rerun()
    if r1c4.button('🖨️ Certidão', use_container_width=True): toggle_view('certidao')

    # VIEW: CERTIDÃO
    if st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.header("🖨️ Registro de Certidão")
            tipo_certidao = st.selectbox("Tipo de Declaração:", ["Física", "Eletrônica", "Geral"])
            c_data = st.date_input("Data do Evento:", value=get_brazil_time().date())
            c_consultor = st.session_state.consultor_selectbox
            c_chamado = ""; c_processo = ""; c_motivo = ""; c_hora = ""
            
            if tipo_certidao == "Geral":
                c_hora = st.text_input("Horário/Período (ex: 14:00 às 18:00):")
                c_motivo = st.text_input("Motivo (ex: Queda de energia no TJ):")
            else:
                col_c1, col_c2 = st.columns(2)
                c_chamado = col_c1.text_input("Nº Chamado:")
                c_processo = col_c2.text_input("Nº Processo (Obrigatório):")
                c_motivo = st.text_area("Motivo / Erro apresentado:")

            col_act1, col_act2 = st.columns([1, 1])
            with col_act1:
                if st.button("📄 Gerar Word (Sem Salvar)", use_container_width=True):
                    if c_consultor == "Selecione um nome": st.error("Selecione seu nome.")
                    elif not c_processo and tipo_certidao != 'Geral': st.error("Processo obrigatório.")
                    else:
                        docx = gerar_docx_certidao_internal(tipo_certidao, c_processo, c_data.strftime("%d/%m/%Y"), c_consultor, c_motivo, c_chamado if c_chamado else c_hora)
                        if docx: st.download_button("⬇️ Baixar DOCX", docx, file_name=f"certidao_{c_processo}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
            with col_act2:
                if st.button("💾 Salvar Registro", type="primary", use_container_width=True):
                    if c_consultor == "Selecione um nome": st.error("Selecione seu nome.")
                    else:
                        try:
                            if verificar_duplicidade_certidao(tipo_certidao, n_processo=c_processo, data_evento=c_data, hora_periodo=c_hora):
                                st.warning("⚠️ **Atenção: Já existe registro!**")
                                with st.popover("🚨 LER AVISO"):
                                    st.error(f"Já existe uma certidão registrada. Por favor, procure Matheus ou Gilberto.")
                            else:
                                p_final = c_processo.strip().rstrip('.') if c_processo else ""
                                payload = {"tipo": tipo_certidao, "data_evento": c_data.isoformat(), "consultor": c_consultor, "n_chamado": c_chamado, "n_processo": p_final, "motivo": c_motivo, "hora_periodo": c_hora}
                                if salvar_certidao_db(payload):
                                    st.success("✅ Registrado!"); time.sleep(2); st.session_state.active_view = None; st.rerun()
                        except: st.error("Erro técnico. Fale com Matheus ou Gilberto.")

with col_disponibilidade:
    st.header('Status')
    responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if responsavel:
        st.success(f"👑 **Bastão:** {responsavel}")
    
    for nome in CONSULTORES:
        status = st.session_state.status_texto.get(nome, 'Indisponível')
        if nome in st.session_state.bastao_queue or "Bastão" in status:
            bg = "#FFD700" if "Bastão" in status else "#F0F2F6"
            st.markdown(f"<div style='background:{bg}; padding:8px; border-radius:10px; margin-bottom:5px; color:black;'><strong>{nome}</strong>: {status}</div>", unsafe_allow_html=True)
