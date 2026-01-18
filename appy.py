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

# --- GERADOR DE WORD OFICIAL ---
def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado="", hora=""):
    try:
        doc = Document()
        section = doc.sections[0]
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(3.0)

        style = doc.styles['Normal']
        style.font.name = 'Arial'
        style.font.size = Pt(11)

        head_p = doc.add_paragraph()
        head_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        runner = head_p.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        runner.bold = True
        head_p.add_run("Rua Ouro Preto, N° 1564 - Bairro Santo Agostinho - CEP 30170-041 - Belo Horizonte - MG\nwww.tjmg.jus.br - Andar: 3º e 4º PV")
        
        doc.add_paragraph("\n")
        p_num = doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2025.")
        p_num.runs[0].bold = True
        doc.add_paragraph("Assunto: Notifica erro no \"JPe - 2ª Instância\" ao peticionar.")
        
        data_atual = datetime.now().strftime("%d de %B de %Y")
        doc.add_paragraph(f"\nExmo(a). Senhor(a) Relator(a),\n\nBelo Horizonte, {data_atual}")
        
        corpo = doc.add_paragraph()
        corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if tipo == 'Geral':
            txt = (f"Para fins de cumprimento dos artigos 13 e 14 da Resolução nº 780/2014 do Tribunal de Justiça do Estado de Minas Gerais, "
                   f"informamos que em {data} houve indisponibilidade do portal JPe, superior a uma hora, {hora}, que impossibilitou o peticionamento eletrônico de recursos em processos que já tramitavam no sistema.")
            corpo.add_run(txt)
        else:
            corpo.add_run(f"Informamos que no dia {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}.\n\n")
            corpo.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
            if tipo == 'Física':
                corpo.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.\n\n")
            else:
                corpo.add_run("Informamos a indisponibilidade para fins de restituição de prazo ou providências que V.Exa julgar necessárias, nos termos da legislação vigente.\n\n")
        
        corpo.add_run("\nColocamo-nos à disposição para outras informações que se fizerem necessárias.")
        doc.add_paragraph("\nRespeitosamente,")
        doc.add_paragraph("\n\n___________________________________\nWaner Andrade Silva\n0-009020-9\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD\nDiretoria Executiva de Tecnologia da Informação e Comunicação - DIRTEC")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
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

def _send_webhook_sync(url, payload):
    try: requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=3)
    except: pass

def send_log_to_sheets(timestamp_str, consultor, old_status, new_status, duration_str):
    if not SHEETS_WEBHOOK_URL: return
    payload = {"data_hora": timestamp_str, "consultor": consultor, "status_anterior": old_status, "status_atual": new_status, "tempo_anterior": duration_str}
    _send_webhook_sync(SHEETS_WEBHOOK_URL, payload)

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    now_br = get_brazil_time()
    old_lbl = old_status if old_status else 'Fila Bastão'
    new_lbl = new_status if new_status else 'Fila Bastão'
    if consultor in st.session_state.bastao_queue:
        if 'Bastão' not in new_lbl and new_lbl != 'Fila Bastão': new_lbl = f"Fila | {new_lbl}"
    entry = {'timestamp': now_br, 'consultor': consultor, 'old_status': old_lbl, 'new_status': new_lbl, 'duration': duration, 'duration_s': duration.total_seconds()}
    st.session_state.daily_logs.append(entry)
    timestamp_str = now_br.strftime("%d/%m/%Y %H:%M:%S")
    duration_str = format_time_duration(duration)
    send_log_to_sheets(timestamp_str, consultor, old_lbl, new_lbl, duration_str)
    st.session_state.current_status_starts[consultor] = now_br

# --- HANDLERS ---
def on_auxilio_change(): save_state()

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        msg = f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {APP_URL_CLOUD}"
        send_to_chat("bastao", msg); return True
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    msg = f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n🕐 **Início:** {inicio.strftime('%H:%M')}\n⏱️ **Tempo Total:** {tempo}\n📝 **Motivo:** {motivo}"
    send_to_chat("extras", msg); return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    jira_str = f"\n🔢 **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n👥 **Usuário:** {usuario}\n🏢 **Nome/Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {descricao}\n📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{jira_str}"
    send_to_chat("registro", msg); return True

