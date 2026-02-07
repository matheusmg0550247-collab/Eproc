# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import time
import gc
from datetime import datetime, timedelta, date
from operator import itemgetter
import json
import re
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

# =============================================================================
# 1. CONFIGURAÇÕES E CONSTANTES (BASEADO NO ARQUIVO EQUIPE1.TXT ORIGINAL)
# =============================================================================
DB_APP_ID = 2        # ID padrão (será sobrescrito pelos argumentos da função)
LOGMEIN_DB_ID = 1    # ID Compartilhado

# LISTA DE RAMAIS (SOLICITAÇÃO DO USUÁRIO)
RAMAIS_CESUPE = {
    "Alex": "2510", "Barbara": "2517", "Bruno Glaicon": "2644", "Claudio": "2667",
    "Dirceu Gonçalves": "2666", "Douglas De Souza": "2659", "Douglas Paiva": "2663",
    "Fábio Alves": "2665", "Farley Leandro": "2651", "Gilberto": "2654", "Gleis Da Silva": "2536",
    "Glayce Torres": "2647", "Hugo Leonardo": "2650", "Jerry Marcos": "2654", "Jonatas Gomes": "2656",
    "Leandro Victor": "2652", "Leonardo Damaceno": "2655", "Ivana Guimarães": "2653",
    "Marcelo PenaGuerra": "2655", "Marcelo Dos Santos": "2655", "Matheus": "2664", 
    "Michael Douglas": "2638", "Pablo Mol": "2643", "Ranyer Segal": "2669", 
    "Vanessa Ligiane": "2607", "Victoria Lisboa": "2660", "Isac Candido": "0000",
    "Sarah Leal": "0000", "Morôni": "0000", "Marina Silva": "0000", "Marina Torres": "0000",
    "Luiz Henrique": "0000", "Igor Dayrell": "0000"
}

# Listas de Opções
REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]
OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]

# URLs e Visuais
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
GIF_LOGMEIN_TARGET = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZjFvczlzd3ExMWc2cWJrZ3EwNmplM285OGFqOHE1MXlzdnd4cndibiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/mcsPU3SkKrYDdW3aAU/giphy.gif"
BASTAO_EMOJI = "🎭" 
PUG2026_FILENAME = "Carnaval.gif" 

# Secrets (Carregados via utils)
# As chaves são passadas na função render_dashboard

# ============================================
# 2. OTIMIZAÇÃO E CONEXÃO
# ============================================
@st.cache_resource(ttl=3600)
def get_supabase():
    try: 
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.cache_resource.clear()
        return None

@st.cache_data(ttl=3600, show_spinner=False)
def carregar_dados_grafico(app_id):
    sb = get_supabase()
    if not sb: return None, None
    try:
        res = sb.table("atendimentos_resumo").select("data").eq("id", app_id).execute()
        if res.data:
            json_data = res.data[0]['data']
            if 'totais_por_relatorio' in json_data:
                df = pd.DataFrame(json_data['totais_por_relatorio'])
                return df, json_data.get('gerado_em', '-')
    except Exception as e:
        pass
    return None, None