def handle_erro_novidade_submission(consultor, titulo, objetivo, relato, resultado):
    data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
    msg = f"🐛 **Novo Relato de Erro e Novidade**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n📌 **Título:** {titulo}\n\n🎯 **Objetivo:**\n{objetivo}\n\n🧪 **Relato:**\n{relato}\n\n🏁 **Resultado:**\n{resultado}"
    send_to_chat("erro", msg); return True

def send_sessao_to_chat_fn(consultor, texto_mensagem):
    if not consultor or consultor == 'Selecione um nome': return False
    send_to_chat("sessao", texto_mensagem); return True

def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'
def render_fireworks(): st.markdown("""<style>...</style>""", unsafe_allow_html=True)

def auto_manage_time():
    now = get_brazil_time(); last_run = st.session_state.report_last_run_date
    if now.hour >= 23 and now.date() == last_run.date(): reset_day_state(); save_state()
    elif now.date() > last_run.date(): reset_day_state(); save_state()
    elif now.hour >= 20:
        if any(s != 'Indisponível' for s in st.session_state.status_texto.values()) or st.session_state.bastao_queue:
            st.session_state.bastao_queue = []; st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
            for n in CONSULTORES: st.session_state[f'check_{n}'] = False
            save_state()

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
                st.session_state.play_sound = True; send_chat_notification_internal(target, 'Bastão')
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
        'chamado_guide_step': 0, 'sessao_msg_preview': "", 'html_download_ready': False, 'html_content_cache': "",
        'auxilio_ativo': False, 'active_view': None, 'last_jira_number': "",
        'simon_sequence': [], 'simon_user_input': [], 'simon_status': 'start', 'simon_level': 1,
        'consultor_selectbox': "Selecione um nome",
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [], 'skip_flags': {}, 'current_status_starts': {nome: now for nome in CONSULTORES},
        'bastao_counts': {nome: 0 for nome in CONSULTORES}, 'priority_return_queue': [], 'daily_logs': [], 'simon_ranking': [],
        'word_buffer': None, 'aviso_duplicidade': False
    }
    for key, default in defaults.items():
        if key not in st.session_state: st.session_state[key] = default
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0); st.session_state.skip_flags.setdefault(nome, False)
        current_status = st.session_state.status_texto.get(nome, 'Indisponível')
        if current_status is None: current_status = 'Indisponível'
        st.session_state.status_texto[nome] = current_status
        blocking = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento']
        is_hard_blocked = any(kw in current_status for kw in blocking)
        if is_hard_blocked: is_available = False
        elif nome in st.session_state.priority_return_queue: is_available = False
        elif nome in st.session_state.bastao_queue: is_available = True
        else: is_available = 'Indisponível' not in current_status
        st.session_state[f'check_{nome}'] = is_available
        if nome not in st.session_state.current_status_starts: st.session_state.current_status_starts[nome] = now
    check_and_assume_baton()

def reset_day_state():
    now = get_brazil_time()
    st.session_state.bastao_queue = []; st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
    st.session_state.bastao_counts = {n: 0 for n in CONSULTORES}; st.session_state.skip_flags = {}
    st.session_state.daily_logs = []; st.session_state.current_status_starts = {n: now for n in CONSULTORES}
    st.session_state.report_last_run_date = now
    for n in CONSULTORES: st.session_state[f'check_{n}'] = False

def ensure_daily_reset():
    now_br = get_brazil_time(); last_run = st.session_state.report_last_run_date
    if now_br.date() > last_run.date(): reset_day_state(); st.toast("☀️ Novo dia detectado! Fila limpa.", icon="🧹"); save_state()

def toggle_queue(consultor):
    now_hour = get_brazil_time().hour
    if now_hour >= 20 or now_hour < 6:
        st.toast("💤 Fora do expediente!", icon="🌙"); return False
    ensure_daily_reset(); st.session_state.gif_warning = False; now_br = get_brazil_time()
    if consultor in st.session_state.bastao_queue:
        current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        forced_successor = None
        if consultor == current_holder:
            idx = st.session_state.bastao_queue.index(consultor)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: forced_successor = st.session_state.bastao_queue[nxt]
        st.session_state.bastao_queue.remove(consultor)
        st.session_state[f'check_{consultor}'] = False
        current_s = st.session_state.status_texto.get(consultor, '')
        if current_s == '' or current_s == 'Bastão':
            log_status_change(consultor, current_s, 'Indisponível', now_br - st.session_state.current_status_starts.get(consultor, now_br))
            st.session_state.status_texto[consultor] = 'Indisponível'
        check_and_assume_baton(forced_successor)
    else:
        st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True
        st.session_state.skip_flags[consultor] = False
        if consultor in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(consultor)
        current_s = st.session_state.status_texto.get(consultor, 'Indisponível')
        if 'Indisponível' in current_s:
            log_status_change(consultor, current_s, '', now_br - st.session_state.current_status_starts.get(consultor, now_br))
            st.session_state.status_texto[consultor] = ''
        check_and_assume_baton()
    save_state(); return True

def leave_specific_status(consultor, status_type_to_remove):
    ensure_daily_reset(); st.session_state.gif_warning = False
    if status_type_to_remove in ['Almoço', 'Treinamento', 'Sessão', 'Reunião']:
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True; st.session_state.skip_flags[consultor] = False
    old_status = st.session_state.status_texto.get(consultor, '')
    now_br = get_brazil_time(); duration = now_br - st.session_state.current_status_starts.get(consultor, now_br)
    parts = [p.strip() for p in old_status.split('|')]
    new_parts = [p for p in parts if status_type_to_remove not in p and p]
    new_status = " | ".join(new_parts)
    if not new_status and consultor in st.session_state.bastao_queue: new_status = '' 
    elif not new_status: new_status = 'Indisponível'
    log_status_change(consultor, old_status, new_status, duration)
    st.session_state.status_texto[consultor] = new_status
    check_and_assume_baton(); save_state()

def enter_from_indisponivel(consultor):
    now_hour = get_brazil_time().hour
    if now_hour >= 20 or now_hour < 6: st.toast("💤 Fora do expediente!", icon="🌙"); time.sleep(1); st.rerun(); return
    ensure_daily_reset(); st.session_state.gif_warning = False
    if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    st.session_state[f'check_{consultor}'] = True
    st.session_state.skip_flags[consultor] = False
    old_status = st.session_state.status_texto.get(consultor, 'Indisponível')
    duration = get_brazil_time() - st.session_state.current_status_starts.get(consultor, get_brazil_time())
    log_status_change(consultor, old_status, '', duration)
    st.session_state.status_texto[consultor] = ''
    check_and_assume_baton(); save_state()

def rotate_bastao():
    ensure_daily_reset(); selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if selected != current_holder: st.session_state.gif_warning = True; return
    current_index = queue.index(current_holder) if current_holder in queue else -1
    if current_index == -1: check_and_assume_baton(); return
    next_idx = find_next_holder_index(current_index, queue, skips)
    if next_idx == -1 and len(queue) > 1: next_idx = (current_index + 1) % len(queue)
    if next_idx != -1:
        next_holder = queue[next_idx]
        st.session_state.skip_flags[next_holder] = False
        now_br = get_brazil_time()
        old_h_status = st.session_state.status_texto[current_holder]
        new_h_status = old_h_status.replace('Bastão | ', '').replace('Bastão', '').strip()
        log_status_change(current_holder, old_h_status, new_h_status, now_br - (st.session_state.bastao_start_time or now_br))
        st.session_state.status_texto[current_holder] = new_h_status
        old_n_status = st.session_state.status_texto.get(next_holder, '')
        new_n_status = f"Bastão | {old_n_status}" if old_n_status else "Bastão"
        log_status_change(next_holder, old_n_status, new_n_status, timedelta(0))
        st.session_state.status_texto[next_holder] = new_n_status
        st.session_state.bastao_start_time = now_br
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True; st.session_state.rotation_gif_start_time = now_br
        send_chat_notification_internal(next_holder, 'Bastão'); save_state()
    else: st.warning('Ninguém elegível.'); check_and_assume_baton()