@st.cache_data
def get_img_as_base64_cached(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return None

# ============================================
# 3. REPOSITÓRIO (CRUD)
# ============================================
def clean_data_for_db(obj):
    if isinstance(obj, dict): return {k: clean_data_for_db(v) for k, v in obj.items()}
    elif isinstance(obj, list): return [clean_data_for_db(i) for i in obj]
    elif isinstance(obj, (datetime, date)): return obj.isoformat()
    elif isinstance(obj, timedelta): return obj.total_seconds()
    else: return obj

def load_state_from_db(target_id):
    sb = get_supabase()
    if not sb: return {}
    try:
        response = sb.table("app_state").select("data").eq("id", target_id).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("data", {})
        return {}
    except Exception as e:
        return {}

def save_state_to_db(app_id, state_data):
    sb = get_supabase()
    if not sb: return
    try:
        sanitized_data = clean_data_for_db(state_data)
        sb.table("app_state").upsert({"id": app_id, "data": sanitized_data}).execute()
    except Exception as e:
        st.error(f"🔥 ERRO DE ESCRITA NO BANCO: {e}")

# --- LOGMEIN DB ---
def get_logmein_status():
    sb = get_supabase()
    if not sb: return None, False
    try:
        res = sb.table("controle_logmein").select("*").eq("id", LOGMEIN_DB_ID).execute()
        if res.data:
            return res.data[0].get('consultor_atual'), res.data[0].get('em_uso', False)
    except: pass
    return None, False

def set_logmein_status(consultor, em_uso):
    sb = get_supabase()
    if not sb: return
    try:
        dados = {
            "consultor_atual": consultor if em_uso else None,
            "em_uso": em_uso,
            "data_inicio": datetime.now().isoformat()
        }
        sb.table("controle_logmein").update(dados).eq("id", LOGMEIN_DB_ID).execute()
    except Exception as e: st.error(f"Erro LogMeIn DB: {e}")

# ============================================
# 4. FUNÇÕES DE UTILIDADE E IP
# ============================================
def get_browser_id():
    if st_javascript is None: return "no_js_lib"
    js_code = """(function() {
        let id = localStorage.getItem("device_id");
        if (!id) {
            id = "id_" + Math.random().toString(36).substr(2, 9);
            localStorage.setItem("device_id", id);
        }
        return id;
    })();"""
    try: return st_javascript(js_code, key="browser_id_tag")
    except: return "unknown_device"

def get_remote_ip():
    try:
        from streamlit.web.server.websocket_headers import ClientWebSocketRequest
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and ctx.session_id:
            session_info = st.runtime.get_instance().get_client(ctx.session_id)
            if session_info:
                request = session_info.request
                if isinstance(request, ClientWebSocketRequest):
                    if 'X-Forwarded-For' in request.headers:
                        return request.headers['X-Forwarded-For'].split(',')[0]
                    return request.remote_ip
    except: return "Unknown"
    return "Unknown"

# --- LIMPEZA DE MEMÓRIA ---
def memory_sweeper():
    if 'last_cleanup' not in st.session_state: st.session_state.last_cleanup = time.time(); return
    if time.time() - st.session_state.last_cleanup > 300:
        st.session_state.word_buffer = None 
        gc.collect()
        st.session_state.last_cleanup = time.time()
    
    if 'last_hard_cleanup' not in st.session_state: st.session_state.last_hard_cleanup = time.time()
    if time.time() - st.session_state.last_hard_cleanup > 14400: # 4h
        st.cache_data.clear()
        gc.collect()
        st.session_state.last_hard_cleanup = time.time()

# --- LÓGICA DE FILA VISUAL ---
def get_ordered_visual_queue(queue, status_dict):
    if not queue: return []
    current_holder = next((c for c, s in status_dict.items() if 'Bastão' in (s or '')), None)
    if not current_holder or current_holder not in queue: return list(queue)
    try:
        idx = queue.index(current_holder)
        return queue[idx:] + queue[:idx]
    except ValueError: return list(queue)

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

# ============================================
# 5. DOCUMENTOS (WORD) - MODELO EXATO
# ============================================
def verificar_duplicidade_certidao(tipo, processo=None, data=None):
    sb = get_supabase()
    if not sb: return False
    try:
        query = sb.table("certidoes_registro").select("*")
        if tipo in ['Físico', 'Eletrônico', 'Física', 'Eletrônica'] and processo:
            proc_limpo = str(processo).strip()
            if not proc_limpo: return False
            response = query.eq("processo", proc_limpo).execute()
            return len(response.data) > 0
        return False
    except Exception as e: return False

def salvar_certidao_db(dados):
    sb = get_supabase()
    if not sb: return False
    try:
        if isinstance(dados.get('data'), (date, datetime)): dados['data'] = dados['data'].isoformat()
        if 'hora_periodo' in dados:
             if dados['hora_periodo']: dados['motivo'] = f"{dados.get('motivo', '')} - Hora/Período: {dados['hora_periodo']}"
             del dados['hora_periodo']
        if 'n_processo' in dados: dados['processo'] = dados.pop('n_processo')
        if 'n_chamado' in dados: dados['incidente'] = dados.pop('n_chamado')
        if 'data_evento' in dados: dados['data'] = dados.pop('data_evento')

        sb.table("certidoes_registro").insert(dados).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Supabase: {e}")
        return False

def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado="", hora="", nome_parte=""):
    try:
        doc = Document()
        section = doc.sections[0]
        section.top_margin = Cm(2.5); section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(3.0); section.right_margin = Cm(3.0)
        style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
        
        # Cabeçalho
        head_p = doc.add_paragraph(); head_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        runner = head_p.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        runner.bold = True
        head_p.add_run("Rua Ouro Preto, N° 1564 - Bairro Santo Agostinho - CEP 30170-041 - Belo Horizonte - MG\nwww.tjmg.jus.br - Andar: 3º e 4º PV")
        doc.add_paragraph("\n")
        
        # Numeração e Assunto
        if tipo == 'Geral': p_num = doc.add_paragraph(f"Parecer GEJUD/DIRTEC/TJMG nº ____/2026. Assunto: Notifica erro no “JPe – 2ª Instância” ao peticionar.")
        else: p_num = doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2026. Assunto: Notifica erro no “JPe – 2ª Instância” ao peticionar.")
        p_num.runs[0].bold = True
        
        # Data
        data_extenso_str = ""
        try:
            dt_obj = datetime.strptime(data, "%d/%m/%Y")
            meses = {1:'janeiro', 2:'fevereiro', 3:'março', 4:'abril', 5:'maio', 6:'junho', 7:'julho', 8:'agosto', 9:'setembro', 10:'outubro', 11:'novembro', 12:'dezembro'}
            data_extenso_str = f"Belo Horizonte, {dt_obj.day} de {meses[dt_obj.month]} de {dt_obj.year}"
        except:
            data_extenso_str = f"Belo Horizonte, {data}" 
        
        doc.add_paragraph(data_extenso_str)
        doc.add_paragraph(f"Exmo(a). Senhor(a) Relator(a),")
        
        if tipo == 'Geral':
            corpo = doc.add_paragraph(); corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            txt = (f"Para fins de cumprimento dos artigos 13 e 14 da Resolução nº 780/2014 do Tribunal de Justiça do Estado de Minas Gerais, "
                   f"informamos que em {data} houve indisponibilidade do portal JPe, superior a uma hora, {hora}, que impossibilitou o peticionamento eletrônico de recursos em processos que já tramitavam no sistema.")
            corpo.add_run(txt)
            doc.add_paragraph("\nColocamo-nos à disposição para outras que se fizerem necessárias.")
            
        elif tipo in ['Eletrônica', 'Eletrônico']:
            corpo = doc.add_paragraph(); corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            corpo.add_run(f"Informamos que de {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}")
            if nome_parte: corpo.add_run(f", Parte/Advogado: {nome_parte}")
            corpo.add_run(".\n\n")
            corpo.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
            corpo.add_run("Esperamos ter prestado as informações solicitadas e colocamo-nos à disposição para outras que se fizerem necessárias.")

        elif tipo in ['Física', 'Físico']:
            corpo1 = doc.add_paragraph(); corpo1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            corpo1.add_run(f"Informamos que no dia {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}")
            if nome_parte: corpo1.add_run(f", Parte/Advogado: {nome_parte}")
            corpo1.add_run(".")
            
            corpo2 = doc.add_paragraph(); corpo2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            corpo2.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).")
            
            corpo3 = doc.add_paragraph(); corpo3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            corpo3.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.")
            doc.add_paragraph("Colocamo-nos à disposição para outras informações que se fizerem necessárias.")

        doc.add_paragraph("\nRespeitosamente,")
        sign = doc.add_paragraph("\n___________________________________\nWaner Andrade Silva\n0-009020-9\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD\nDiretoria Executiva de Tecnologia da Informação e Comunicação - DIRTEC")
        sign.runs[0].bold = True 
        
        buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
        return buffer
    except: return None