def toggle_skip():
    [437] def rotate_bastao():
 queue = st.session_state.bastao_queue
holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
     if not holder: 
     return   
     idx = queue.index(holder) if holder in queue else -1
     nxt = find_next_holder_index(idx, queue, st.session_state.skip_flags)
     if nxt != -1: 
    check_and_assume_baton(forced_successor=queue[nxt])
    st.rerun()
    if not holder: return
    idx = queue.index(holder) if holder in queue else -1
    nxt = find_next_holder_index(idx, queue, st.session_state.skip_flags)
    if nxt != -1: check_and_assume_baton(forced_successor=queue[nxt])
    st.rerun()
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    if not st.session_state.get(f'check_{selected}'): st.warning(f'{selected} não está disponível.'); return
    novo = not st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = novo
    if novo:
        now_br = get_brazil_time()
        st.session_state.current_status_starts[selected] = now_br
        log_status_change(selected, "Fila", "Fila (Final)", timedelta(0))
        if selected in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(selected); st.session_state.bastao_queue.append(selected)
        st.toast(f"⏭️ {selected} pulou e foi para o fim da fila!", icon="⏭️")
    else: st.toast(f"✅ {selected} voltou para a fila!", icon="✅")
    save_state(); st.rerun()

def update_status(new_status_part, force_exit_queue=False):
    ensure_daily_reset(); selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    current = st.session_state.status_texto.get(selected, '')
    blocking = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento']
    should_exit = force_exit_queue or any(b in new_status_part for b in blocking)
    is_holder = 'Bastão' in current
    forced_succ = None
    if should_exit and selected in st.session_state.bastao_queue:
        holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        if selected == holder:
            idx = st.session_state.bastao_queue.index(selected)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt == -1 and len(st.session_state.bastao_queue) > 1:
                nxt = (idx + 1) % len(st.session_state.bastao_queue)
                st.session_state.skip_flags[st.session_state.bastao_queue[nxt]] = False
            if nxt != -1: forced_succ = st.session_state.bastao_queue[nxt]
        st.session_state[f'check_{selected}'] = False; st.session_state.bastao_queue.remove(selected)
    if new_status_part in ['Almoço', 'Ausente', 'Saída rápida']: final_status = new_status_part
    else:
        parts = [p.strip() for p in current.split('|') if p.strip()]
        type_new = new_status_part.split(':')[0]
        clean = [p for p in parts if p != 'Indisponível' and not p.startswith(type_new) and p not in blocking]
        clean.append(new_status_part)
        clean.sort(key=lambda x: 0 if 'Bastão' in x else 1 if 'Atividade' in x or 'Projeto' in x else 2)
        final_status = " | ".join(clean)
        if is_holder and not should_exit and 'Bastão' not in final_status: final_status = f"Bastão | {final_status}"
        if should_exit: final_status = final_status.replace("Bastão | ", "").replace("Bastão", "").strip()
    now_br = get_brazil_time()
    log_status_change(selected, current, final_status, now_br - st.session_state.current_status_starts.get(selected, now_br))
    st.session_state.status_texto[selected] = final_status
    if is_holder: check_and_assume_baton(forced_succ, immune_consultant=selected)
    save_state()

def manual_rerun(): st.session_state.gif_warning = False; st.rerun()
def toggle_view(v): st.session_state.active_view = v if st.session_state.active_view != v else None

# --- SIMON GAME ---
def handle_simon_input(color):
    st.session_state.simon_user_input.append(color)
    idx = len(st.session_state.simon_user_input) - 1
    if st.session_state.simon_user_input[idx] != st.session_state.simon_sequence[idx]:
        st.session_state.simon_status = 'game_over'
    elif len(st.session_state.simon_user_input) == len(st.session_state.simon_sequence):
        st.session_state.simon_status = 'level_up'

def simon_game_ui():
    st.subheader("🧠 Simon Game - Descanso")
    colors = {"🔴": "Red", "🟢": "Green", "🔵": "Blue", "🟡": "Yellow"}
    if st.session_state.simon_status == 'start':
        if st.button("Iniciar Jogo"):
            import random
            st.session_state.simon_sequence = [random.choice(list(colors.values())) for _ in range(3)]
            st.session_state.simon_level = 1; st.session_state.simon_status = 'showing'; st.rerun()
    elif st.session_state.simon_status == 'showing':
        st.write(f"Nível: {st.session_state.simon_level}")
        st.write("Memorize a sequência...")
        time.sleep(1)
        st.session_state.simon_status = 'waiting'; st.rerun()
    elif st.session_state.simon_status == 'waiting':
        cols = st.columns(4)
        for i, (emoji, name) in enumerate(colors.items()):
            if cols[i].button(emoji, key=f"simon_{name}"): handle_simon_input(name); st.rerun()
    elif st.session_state.simon_status == 'level_up':
        import random
        st.session_state.simon_level += 1
        st.session_state.simon_sequence.append(random.choice(list(colors.values())))
        st.session_state.simon_user_input = []; st.session_state.simon_status = 'showing'; st.success("Muito bem!"); st.rerun()
    elif st.session_state.simon_status == 'game_over':
        st.error(f"Fim de jogo! Pontuação: {st.session_state.simon_level}")
        if st.button("Tentar Novamente"): st.session_state.simon_status = 'start'; st.rerun()
    if st.button("❌ Sair"): st.session_state.active_view = None; st.rerun()

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================
    def rotate_bastao():
    queue = st.session_state.bastao_queue
    holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if not holder: 
        return
    idx = queue.index(holder) if holder in queue else -1
    nxt = find_next_holder_index(idx, queue, st.session_state.skip_flags)
    if nxt != -1: 
        check_and_assume_baton(forced_successor=queue[nxt])
    st.rerun()

def toggle_skip():
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome':
        st.warning('Selecione um(a) consultor(a).')
        return
    if not st.session_state.get(f'check_{selected}'):
        st.warning(f'{selected} não está disponível.')
        return
    novo = not st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = novo
    if novo and selected in st.session_state.bastao_queue:
        st.session_state.bastao_queue.remove(selected)
        st.session_state.bastao_queue.append(selected)
    save_state()
    st.rerun()
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state(); auto_manage_time()
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
render_fireworks()

c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img = get_img_as_base64(PUG2026_FILENAME); src = f"data:image/png;base64,{img}" if img else GIF_BASTAO_HOLDER
    st.markdown(f"""<div style="display: flex; align-items: center; gap: 15px;"><h1 style="margin: 0; padding: 0; font-size: 2.2rem; color: #FFD700; text-shadow: 1px 1px 2px #B8860B;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{src}" style="width: 120px; height: 120px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;"></div>""", unsafe_allow_html=True)

with c_topo_dir:
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_sub1: novo_responsavel = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
    with c_sub2:
        if st.button("🚀 Entrar", use_container_width=True):
            if novo_responsavel != "Selecione": toggle_queue(novo_responsavel); st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)
st_autorefresh(interval=8000, key='auto_rerun')

col_principal, col_disponibilidade = st.columns([1.5, 1])
queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
curr_idx = queue.index(responsavel) if responsavel in queue else -1
prox_idx = find_next_holder_index(curr_idx, queue, skips)
proximo = queue[prox_idx] if prox_idx != -1 else None