# =============================================================================
# FUNÇÃO PRINCIPAL (MOTOR UNIFICADO)
# =============================================================================
def render_dashboard(team_id, team_name, consultores_list, webhook_key, app_url, other_team_id, other_team_name):
    
    # SETUP INICIAL
    DB_APP_ID = team_id
    CONSULTORES = sorted(consultores_list)
    APP_URL_CLOUD = app_url
    CHAT_WEBHOOK_BASTAO = get_secret("chat", webhook_key)
    WEBHOOK_STATE_DUMP = get_secret("webhook", "test_state")

    # --- HELPERS DE NOTIFICAÇÃO ---
    def send_chat_notification_internal(consultor, status):
        if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
            msg = f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {APP_URL_CLOUD}"
            try: send_to_chat("bastao", msg, webhook_url=CHAT_WEBHOOK_BASTAO); return True
            except: return False
        return False

    def send_state_dump_webhook(state_data):
        if not WEBHOOK_STATE_DUMP: return False
        try:
            sanitized_data = clean_data_for_db(state_data)
            headers = {'Content-Type': 'application/json'}
            requests.post(WEBHOOK_STATE_DUMP, data=json.dumps(sanitized_data), headers=headers, timeout=5)
            return True
        except: return False

    def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
        msg = f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n🕐 **Início:** {inicio.strftime('%H:%M')}\n⏱️ **Tempo Total:** {tempo}\n📝 **Motivo:** {motivo}"
        try: send_to_chat("extras", msg); return True
        except: return False

    def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
        jira_str = f"\n🔢 **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
        msg = f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n👥 **Usuário:** {usuario}\n🏢 **Nome/Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {descricao}\n📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{jira_str}"
        try: send_to_chat("registro", msg); return True
        except: return False

    def send_chamado_to_chat(consultor, texto):
        if not consultor or consultor == 'Selecione um nome' or not texto.strip(): return False
        data_envio = get_brazil_time().strftime('%d/%m/%Y %H:%M')
        msg = f"🆘 **Rascunho de Chamado/Jira**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n\n📝 **Texto:**\n{texto}"
        try: send_to_chat('chamado', msg); return True
        except:
            try: send_to_chat('registro', msg); return True
            except: return False

    def handle_erro_novidade_submission(consultor, titulo, objetivo, relato, resultado):
        data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
        msg = f"🐛 **Novo Relato de Erro/Novidade**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n📌 **Título:** {titulo}\n\n🎯 **Objetivo:**\n{objetivo}\n\n🧪 **Relato:**\n{relato}\n\n🏁 **Resultado:**\n{resultado}"
        try: send_to_chat("erro", msg); return True
        except: return False

    def handle_sugestao_submission(consultor, texto):
        data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
        ip_usuario = get_remote_ip()
        msg = f"💡 **Nova Sugestão**\n📅 **Data:** {data_envio}\n👤 **Autor:** {consultor}\n🌐 **IP:** {ip_usuario}\n\n📝 **Sugestão:**\n{texto}"
        try: send_to_chat("extras", msg); return True
        except: return False
    
    def handle_chamado_submission():
         texto = st.session_state.get('chamado_textarea')
         consultor = st.session_state.get('consultor_selectbox')
         return send_chamado_to_chat(consultor, texto)

    # ============================================
    # 7. FUNÇÕES DE ESTADO (CORE LOGIC)
    # ============================================
    def save_state():
        try:
            last_run = st.session_state.report_last_run_date
            visual_queue_calculated = get_ordered_visual_queue(st.session_state.bastao_queue, st.session_state.status_texto)
            state_to_save = {
                'status_texto': st.session_state.status_texto, 'bastao_queue': st.session_state.bastao_queue,
                'visual_queue': visual_queue_calculated, 'skip_flags': st.session_state.skip_flags, 
                'current_status_starts': st.session_state.current_status_starts,
                'bastao_counts': st.session_state.bastao_counts, 'priority_return_queue': st.session_state.priority_return_queue,
                'bastao_start_time': st.session_state.bastao_start_time, 
                'report_last_run_date': last_run, 'daily_logs': st.session_state.daily_logs, 
                'previous_states': st.session_state.get('previous_states', {})
            }
            save_state_to_db(DB_APP_ID, state_to_save)
            load_state_from_db.clear() # Limpa cache
        except Exception as e: print(f"Erro save: {e}")

    def sync_state_from_db():
        try:
            db_data = load_state_from_db(DB_APP_ID)
            if not db_data: return
            keys = ['status_texto', 'bastao_queue', 'skip_flags', 'bastao_counts', 'priority_return_queue', 'daily_logs', 'previous_states']
            for k in keys:
                if k in db_data: 
                    if k == 'daily_logs' and isinstance(db_data[k], list) and len(db_data[k]) > 150:
                        st.session_state[k] = db_data[k][-150:] 
                    else: st.session_state[k] = db_data[k]
            
            # CORREÇÃO CRÍTICA DE DATA
            if 'bastao_start_time' in db_data and db_data['bastao_start_time']:
                try:
                    if isinstance(db_data['bastao_start_time'], str): st.session_state['bastao_start_time'] = datetime.fromisoformat(db_data['bastao_start_time'])
                    else: st.session_state['bastao_start_time'] = db_data['bastao_start_time']
                except: st.session_state['bastao_start_time'] = get_brazil_time()
            
            if 'current_status_starts' in db_data:
                starts = db_data['current_status_starts']
                for nome, val in starts.items():
                    if isinstance(val, str):
                        try: st.session_state.current_status_starts[nome] = datetime.fromisoformat(val)
                        except: pass
                    else: st.session_state.current_status_starts[nome] = val
        except Exception as e: print(f"Erro sync: {e}")

    def log_status_change(consultor, old_status, new_status, duration):
        if not isinstance(duration, timedelta): duration = timedelta(0)
        now_br = get_brazil_time()
        st.session_state.daily_logs.append({
            'timestamp': now_br, 'consultor': consultor, 
            'old_status': old_status or 'Fila', 'new_status': new_status or 'Fila', 
            'duration': duration, 'ip': st.session_state.get('device_id_val', 'unknown')
        })
        if len(st.session_state.daily_logs) > 150: st.session_state.daily_logs = st.session_state.daily_logs[-150:]
        st.session_state.current_status_starts[consultor] = now_br

    def find_next_holder_index(current_index, queue, skips):
        if not queue: return -1
        n = len(queue); start_index = (current_index + 1) % n
        for i in range(n):
            idx = (start_index + i) % n
            if not skips.get(queue[idx], False): return idx
        if n > 1:
            proximo_imediato_idx = (current_index + 1) % n
            nome_escolhido = queue[proximo_imediato_idx]; st.session_state.skip_flags[nome_escolhido] = False 
            return proximo_imediato_idx
        return -1

    def send_daily_report_to_webhook():
        logs = st.session_state.daily_logs
        if not logs: return False
        try: send_state_dump_webhook({'logs': st.session_state.daily_logs})
        except: pass

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
                    log_status_change(c, 'Bastão', '', now - st.session_state.current_status_starts.get(c, now))
                    st.session_state.status_texto[c] = ''; changed = True
        
        if target:
            curr_s = st.session_state.status_texto.get(target, '')
            if 'Bastão' not in curr_s:
                new_s = f"Bastão | {curr_s}" if curr_s and "Bastão" not in curr_s else "Bastão"
                log_status_change(target, curr_s, new_s, now - st.session_state.current_status_starts.get(target, now))
                st.session_state.status_texto[target] = new_s; st.session_state.bastao_start_time = now
                if current_holder != target: 
                    st.session_state.play_sound = True; send_chat_notification_internal(target, 'Bastão')
                st.session_state.skip_flags[target] = False
                changed = True
        
        if changed: save_state()
        return changed

    # --- LÓGICA ATUALIZADA: UPDATE_STATUS ---
    def update_status(novo_status: str, marcar_indisponivel: bool = False, manter_fila_atual: bool = False):
        selected = st.session_state.get('consultor_selectbox')
        if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
        
        ensure_daily_reset()
        now_br = get_brazil_time()
        current = st.session_state.status_texto.get(selected, '')
        current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in (s or '')), None)
        
        # Se for Almoço, salva estado anterior
        if novo_status == 'Almoço':
            st.session_state.previous_states[selected] = {'status': current, 'in_queue': selected in st.session_state.bastao_queue}
        
        if marcar_indisponivel:
            st.session_state.skip_flags[selected] = True
            if selected in st.session_state.bastao_queue:
                st.session_state.bastao_queue.remove(selected)
        
        if novo_status == 'Indisponível':
            if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)

        elif not manter_fila_atual:
            if selected not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(selected)
            st.session_state.skip_flags[selected] = False
        
        final_status = (novo_status or '').strip()
        # Se tem o bastão, mantém o prefixo
        if selected == current_holder and selected in st.session_state.bastao_queue:
            final_status = ('Bastão | ' + final_status).strip(' |') if final_status else 'Bastão'
        
        # REGRA DE SAÍDA: Se vazio e não estiver na fila, fica vazio (não indisponível)
        if not final_status and (selected not in st.session_state.bastao_queue): final_status = ''
        
        log_status_change(selected, current, final_status, now_br - st.session_state.current_status_starts.get(selected, now_br))
        
        st.session_state.status_texto[selected] = final_status
        check_and_assume_baton()
        save_state()

    # --- LÓGICA ATUALIZADA: ENTRAR/SAIR (TOGGLE) ---
    def toggle_queue(consultor):
        ensure_daily_reset(); now_br = get_brazil_time()
        
        # REGRA PEDIDA: Se está na fila -> Vai para Indisponível (Sai da lista)
        # Se NÃO está na fila (mas estava ocupado) -> Vai para Fila (Livre)
        if consultor in st.session_state.bastao_queue:
            # SAI DA FILA -> Vira Indisponível
            st.session_state.bastao_queue.remove(consultor)
            st.session_state.status_texto[consultor] = '' # Limpa visualmente, mas saiu da fila
            check_and_assume_baton()
        else:
            # ENTRA NA FILA
            st.session_state.bastao_queue.append(consultor)
            st.session_state.skip_flags[consultor] = False
            # Se estava ocupado com algo, limpa status para mostrar que está livre na fila?
            # Ou mantém status anterior? Geralmente "Entrar na fila" implica estar livre.
            st.session_state.status_texto[consultor] = '' 
            check_and_assume_baton()
        save_state()

    def rotate_bastao():
        ensure_daily_reset(); selected = st.session_state.consultor_selectbox
        if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
        
        queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags
        current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        
        if selected != current_holder: st.error(f"⚠️ Apenas quem está com o bastão ({current_holder}) pode passá-lo!"); return
            
        current_index = queue.index(current_holder) if current_holder in queue else -1
        next_idx = find_next_holder_index(current_index, queue, skips)
        if next_idx == -1 and len(queue) > 1: next_idx = (current_index + 1) % len(queue)
        
        if next_idx != -1:
            n_queue = len(queue); tmp_idx = (current_index + 1) % n_queue
            while tmp_idx != next_idx:
                if st.session_state.skip_flags.get(queue[tmp_idx], False): st.session_state.skip_flags[queue[tmp_idx]] = False
                tmp_idx = (tmp_idx + 1) % n_queue
            next_holder = queue[next_idx]; st.session_state.skip_flags[next_holder] = False; now_br = get_brazil_time()
            
            old_h = st.session_state.status_texto[current_holder]
            new_h = old_h.replace('Bastão | ', '').replace('Bastão', '').strip()
            log_status_change(current_holder, old_h, new_h, now_br - (st.session_state.bastao_start_time or now_br))
            st.session_state.status_texto[current_holder] = new_h
            
            old_n = st.session_state.status_texto.get(next_holder, '')
            new_n = f"Bastão | {old_n}" if old_n else "Bastão"
            log_status_change(next_holder, old_n, new_n, timedelta(0))
            st.session_state.status_texto[next_holder] = new_n
            
            st.session_state.bastao_start_time = now_br
            send_chat_notification_internal(next_holder, 'Bastão')
            save_state()
        else: check_and_assume_baton()

    def toggle_skip():
        selected = st.session_state.consultor_selectbox
        if not selected or selected == 'Selecione um nome': return
        if selected not in st.session_state.bastao_queue: return
        st.session_state.skip_flags[selected] = not st.session_state.skip_flags.get(selected, False)
        save_state()

    def toggle_emoji(emoji_char):
        selected = st.session_state.consultor_selectbox
        if not selected or selected == 'Selecione um nome': return
        current = st.session_state.status_texto.get(selected, '')
        
        if emoji_char in current:
            # Remove
            new_s = current.replace(emoji_char, '').strip()
        else:
            # Adiciona
            new_s = f"{current} {emoji_char}".strip()
        
        st.session_state.status_texto[selected] = new_s
        save_state()

    def toggle_view(v):
        if st.session_state.active_view == v: st.session_state.active_view = None
        else: st.session_state.active_view = v

    def reset_day_state():
        st.session_state.bastao_queue = []
        st.session_state.status_texto = {n: '' for n in CONSULTORES} # Reset limpo
        st.session_state.daily_logs = []
        st.session_state.report_last_run_date = get_brazil_time()

    def ensure_daily_reset():
        now_br = get_brazil_time()
        last_run = st.session_state.report_last_run_date
        if isinstance(last_run, str):
            try: last_run_dt = datetime.fromisoformat(last_run).date()
            except: last_run_dt = date.min
        elif isinstance(last_run, datetime): last_run_dt = last_run.date()
        else: last_run_dt = date.min

        if now_br.date() > last_run_dt:
            if st.session_state.daily_logs: 
                full_state = {'date': now_br.isoformat(), 'logs': st.session_state.daily_logs}
                send_state_dump_webhook(full_state)
            reset_day_state(); save_state()

    def auto_manage_time():
        ensure_daily_reset()

    def init_session_state():
        dev = get_browser_id(); 
        if dev: st.session_state['device_id_val'] = dev
        if 'db_loaded' not in st.session_state:
            db = load_state_from_db(DB_APP_ID)
            if 'report_last_run_date' in db and isinstance(db['report_last_run_date'], str):
                try: db['report_last_run_date'] = datetime.fromisoformat(db['report_last_run_date'])
                except: db['report_last_run_date'] = datetime.min
            st.session_state.update(db); st.session_state['db_loaded'] = True
        
        defaults = {
            'bastao_start_time': None, 'report_last_run_date': datetime.min, 'active_view': None,
            'consultor_selectbox': "Selecione um nome", 'status_texto': {n: '' for n in CONSULTORES},
            'bastao_queue': [], 'skip_flags': {}, 'current_status_starts': {n: get_brazil_time() for n in CONSULTORES},
            'bastao_counts': {n: 0 for n in CONSULTORES}, 'priority_return_queue': [], 'daily_logs': [],
            'word_buffer': None, 'aviso_duplicidade': False, 'previous_states': {}, 'view_logmein_ui': False
        }
        for k, v in defaults.items():
            if k not in st.session_state: st.session_state[k] = v
        for n in CONSULTORES:
            st.session_state.skip_flags.setdefault(n, False)

    def open_logmein_ui(): st.session_state.view_logmein_ui = True
    def close_logmein_ui(): st.session_state.view_logmein_ui = False

    # ============================================
    # 8. INTERFACE VISUAL
    # ============================================
    st.markdown("""<style>div.stButton > button {width: 100%; height: 3rem;}</style>""", unsafe_allow_html=True)
    init_session_state(); memory_sweeper(); auto_manage_time()

    # --- SIDEBAR (COM RAMAIS E LOGMEIN SUSPENSOS) ---
    with st.sidebar:
        st.markdown(f"### 🏢 {team_name}")
        st.caption("Central Unificada 2026")
        
        # Botão de Sair/Home
        if st.button("🚪 Sair (Home)", use_container_width=True):
            st.session_state["time_selecionado"] = None; st.rerun()

        st.divider()

        # LOGMEIN EM EXPANDER
        with st.expander("🔑 LogMeIn", expanded=False):
            l_user, l_in_use = get_logmein_status()
            if l_in_use:
                st.error(f"Em uso: {l_user}")
                if st.button("Liberar", key="btn_lib_log_side"):
                    set_logmein_status(None, False); st.rerun()
            else:
                st.success("Livre")
                meu_nome = st.session_state.get('consultor_selectbox')
                if meu_nome and meu_nome != "Selecione um nome":
                    if st.button("Assumir", key="btn_ass_log_side"):
                        set_logmein_status(meu_nome, True); st.rerun()
                else:
                    st.info("Selecione seu nome.")

        # FILA VIZINHA COM RAMAIS
        with st.expander(f"👀 Fila {other_team_name}", expanded=False):
            other_data = load_state_from_db(other_team_id)
            other_queue = other_data.get('bastao_queue', [])
            other_status = other_data.get('status_texto', {})
            
            if not other_queue: st.info("Fila vazia.")
            else:
                # Ordenação visual
                other_holder = next((c for c, s in other_status.items() if 'Bastão' in s), None)
                try: idx = other_queue.index(other_holder)
                except: idx = 0
                ordered = other_queue[idx:] + other_queue[:idx] if other_holder else other_queue
                
                for i, nome in enumerate(ordered):
                    extra = "🎭" if nome == other_holder else f"{i}º"
                    ramal = RAMAIS_CESUPE.get(nome, "----") # Busca ramal
                    status_extra = other_status.get(nome, "")
                    # Mostra se está no telefone ou café
                    icons = ""
                    if "📞" in status_extra: icons += "📞 "
                    if "☕" in status_extra: icons += "☕ "
                    
                    st.markdown(f"**{extra} {nome}** (☎️ {ramal}) {icons}")

    # --- HEADER ---
    @st.fragment(run_every=15)
    def render_header_info_left():
        sync_state_from_db()
        c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
        with c_topo_esq:
            img = get_img_as_base64_cached(PUG2026_FILENAME); src = f"data:image/png;base64,{img}" if img else GIF_BASTAO_HOLDER
            st.markdown(f"""<div style="display: flex; align-items: center; gap: 15px;"><h1 style="margin: 0; padding: 0; font-size: 2.2rem; color: #FF8C00; text-shadow: 1px 1px 2px #FF4500;">Controle {team_name} {BASTAO_EMOJI}</h1><img src="{src}" style="width: 150px; height: 150px; border-radius: 10px; border: 4px solid #FF8C00; object-fit: cover;"></div>""", unsafe_allow_html=True)
        with c_topo_dir:
            c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
            with c_sub1: 
                 novo_responsavel = st.selectbox("Assumir (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
            with c_sub2:
                if st.button("🚀 Entrar", use_container_width=True, key="btn_entrar_header"):
                    if novo_responsavel != "Selecione": toggle_queue(novo_responsavel); st.rerun()
            if st.button("🔄 Atualizar", use_container_width=True): load_state_from_db(DB_APP_ID); st.rerun()

        st.markdown("<hr style='border: 1px solid #FF8C00; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)
        
        queue = st.session_state.bastao_queue
        skips = st.session_state.skip_flags
        responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        curr_idx = queue.index(responsavel) if responsavel in queue else -1
        prox_idx = find_next_holder_index(curr_idx, queue, skips)
        proximo = queue[prox_idx] if prox_idx != -1 else None

        st.header("Responsável pelo Bastão")
        if responsavel:
            st.markdown(f"""<div style="background: linear-gradient(135deg, #FFF3E0 0%, #FFFFFF 100%); border: 3px solid #FF8C00; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255, 140, 0, 0.3); margin-bottom: 20px;"><div style="flex-shrink: 0; margin-right: 25px;"><img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #FF8C00;"></div><div><span style="font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px;">Atualmente com:</span><br><span style="font-size: 42px; font-weight: 800; color: #FF4500; line-height: 1.1;">{responsavel}</span></div></div>""", unsafe_allow_html=True)
            
            # Correção de Data
            start_t = st.session_state.bastao_start_time
            if start_t and isinstance(start_t, str):
                try: start_t = datetime.fromisoformat(start_t)
                except: start_t = get_brazil_time()
            elif not start_t: start_t = get_brazil_time()
                
            dur = get_brazil_time() - start_t
            st.caption(f"⏱️ Tempo com o bastão: **{format_time_duration(dur)}**")
        else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
        
        st.markdown("###"); st.header("Próximos da Fila")
        if responsavel and responsavel in queue:
            c_idx = queue.index(responsavel)
            raw_ordered = queue[c_idx+1:] + queue[:c_idx]
        else: raw_ordered = list(queue)
        demais_na_fila = [n for n in raw_ordered if n != proximo and not skips.get(n, False)]
        
        if proximo: st.markdown(f"**Próximo Bastão:** {proximo}")
        else: st.markdown("**Próximo Bastão:** _Ninguém elegível_")
        if demais_na_fila: st.markdown(f"**Demais na fila:** {', '.join(demais_na_fila)}")
        else: st.markdown("**Demais na fila:** _Vazio_")

    # FRAGMENTO DE STATUS
    @st.fragment(run_every=15)
    def render_status_list():
        sync_state_from_db()
        queue = st.session_state.bastao_queue
        skips = st.session_state.skip_flags
        responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)

        st.header('Status Consultores')
        ui_lists = {'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade_especifica': [], 'sessao_especifica': [], 'projeto_especifico': [], 'reuniao_especifica': [], 'treinamento_especifico': [], 'indisponivel': [], 'presencial_especifico': []}
        for nome in CONSULTORES:
            if nome in st.session_state.bastao_queue: ui_lists['fila'].append(nome)
            status = st.session_state.status_texto.get(nome, ''); status = status if status is not None else ''
            if status in ('', None): pass
            elif status == 'Almoço': ui_lists['almoco'].append(nome)
            elif status == 'Saída rápida': ui_lists['saida'].append(nome)
            elif status == 'Indisponível' and nome not in st.session_state.bastao_queue: ui_lists['indisponivel'].append(nome)
            if isinstance(status, str):
                if 'Sessão:' in status: ui_lists['sessao_especifica'].append((nome, status.replace('Sessão:', '').strip()))
                if 'Reunião:' in status: ui_lists['reuniao_especifica'].append((nome, status.replace('Reunião:', '').strip()))
                if 'Projeto:' in status: ui_lists['projeto_especifico'].append((nome, status.replace('Projeto:', '').strip()))
                if 'Treinamento:' in status: ui_lists['treinamento_especifico'].append((nome, status.replace('Treinamento:', '').strip()))
                if 'Atividade:' in status: ui_lists['atividade_especifica'].append((nome, status.replace('Atividade:', '').strip()))
                if 'Atendimento Presencial:' in status: ui_lists['presencial_especifico'].append((nome, status.replace('Atendimento Presencial:', '').strip()))

        st.subheader(f'✅ Na Fila ({len(ui_lists["fila"])})')
        render_order = get_ordered_visual_queue(queue, st.session_state.status_texto)
        if not render_order and queue: render_order = list(queue)
        if not render_order: st.markdown('_Ninguém na fila._')
        else:
            for i, nome in enumerate(render_order):
                if nome not in ui_lists['fila']: continue
                col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment='center')
                col_check.checkbox(' ', key=f'chk_fila_{nome}_frag', value=True, disabled=True, label_visibility='collapsed')
                skip_flag = skips.get(nome, False); status_atual = st.session_state.status_texto.get(nome, '') or ''; extra = ''
                if 'Atividade' in status_atual: extra += ' 📋'
                if 'Projeto' in status_atual: extra += ' 🏗️'
                if "📞" in status_atual: extra += ' 📞'
                if "☕" in status_atual: extra += ' ☕'
                
                if nome == responsavel: display = f'<span style="background-color: #FF8C00; color: #FFF; padding: 2px 6px; border-radius: 5px; font-weight: 800;">🎭 {nome}</span>'
                elif skip_flag: display = f'<strong>{i}º {nome}</strong>{extra} <span style="background-color: #FFECB3; padding: 2px 8px; border-radius: 10px;">Pulando ⏭️</span>'
                else: display = f'<strong>{i}º {nome}</strong>{extra} <span style="background-color: #FFE0B2; padding: 2px 8px; border-radius: 10px;">Aguardando</span>'
                col_nome.markdown(display, unsafe_allow_html=True)
        st.markdown('---')

        def _render_section(titulo, icon, itens, cor, key_rm):
            colors = {'orange': '#FFECB3', 'blue': '#BBDEFB', 'teal': '#B2DFDB', 'violet': '#E1BEE7', 'green': '#C8E6C9', 'red': '#FFCDD2', 'grey': '#EEEEEE', 'yellow': '#FFF9C4'}
            bg_hex = colors.get(cor, '#EEEEEE'); st.subheader(f'{icon} {titulo} ({len(itens)})')
            if not itens: st.markdown(f'_Nenhum._')
            else:
                for item in itens:
                    nome = item[0] if isinstance(item, tuple) else item
                    desc = item[1] if isinstance(item, tuple) else titulo
                    st.markdown(f"<div style='font-size: 16px; margin: 2px 0;'><strong>{nome}</strong><span style='background-color: {bg_hex}; color: #333; padding: 2px 8px; border-radius: 12px; font-size: 14px; margin-left: 8px;'>{desc}</span></div>", unsafe_allow_html=True)
            st.markdown('---')
            
        _render_section('Atend. Presencial', '🤝', ui_lists['presencial_especifico'], 'yellow', 'Atendimento Presencial')
        _render_section('Em Demanda', '📋', ui_lists['atividade_especifica'], 'orange', 'Atividade')
        _render_section('Projetos', '🏗️', ui_lists['projeto_especifico'], 'blue', 'Projeto')
        _render_section('Treinamento', '🎓', ui_lists['treinamento_especifico'], 'teal', 'Treinamento')
        _render_section('Reuniões', '📅', ui_lists['reuniao_especifica'], 'violet', 'Reunião')
        _render_section('Almoço', '🍽️', ui_lists['almoco'], 'red', 'Almoço')
        _render_section('Sessão', '🎙️', ui_lists['sessao_especifica'], 'green', 'Sessão')
        _render_section('Saída rápida', '🚶', ui_lists['saida'], 'red', 'Saída rápida')
        _render_section('Indisponível', '❌', ui_lists['indisponivel'], 'grey', '')

    # --- LAYOUT PRINCIPAL ---
    col_principal, col_disponibilidade = st.columns([1.5, 1])

    with col_principal:
        render_header_info_left()

    with col_disponibilidade:
        render_status_list()

    with col_principal:
        st.markdown("### 🎮 Painel de Ação")
        
        # IDENTIDADE FIXA (Se selecionada)
        curr = st.session_state.get('consultor_selectbox')
        if curr and curr != "Selecione um nome":
            st.success(f"**Logado como:** {curr}")
        else:
            st.info("Selecione seu nome abaixo:")
        
        c_nome, c_act1, c_act2, c_act3 = st.columns([2, 1, 1, 1], vertical_alignment="bottom")
        with c_nome:
            st.selectbox('Sou:', ['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
        with c_act1:
            if st.button("🎭 Entrar/Sair", use_container_width=True): 
                 toggle_queue(st.session_state.consultor_selectbox); st.rerun()
        with c_act2:
            if st.button('🎯 Passar', use_container_width=True): 
                 rotate_bastao(); st.rerun()
        with c_act3:
            if st.button('⏭️ Pular', use_container_width=True): 
                 toggle_skip(); st.rerun()
        
        # BOTÕES DE STATUS
        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        if r2c1.button('📋 Atividades', use_container_width=True): toggle_view('menu_atividades'); st.rerun()
        if r2c2.button('🏗️ Projeto', use_container_width=True): toggle_view('menu_projetos'); st.rerun()
        if r2c3.button('🎓 Treino', use_container_width=True): toggle_view('menu_treinamento'); st.rerun()
        if r2c4.button('📅 Reunião', use_container_width=True): toggle_view('menu_reuniao'); st.rerun()
        if r2c5.button('🍽️ Almoço', use_container_width=True): update_status('Almoço', True); st.rerun()
        
        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        if r3c1.button('🎙️ Sessão', use_container_width=True): toggle_view('menu_sessao'); st.rerun()
        if r3c2.button('🚶 Saída', use_container_width=True): update_status('Saída rápida', True); st.rerun()
        if r3c3.button('🏃 Sair Geral', use_container_width=True): update_status('Indisponível', True); st.rerun()
        if r3c4.button("🤝 Presencial", use_container_width=True): toggle_view('menu_presencial'); st.rerun()

        # BOTÕES EXTRAS (TELEFONE / CAFÉ)
        c_ex1, c_ex2 = st.columns(2)
        if c_ex1.button("📞 Telefone (Toggle)", use_container_width=True): toggle_emoji("📞"); st.rerun()
        if c_ex2.button("☕ Café (Toggle)", use_container_width=True): toggle_emoji("☕"); st.rerun()

        # MENUS DE AÇÃO (EXPANSÍVEIS)
        if st.session_state.active_view == 'menu_atividades':
            with st.container(border=True):
                at_t = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS); at_e = st.text_input("Detalhe:")
                manter = st.checkbox("Manter na fila do bastão?", value=True)
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    if st.button("Confirmar", type="primary", use_container_width=True): 
                        st.session_state.active_view = None
                        update_status(f"Atividade: {', '.join(at_t)} - {at_e}", manter_fila_atual=manter)
                with c2:
                    if st.button("Sair de atividades", use_container_width=True):
                        st.session_state.active_view = None; update_status("", manter_fila_atual=True) 
                with c3:
                    if st.button("Cancelar", use_container_width=True): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == 'menu_presencial':
            with st.container(border=True):
                st.subheader('🤝 Registrar Atendimento Presencial'); local_presencial = st.text_input('Local:', key='pres_local'); objetivo_presencial = st.text_input('Objetivo:', key='pres_obj')
                c_ok, c_cancel = st.columns(2)
                with c_ok:
                    if st.button('✅ Confirmar', type='primary', use_container_width=True):
                        if not local_presencial.strip() or not objetivo_presencial.strip(): st.warning('Preencha Local e Objetivo.')
                        else: st.session_state.active_view = None; update_status(f"Atendimento Presencial: {local_presencial.strip()} - {objetivo_presencial.strip()}", True)
                with c_cancel:
                    if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == 'menu_projetos':
            with st.container(border=True):
                st.subheader('🏗️ Registrar Projeto')
                proj_nome = st.text_input('Nome do Projeto:', placeholder='Digite o nome do projeto...')
                manter_bastao = st.checkbox("Continuar recebendo bastão? (Modo Atividade)", value=True)
                c_ok, c_cancel = st.columns(2)
                with c_ok:
                    if st.button('✅ Confirmar', type='primary', use_container_width=True):
                        if not proj_nome.strip(): st.warning('Digite o nome do projeto.')
                        else: 
                            st.session_state.active_view = None
                            status_msg = f"Projeto: {proj_nome.strip()}"
                            update_status(status_msg, manter_fila_atual=manter_bastao)
                with c_cancel:
                    if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == 'menu_treinamento':
            with st.container(border=True):
                st.subheader('🎓 Registrar Treinamento'); tema = st.text_input('Tema/Conteúdo:'); obs = st.text_input('Observação (opcional):')
                c_ok, c_cancel = st.columns(2)
                with c_ok:
                    if st.button('✅ Confirmar', type='primary', use_container_width=True):
                        if not tema.strip(): st.warning('Informe o tema.')
                        else: st.session_state.active_view = None; update_status(f"Treinamento: {tema.strip()}" + (f" - {obs.strip()}" if obs.strip() else ""), True)
                with c_cancel:
                    if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == 'menu_reuniao':
            with st.container(border=True):
                st.subheader('📅 Registrar Reunião'); assunto = st.text_input('Assunto:'); obs = st.text_input('Observação (opcional):')
                c_ok, c_cancel = st.columns(2)
                with c_ok:
                    if st.button('✅ Confirmar', type='primary', use_container_width=True):
                        if not assunto.strip(): st.warning('Informe o assunto.')
                        else: st.session_state.active_view = None; update_status(f"Reunião: {assunto.strip()}" + (f" - {obs.strip()}" if obs.strip() else ""), True)
                with c_cancel:
                    if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == 'menu_sessao':
            with st.container(border=True):
                st.subheader('🎙️ Registrar Sessão')
                sessao_livre = st.text_input('Qual Sessão / Câmara?'); obs = st.text_input('Observação (opcional):')
                c_ok, c_cancel = st.columns(2)
                with c_ok:
                    if st.button('✅ Confirmar', type='primary', use_container_width=True):
                        if not sessao_livre.strip(): st.warning('Digite qual a sessão.')
                        else: st.session_state.active_view = None; update_status(f"Sessão: {sessao_livre}" + (f" - {obs.strip()}" if obs.strip() else ""), True)
                with c_cancel:
                    if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()
                        
        # --- FERRAMENTAS ESPECIAIS ---
        st.markdown("<hr style='border: 1px solid #FF8C00;'>", unsafe_allow_html=True)
        st.markdown("#### Ferramentas")
        
        c_t1, c_t2, c_t3, c_t4 = st.columns(4)
        c_t1.button("📑 Checklist", use_container_width=True, on_click=toggle_view, args=("checklist",))
        c_t2.button("🆘 Chamados", use_container_width=True, on_click=toggle_view, args=("chamados",))
        c_t3.button("📝 Atendimentos", use_container_width=True, on_click=toggle_view, args=("atendimentos",))
        c_t4.button("⏰ H. Extras", use_container_width=True, on_click=toggle_view, args=("hextras",))
        
        c_t5, c_t6, c_t7 = st.columns(3)
        c_t5.button("🐛 Erro/Novidade", use_container_width=True, on_click=toggle_view, args=("erro_novidade",))
        c_t6.button("🖨️ Certidão", use_container_width=True, on_click=toggle_view, args=("certidao",))
        c_t7.button("💡 Sugestão", use_container_width=True, on_click=toggle_view, args=("sugestao",))

        if st.session_state.active_view == "checklist":
            with st.container(border=True):
                st.header("Gerador de Checklist"); data_eproc = st.date_input("Data:", value=get_brazil_time().date()); camara_eproc = st.text_input("Câmara:")
                if st.button("Gerar HTML"): send_to_chat("sessao", f"Consultor {st.session_state.consultor_selectbox} acompanhando sessão {camara_eproc}"); st.success("Registrado no chat!")
                if st.button("❌ Cancelar"): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == "chamados":
            with st.container(border=True):
                st.header('🆘 Chamados (Padrão / Jira)')
                st.text_area('Texto do chamado:', height=240, key='chamado_textarea')
                c1, c2 = st.columns(2)
                with c1:
                    if st.button('Enviar', type='primary', use_container_width=True): 
                        if handle_chamado_submission(): st.success('Enviado!'); st.session_state.active_view = None; st.rerun()
                        else: st.error('Erro ao enviar.')
                with c2:
                        if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == "atendimentos":
            with st.container(border=True):
                st.header('📝 Registro de Atendimentos')
                at_data = st.date_input('Data:', value=get_brazil_time().date())
                at_usuario = st.selectbox('Usuário:', REG_USUARIO_OPCOES); at_setor = st.text_input('Setor:'); at_sys = st.selectbox('Sistema:', REG_SISTEMA_OPCOES)
                at_desc = st.text_input('Descrição:'); at_canal = st.selectbox('Canal:', REG_CANAL_OPCOES); at_res = st.selectbox('Desfecho:', REG_DESFECHO_OPCOES); at_jira = st.text_input('Jira:')
                if st.button('Enviar', type='primary', use_container_width=True):
                    if send_atendimento_to_chat(st.session_state.consultor_selectbox, at_data, at_usuario, at_setor, at_sys, at_desc, at_canal, at_res, at_jira):
                        st.success('Enviado!'); st.session_state.active_view = None; st.rerun()
                    else: st.error('Erro.')
                if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == "hextras":
            with st.container(border=True):
                st.header("⏰ Horas Extras"); d_ex = st.date_input("Data:"); h_in = st.time_input("Início:"); t_ex = st.text_input("Tempo Total:"); mot = st.text_input("Motivo:")
                if st.button("Registrar"): 
                    if send_horas_extras_to_chat(st.session_state.consultor_selectbox, d_ex, h_in, t_ex, mot): st.success("Registrado!"); st.session_state.active_view = None; st.rerun()
                if st.button("❌ Cancelar"): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == "erro_novidade":
            with st.container(border=True):
                st.header("🐛 Erro/Novidade"); tit = st.text_input("Título:"); obj = st.text_area("Objetivo:"); rel = st.text_area("Relato:"); res = st.text_area("Resultado:")
                if st.button("Enviar"): 
                    if handle_erro_novidade_submission(st.session_state.consultor_selectbox, tit, obj, rel, res): st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
                if st.button("❌ Cancelar"): st.session_state.active_view = None; st.rerun()

        if st.session_state.active_view == "certidao":
            with st.container(border=True):
                st.header("🖨️ Registro de Certidão (2026)")
                c_data = st.date_input("Data do Evento:", value=get_brazil_time().date(), format="DD/MM/YYYY")
                tipo_cert = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"])
                c_cons = st.session_state.consultor_selectbox
                c_hora = ""; c_motivo = st.text_area("Motivo/Detalhes:", height=100)
                if tipo_cert == "Geral": 
                    c_hora = st.text_input("Horário/Período (Ex: 13h às 15h):")
                    c_proc = ""; c_chamado = ""; c_nome_parte = ""; c_peticao = ""
                    if c_hora: c_motivo = f"{c_motivo} - Período: {c_hora}"
                else: 
                    c1, c2 = st.columns(2)
                    c_proc = c1.text_input("Processo (Com pontuação):")
                    c_chamado = c2.text_input("Incidente/Chamado:")
                    c3, c4 = st.columns(2)
                    c_nome_parte = c3.text_input("Nome da Parte/Advogado:")
                    c_peticao = c4.selectbox("Tipo de Petição:", ["Inicial", "Recursal", "Intermediária", "Outros"])
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("📄 Gerar Word", use_container_width=True): 
                        st.session_state.word_buffer = gerar_docx_certidao_internal(tipo_cert, c_proc, c_data.strftime("%d/%m/%Y"), c_cons, c_motivo, c_chamado, c_hora, c_nome_parte)
                    if st.session_state.word_buffer: st.download_button("⬇️ Baixar", st.session_state.word_buffer, file_name="certidao.docx")
                with c2:
                    if st.button("💾 Salvar e Notificar", type="primary", use_container_width=True):
                        if verificar_duplicidade_certidao(tipo_cert, c_proc, c_data): st.session_state.aviso_duplicidade = True
                        else:
                            payload = {"tipo": tipo_cert, "data": c_data.isoformat(), "consultor": c_cons, "incidente": c_chamado, "processo": c_proc, "motivo": c_motivo, "nome_parte": c_nome_parte, "peticao": c_peticao}
                            if salvar_certidao_db(payload):
                                msg_cert = f"🖨️ **Nova Certidão Registrada**\n👤 **Autor:** {c_cons}\n📅 **Data:** {c_data.strftime('%d/%m/%Y')}\n📄 **Tipo:** {tipo_cert}\n📂 **Proc:** {c_proc}"
                                try: send_to_chat("certidao", msg_cert)
                                except Exception as e: st.error(f"Erro Webhook: {e}")
                                st.success("Salvo!"); time.sleep(1); st.session_state.active_view = None; st.session_state.word_buffer = None; st.rerun()
                            else: st.error("Erro ao salvar no banco.")
                if st.button("❌ Cancelar"): st.session_state.active_view = None; st.rerun()
                if st.session_state.get('aviso_duplicidade'): st.error("⚠️ Este processo já possui registro de certidão!"); st.button("Ok, entendi", on_click=st.rerun)

        if st.session_state.active_view == "sugestao":
            with st.container(border=True):
                st.header("💡 Enviar Sugestão")
                sug_txt = st.text_area("Sua ideia ou melhoria:")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Enviar Sugestão", type="primary", use_container_width=True):
                        if handle_sugestao_submission(st.session_state.consultor_selectbox, sug_txt): st.success("Enviado com sucesso!"); st.session_state.active_view = None; st.rerun()
                        else: st.error("Erro ao enviar.")
                with c2:
                    if st.button("Cancelar", use_container_width=True): st.session_state.active_view = None; st.rerun()
        
        # --- GRÁFICO OPERACIONAL ---
        st.markdown("---")
        st.subheader("📊 Resumo Operacional")
        
        df_chart, gerado_em = carregar_dados_grafico(DB_APP_ID)
        
        if df_chart is not None:
            try:
                df_long = df_chart.melt(id_vars=['relatorio'], value_vars=['Eproc', 'Legados'], var_name='Sistema', value_name='Qtd')
                base = alt.Chart(df_long).encode(
                    x=alt.X('relatorio', title=None, axis=alt.Axis(labels=True, labelAngle=0)),
                    y=alt.Y('Qtd', title='Quantidade'),
                    color=alt.Color('Sistema', legend=alt.Legend(title="Sistema")),
                    xOffset='Sistema'
                )
                bars = base.mark_bar()
                text = base.mark_text(dy=-5, color='black').encode(text='Qtd')
                final_chart = (bars + text).properties(height=300)
                st.altair_chart(final_chart, use_container_width=True)
                st.caption(f"Dados do dia: {gerado_em} (Atualização diária)")
                st.markdown("### Dados Detalhados")
                st.dataframe(df_chart, use_container_width=True)
            except Exception as e: st.error(f"Erro gráfico: {e}")
        else: st.info("Sem dados de resumo disponíveis.")