with col_principal:
    st.header("Responsável pelo Bastão")
    if responsavel:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%); border: 3px solid #FFD700; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3); margin-bottom: 20px;"><div style="flex-shrink: 0; margin-right: 25px;"><img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #FFD700;"></div><div><span style="font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px;">Atualmente com:</span><br><span style="font-size: 42px; font-weight: 800; color: #000080; line-height: 1.1;">{responsavel}</span></div></div>""", unsafe_allow_html=True)
        dur = get_brazil_time() - (st.session_state.bastao_start_time or get_brazil_time())
        st.caption(f"⏱️ Tempo com o bastão: **{format_time_duration(dur)}**")
    else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
    
    st.markdown("###"); st.header("Próximos da Fila")
    if proximo: st.markdown(f'### 1º: **{proximo}**')
    
    st.markdown("###"); st.header("**Consultor(a)**")
    st.selectbox('Selecione:', ['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    r1c1, r1c2, r1c3, r1c4 = st.columns(4); r2c1, r2c2, r2c3, r2c4, r2c5, r2c6 = st.columns(6)
    r1c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    r1c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True)
    r1c3.button('📋 Atividades', on_click=toggle_view, args=('menu_atividades',), use_container_width=True)
    r1c4.button('🏗️ Projeto', on_click=toggle_view, args=('menu_projetos',), use_container_width=True)
    r2c1.button('🎓 Treinamento', on_click=toggle_view, args=('menu_treinamento',), use_container_width=True)
    r2c2.button('📅 Reunião', on_click=toggle_view, args=('menu_reuniao',), use_container_width=True)
    r2c3.button('🍽️ Almoço', on_click=update_status, args=('Almoço', True), use_container_width=True)
    r2c4.button('🎙️ Sessão', on_click=toggle_view, args=('menu_sessao',), use_container_width=True)
    r2c5.button('🚶 Saída', on_click=update_status, args=('Saída rápida', True), use_container_width=True)
    r2c6.button('👤 Ausente', on_click=update_status, args=('Ausente', True), use_container_width=True)

    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            at_t = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS); at_e = st.text_input("Detalhe:")
            if st.button("Confirmar Atividade"): update_status(f"Atividade: {', '.join(at_t)} - {at_e}"); st.session_state.active_view = None; st.rerun()
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()

    st.markdown("####"); st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True); st.markdown("---")
    c_tool1, c_tool2, c_tool3, c_tool4, c_tool5, c_tool6, c_tool7 = st.columns(7)
    c_tool1.button("📑 Checklist", on_click=toggle_view, args=("checklist",), use_container_width=True)
    c_tool2.button("🆘 Chamados", on_click=toggle_view, args=("chamados",), use_container_width=True)
    c_tool3.button("📝 Atend.", on_click=toggle_view, args=("atendimentos",), use_container_width=True)
    c_tool4.button("⏰ H. Extras", on_click=toggle_view, args=("hextras",), use_container_width=True)
    c_tool5.button("🧠 Descanso", on_click=toggle_view, args=("descanso",), use_container_width=True)
    c_tool6.button("🐛 Erro", on_click=toggle_view, args=("erro_novidade",), use_container_width=True)
    c_tool7.button("🖨️ Certidão", on_click=toggle_view, args=("certidao",), use_container_width=True)

    if st.session_state.active_view == "checklist":
        with st.container(border=True):
            st.header("Gerador de Checklist"); data_eproc = st.date_input("Data:", value=get_brazil_time().date()); camara_eproc = st.selectbox("Câmara:", CAMARAS_OPCOES)
            if st.button("Gerar HTML"): st.write("Checklist registrado no chat!"); send_to_chat("sessao", f"Consultor {st.session_state.consultor_selectbox} acompanhando sessão {camara_eproc}")
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "descanso": simon_game_ui()

    if st.session_state.active_view == "hextras":
        with st.container(border=True):
            st.header("⏰ Horas Extras")
            d_ex = st.date_input("Data:"); h_in = st.time_input("Início:"); t_ex = st.text_input("Tempo Total:"); mot = st.text_input("Motivo:")
            if st.button("Registrar"): send_horas_extras_to_chat(st.session_state.consultor_selectbox, d_ex, h_in, t_ex, mot); st.success("Registrado!"); st.session_state.active_view = None; st.rerun()
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "erro_novidade":
        with st.container(border=True):
            st.header("🐛 Erro e Novidade")
            tit = st.text_input("Título:"); obj = st.text_area("Objetivo:"); rel = st.text_area("Relato:"); res = st.text_area("Resultado:")
            if st.button("Enviar"): handle_erro_novidade_submission(st.session_state.consultor_selectbox, tit, obj, rel, res); st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.header("🖨️ Registro de Certidão")
            tipo_cert = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"])
            c_data = st.date_input("Data do Evento:", value=get_brazil_time().date())
            c_cons = st.session_state.consultor_selectbox
            if tipo_cert == "Geral":
                c_hora = st.text_input("Horário/Período (ex: a partir das 14:00):"); c_motivo = st.text_input("Motivo:"); c_proc = ""
            else:
                c_hora = ""; col_c1, col_c2 = st.columns(2)
                c_chamado = col_c1.text_input("Nº Chamado:"); c_proc = col_c2.text_input("Nº Processo:"); c_motivo = st.text_area("Motivo / Erro:")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📄 Gerar Modelo Word", use_container_width=True):
                    st.session_state.word_buffer = gerar_docx_certidao_internal(tipo_cert, c_proc, c_data.strftime("%d/%m/%Y"), c_cons, c_motivo, c_chamado if tipo_cert != 'Geral' else '', c_hora)
                if st.session_state.word_buffer:
                    st.download_button("⬇️ Baixar DOCX", st.session_state.word_buffer, file_name=f"certidao.docx")
            with col_btn2:
                if st.button("💾 Salvar Registro", type="primary", use_container_width=True):
                    if verificar_duplicidade_certidao(tipo_cert, c_proc, c_data, c_hora): st.session_state.aviso_duplicidade = True
                    else:
                        payload = {"tipo": tipo_cert, "data_evento": c_data.isoformat(), "consultor": c_cons, "n_chamado": c_chamado if tipo_cert != 'Geral' else '', "n_processo": c_proc.strip().rstrip('.'), "motivo": c_motivo, "hora_periodo": c_hora}
                        if salvar_certidao_db(payload): st.success("✅ Salvo!"); time.sleep(2); st.session_state.active_view = None; st.session_state.word_buffer = None; st.rerun()
            if st.button("❌ Cancelar Registro", key="cancel_cert"): st.session_state.active_view = None; st.rerun()
            if st.session_state.get('aviso_duplicidade'):
                st.error("⚠️ ATENÇÃO: Registro já existe! Favor procurar Matheus ou Gilberto.")
                if st.button("Ciente"): st.session_state.aviso_duplicidade = False; st.rerun()

with col_disponibilidade:
    st.header('Status')
    ui_lists = {'fila': [], 'almoco': [], 'indisponivel': []}
    for nome in CONSULTORES:
        if nome in st.session_state.bastao_queue: ui_lists['fila'].append(nome)
        status = st.session_state.status_texto.get(nome, 'Indisponível')
        if status == 'Almoço': ui_lists['almoco'].append(nome)
        elif status == 'Indisponível' and nome not in st.session_state.bastao_queue: ui_lists['indisponivel'].append(nome)
    
    st.subheader(f'✅ Na Fila ({len(ui_lists["fila"])})')
    for nome in [c for c in queue if c in ui_lists["fila"]]:
        c1, c2 = st.columns([0.85, 0.15])
        c2.checkbox(' ', key=f'chk_f_{nome}', value=True, on_change=toggle_queue, args=(nome,), label_visibility='collapsed')
        lbl = f"🥂 {nome}" if nome == responsavel else nome
        if st.session_state.skip_flags.get(nome): lbl += " ⏭️"
        c1.markdown(f"**{lbl}** - {st.session_state.status_texto.get(nome)}")

    st.subheader(f'❌ Indisponível ({len(ui_lists["indisponivel"])})')
    for nome in ui_lists['indisponivel']:
        c1, c2 = st.columns([0.85, 0.15])
        c2.checkbox(' ', key=f'chk_i_{nome}', value=False, on_change=enter_from_indisponivel, args=(nome,), label_visibility='collapsed')
        c1.write(nome)
