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

# ============================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ============================================
# Lista de Ramais Completa (Solicitada)
RAMAIS_MAP = {
    "Alex Paulo": "2510", 
    "Barbara Mara": "2517", 
    "Bruno Glaicon": "2644", 
    "Claudio": "2667",
    "Claudia Luiza": "2667",
    "Dirceu Gonçalves": "2666", 
    "Douglas De Souza": "2659", 
    "Douglas Paiva": "2663",
    "Fábio Alves": "2665", 
    "Farley Leandro": "2651", 
    "Gilberto": "2654", 
    "Gleis Da Silva": "2536",
    "Glayce Torres": "2647", 
    "Hugo Leonardo": "2650", 
    "Jerry Marcos": "2654", 
    "Jonatas Gomes": "2656",
    "Leandro Victor": "2652", 
    "Leonardo Damaceno": "2655", 
    "Ivana Guimarães": "2653",
    "Marcelo PenaGuerra": "2655", 
    "Marcelo Dos Santos": "2655", 
    "Matheus": "2664", 
    "Michael Douglas": "2638", 
    "Pablo Mol": "2643", 
    "Ranyer Segal": "2669", 
    "Vanessa Ligiane": "2607", 
    "Victoria Lisboa": "2660", 
    "Isac Candido": "----",
    "Sarah Leal": "----", 
    "Morôni": "----", 
    "Marina Silva": "----", 
    "Marina Torres": "----",
    "Luiz Henrique": "----", 
    "Igor Dayrell": "----"
}

# ============================================
# FUNÇÃO PRINCIPAL DO DASHBOARD (INTEGRAL)
# ============================================
def render_dashboard(team_id, team_name, consultores_list, webhook_key, app_url, other_team_id, other_team_name, usuario_logado):
    
    # INJEÇÃO CSS PROFISSIONAL (BADGES, BOTÕES, TOASTS)
    st.markdown("""
    <style>
        .status-badge {
            display: inline-block; padding: 2px 8px; border-radius: 12px;
            font-size: 0.8rem; font-weight: 600; color: #333; margin-left: 5px;
        }
        .badge-green { background-color: #C8E6C9; color: #1B5E20; border: 1px solid #A5D6A7; }
        .badge-red { background-color: #FFCDD2; color: #B71C1C; border: 1px solid #EF9A9A; }
        .badge-blue { background-color: #BBDEFB; color: #0D47A1; border: 1px solid #90CAF9; }
        .badge-orange { background-color: #FFECB3; color: #E65100; border: 1px solid #FFE082; }
        
        div.stButton > button {
            width: 100%; height: auto; min-height: 45px; line-height: 1.2;
        }
        div[data-testid="stToast"] {
            padding: 10px; border-radius: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Configurações Dinâmicas
    DB_APP_ID = team_id
    LOGMEIN_DB_ID = 1
    CONSULTORES = sorted(consultores_list)
    APP_URL_CLOUD = app_url

    # Listas de Opções
    REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
    REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
    REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
    REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]
    OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]

    # Imagens
    GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
    GIF_LOGMEIN_TARGET = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZjFvczlzd3ExMWc2cWJrZ3EwNmplM285OGFqOHE1MXlzdnd4cndibiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/mcsPU3SkKrYDdW3aAU/giphy.gif"
    BASTAO_EMOJI = "🎭" 
    PUG2026_FILENAME = "Carnaval.gif" 

    CHAT_WEBHOOK_BASTAO = get_secret("chat", webhook_key)
    WEBHOOK_STATE_DUMP = get_secret("webhook", "test_state")

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

    # TTL 10 minutos para gráfico (Performance)
    @st.cache_data(ttl=600, show_spinner=False)
    def carregar_dados_grafico():
        sb = get_supabase()
        if not sb: return None, None
        try:
            res = sb.table("atendimentos_resumo").select("data").eq("id", DB_APP_ID).execute()
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
    # 3. REPOSITÓRIO
    # ============================================

    def clean_data_for_db(obj):
        if isinstance(obj, dict): return {k: clean_data_for_db(v) for k, v in obj.items()}
        elif isinstance(obj, list): return [clean_data_for_db(i) for i in obj]
        elif isinstance(obj, (datetime, date)): return obj.isoformat()
        elif isinstance(obj, timedelta): return obj.total_seconds()
        else: return obj

    # Cache curto (3s) para atualização quase real-time
    @st.cache_data(ttl=3, show_spinner=False)
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

    def save_state_to_db(state_data):
        sb = get_supabase()
        if not sb: return
        try:
            sanitized_data = clean_data_for_db(state_data)
            sb.table("app_state").upsert({"id": DB_APP_ID, "data": sanitized_data}).execute()
            # Limpa cache imediatamente
            load_state_from_db.clear()
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
        try: return st_javascript(js_code, key=f"browser_id_tag_{team_id}")
        except: return "unknown_device"

    def get_remote_ip():
        try:
            ctx = st.runtime.scriptrunner.get_script_run_ctx()
            if ctx and ctx.session_id:
                req = st.runtime.get_instance().get_client(ctx.session_id).request
                if 'X-Forwarded-For' in req.headers: return req.headers['X-Forwarded-For'].split(',')[0]
                return req.remote_ip
        except: return "Unknown"
        return "Unknown"

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
    # 5. MANIPULAÇÃO DE ESTADO
    # ============================================

    def reset_day_state():
        st.session_state.bastao_queue = []
        # MODIFICADO: Status vazio ao resetar
        st.session_state.status_texto = {n: '' for n in CONSULTORES}
        st.session_state.daily_logs = []
        st.session_state.report_last_run_date = get_brazil_time()

    def ensure_daily_reset():
        now_br = get_brazil_time()
        # Garante que a variável existe antes de usar (Correção AttributeError)
        if 'report_last_run_date' not in st.session_state:
             st.session_state.report_last_run_date = now_br
             
        last_run = st.session_state.report_last_run_date
        if isinstance(last_run, str):
            try: last_run_dt = datetime.fromisoformat(last_run).date()
            except: last_run_dt = date.min
        elif isinstance(last_run, datetime):
            last_run_dt = last_run.date()
        else:
            last_run_dt = date.min

        if now_br.date() > last_run_dt:
            if st.session_state.daily_logs: 
                full_state = {'date': now_br.isoformat(), 'logs': st.session_state.daily_logs}
                send_state_dump_webhook(full_state)
            reset_day_state()
            save_state()

    def auto_manage_time():
        ensure_daily_reset()

    # ============================================
    # 6. DOCUMENTOS (WORD) - TEXTOS FIÉIS AOS ANEXOS
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

            sb.table("certidoes_registro").insert(dados).execute(); return True
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
            
            # CABEÇALHO
            head_p = doc.add_paragraph(); head_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            runner = head_p.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
            runner.bold = True
            head_p.add_run("Rua Ouro Preto, N° 1564 - Bairro Santo Agostinho - CEP 30170-041 - Belo Horizonte - MG\nwww.tjmg.jus.br - Andar: 3º e 4º PV")
            doc.add_paragraph("\n")
            
            # NUMERAÇÃO E ASSUNTO (MODELOS ANEXOS)
            if tipo == 'Geral': 
                p_num = doc.add_paragraph(f"Parecer GEJUD/DIRTEC/TJMG nº ____/2026.")
            else: 
                p_num = doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2026.")
            p_num.runs[0].bold = True
            
            p_assunto = doc.add_paragraph(f"Assunto: Notifica erro no “JPe – 2ª Instância” ao peticionar.")
            
            # DATA
            doc.add_paragraph(f"Belo Horizonte, {data}")
            
            doc.add_paragraph(f"Exmo(a). Senhor(a) Relator(a),")
            
            # CORPO (TEXTO ESPECÍFICO DE CADA ANEXO)
            if tipo == 'Geral':
                # Baseado em "Declaração - Indisponibilidade.docx"
                corpo = doc.add_paragraph(); corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                txt = (f"Para fins de cumprimento dos artigos 13 e 14 da Resolução nº 780/2014 do Tribunal de Justiça do Estado de Minas Gerais, "
                    f"informamos que em {data} houve indisponibilidade do portal JPe, superior a uma hora, {hora if hora else '____'}, que impossibilitou o peticionamento eletrônico de recursos em processos que já tramitavam no sistema.")
                corpo.add_run(txt)
                
            elif tipo in ['Eletrônica', 'Eletrônico']:
                # Baseado em "Declaração eletrônica.docx"
                corpo = doc.add_paragraph(); corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                corpo.add_run(f"Informamos que de {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}")
                if nome_parte: corpo.add_run(f", Parte/Advogado: {nome_parte}")
                corpo.add_run(".\n\n")
                corpo.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
                corpo.add_run("Esperamos ter prestado as informações solicitadas e colocamo-nos à disposição para outras que se fizerem necessárias.")

            elif tipo in ['Física', 'Físico']:
                # Baseado em "Declaração física (1).docx"
                corpo1 = doc.add_paragraph(); corpo1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                corpo1.add_run(f"Informamos que no dia {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}")
                if nome_parte: corpo1.add_run(f", Parte/Advogado: {nome_parte}")
                corpo1.add_run(".")
                
                corpo2 = doc.add_paragraph(); corpo2.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                corpo2.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC.")
                
                corpo3 = doc.add_paragraph(); corpo3.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                corpo3.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.")

            doc.add_paragraph("\nColocamo-nos à disposição para outras informações.")
            doc.add_paragraph("\nRespeitosamente,")
            
            # ASSINATURA PADRÃO
            sign = doc.add_paragraph("\n___________________________________\nWaner Andrade Silva\n0-009020-9\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD")
            sign.runs[0].bold = True 
            
            buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
            return buffer
        except: return None

    # --- WEBHOOKS ---
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
        except: return False

    def handle_erro_novidade_submission(consultor, titulo, objetivo, relato, resultado):
        data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
        msg = f"🐛 **Novo Relato de Erro/Novidade**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n📌 **Título:** {titulo}\n\n🎯 **Objetivo:**\n{objetivo}\n\n🧪 **Relato:**\n{relato}\n\n🏁 **Resultado:**\n{resultado}"
        try: send_to_chat("erro", msg); return True
        except: return False

    def handle_sugestao_submission(consultor, texto):
        data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
        msg = f"💡 **Nova Sugestão**\n📅 **Data:** {data_envio}\n👤 **Autor:** {consultor}\n\n📝 **Sugestão:**\n{texto}"
        try: send_to_chat("extras", msg); return True
        except: return False
    
    def handle_chamado_submission():
         texto = st.session_state.get('chamado_textarea')
         consultor = st.session_state.get('consultor_selectbox')
         return send_chamado_to_chat(consultor, texto)

    # ============================================
    # 7. FUNÇÕES DE ESTADO (CORE LOGIC - PRESERVADA)
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
                'bastao_start_time': st.session_state.bastao_start_time, 'report_last_run_date': last_run, 
                'daily_logs': st.session_state.daily_logs, 'previous_states': st.session_state.get('previous_states', {})
            }
            save_state_to_db(state_to_save)
        except Exception as e: print(f"Erro save: {e}")

    def sync_state_from_db():
        try:
            db_data = load_state_from_db(DB_APP_ID)
            if not db_data: return
            for k in ['status_texto', 'bastao_queue', 'skip_flags', 'bastao_counts', 'daily_logs', 'previous_states']:
                if k in db_data: 
                    # Lógica de paginação para logs grandes (proteção)
                    if k == 'daily_logs' and isinstance(db_data[k], list) and len(db_data[k]) > 150:
                        st.session_state[k] = db_data[k][-150:] 
                    else: st.session_state[k] = db_data[k]
            
            # CORREÇÃO CRÍTICA DE DATA AQUI
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

    def log_status_change(consultor, old, new):
        now = get_brazil_time()
        start = st.session_state.current_status_starts.get(consultor, now)
        if isinstance(start, str): start = datetime.fromisoformat(start)
        duration = now - start
        st.session_state.daily_logs.append({'timestamp': now.isoformat(), 'consultor': consultor, 'old': old, 'new': new, 'duration': duration.total_seconds()})
        st.session_state.current_status_starts[consultor] = now

    def find_next_holder_index(current_index, queue, skips):
        if not queue: return -1
        n = len(queue); start_index = (current_index + 1) % n
        for i in range(n):
            idx = (start_index + i) % n
            if not skips.get(queue[idx], False): return idx
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

    # --- LÓGICA ATUALIZADA (REGRA DE STATUS x FILA) ---
    def update_status(novo_status, marcar_indisponivel=False, manter_fila=False):
        c = st.session_state.get('consultor_selectbox')
        if not c or c == 'Selecione um nome': return
        
        ensure_daily_reset()
        current = st.session_state.status_texto.get(c, '')
        
        # 1. Se Marcar Indisponível (Saída, etc): SAI DA FILA E SAI DO STATUS
        if marcar_indisponivel:
            st.session_state.skip_flags[c] = True
            if c in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(c)
        
        # 2. Se NÃO manter fila (Almoço, Reunião): Remove da fila -> PERDE O BASTÃO
        if not manter_fila and not marcar_indisponivel:
             if c in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(c)

        # 3. Se Manter Fila (Atividade, Projeto): Adiciona ou mantém
        if manter_fila:
            if c not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(c)
            st.session_state.skip_flags[c] = False

        # 4. Construção do Texto Final
        final = novo_status
        current_holder = next((k for k,v in st.session_state.status_texto.items() if 'Bastão' in v), None)
        
        if c == current_holder and c in st.session_state.bastao_queue:
             if final: final = f"Bastão | {final}"
             else: final = "Bastão"

        log_status_change(c, current, final)
        st.session_state.status_texto[c] = final
        check_baton()
        save_state()
        st.toast(f"Status atualizado: {final}", icon="✅")

    # --- LÓGICA ATUALIZADA: SAIR (TOGGLE INTELIGENTE) ---
    def toggle_queue_logic(consultor):
        ensure_daily_reset()
        current_status = st.session_state.status_texto.get(consultor, '')
        
        # CASO 1: Tem status (Ocupado) -> Limpa e Volta pra Fila
        if current_status and "Bastão" not in current_status:
             st.session_state.status_texto[consultor] = ""
             if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
             st.toast("Voltou para a fila (Livre)", icon="🔙")
        
        # CASO 2: Está na fila (Livre) -> Sai da Fila (Indisponível)
        elif consultor in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(consultor)
            st.session_state.status_texto[consultor] = "" 
            st.toast("Saiu da fila (Indisponível)", icon="❌")
        
        # CASO 3: Vazio e fora -> Entra na fila
        else:
            st.session_state.bastao_queue.append(consultor)
            st.session_state.skip_flags[consultor] = False
            st.toast("Entrou na fila", icon="📥")
        
        check_baton()
        save_state()

    def toggle_emoji(emoji_char):
        c = st.session_state.consultor_selectbox
        if not c or c == 'Selecione um nome': return
        current = st.session_state.status_texto.get(c, '')
        if emoji_char in current: new_s = current.replace(emoji_char, '').strip()
        else: new_s = f"{current} {emoji_char}".strip()
        st.session_state.status_texto[c] = new_s
        save_state()
        st.toast(f"Status alterado: {emoji_char}", icon="🔄")

    def rotate_logic():
        c = st.session_state.consultor_selectbox
        holder = next((k for k,v in st.session_state.status_texto.items() if 'Bastão' in v), None)
        if c != holder: st.warning("Só quem tem o bastão pode passar!"); return
        
        queue = st.session_state.bastao_queue
        if not queue: return
        
        try: idx = queue.index(c)
        except: idx = -1
        
        next_idx = (idx + 1) % len(queue)
        start = next_idx
        while st.session_state.skip_flags.get(queue[next_idx], False):
            next_idx = (next_idx + 1) % len(queue)
            if next_idx == start: break 
            
        next_c = queue[next_idx]
        
        st.session_state.status_texto[c] = st.session_state.status_texto[c].replace("Bastão", "").strip(" |")
        st.session_state.status_texto[next_c] = f"Bastão | {st.session_state.status_texto.get(next_c,'')}".strip(" |")
        st.session_state.bastao_start_time = get_brazil_time()
        
        send_to_chat("bastao", f"🎉 **Bastão Girado:** {next_c}", webhook_url=CHAT_WEBHOOK_BASTAO)
        save_state()
        st.toast(f"Bastão passado para {next_c}", icon="👉")

    def toggle_skip():
        selected = st.session_state.consultor_selectbox
        if not selected or selected == 'Selecione um nome': return
        if selected not in st.session_state.bastao_queue: return
        st.session_state.skip_flags[selected] = not st.session_state.skip_flags.get(selected, False)
        save_state()

    def toggle_presence_btn():
        toggle_queue_logic(st.session_state.consultor_selectbox)

    def enter_from_indisponivel(c):
        if c not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(c)
        st.session_state.status_texto[c] = ''; save_state()

    def toggle_view(v):
        if st.session_state.active_view == v: st.session_state.active_view = None
        else: st.session_state.active_view = v

    # --- INICIALIZAÇÃO CORRIGIDA (CORREÇÃO ERRO ATTRIBUTE) ---
    def init_session_state():
        dev = get_browser_id()
        if dev: st.session_state['device_id_val'] = dev
        
        if 'db_loaded' not in st.session_state:
            db = load_state_from_db(DB_APP_ID)
            # Converte data se vier string
            if 'report_last_run_date' in db and isinstance(db['report_last_run_date'], str):
                try: db['report_last_run_date'] = datetime.fromisoformat(db['report_last_run_date'])
                except: db['report_last_run_date'] = datetime.min
            st.session_state.update(db); st.session_state['db_loaded'] = True
        
        # DEFINIÇÃO DE DEFAULTS
        defaults = {
            'bastao_start_time': None, 'report_last_run_date': get_brazil_time(), # INICIALIZA DATA AQUI
            'active_view': None,
            'consultor_selectbox': usuario_logado if usuario_logado else "Selecione um nome", 
            'status_texto': {n: '' for n in CONSULTORES},
            'bastao_queue': [], 'skip_flags': {}, 'current_status_starts': {n: get_brazil_time() for n in CONSULTORES},
            'bastao_counts': {n: 0 for n in CONSULTORES}, 'priority_return_queue': [], 'daily_logs': [],
            'word_buffer': None, 'aviso_duplicidade': False, 'previous_states': {}, 'view_logmein_ui': False,
            'last_cleanup': time.time(), 'last_hard_cleanup': time.time(),
            'init': True
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
        
        if st.button("🚪 Sair (Voltar)", use_container_width=True):
            st.session_state["time_selecionado"] = None; st.session_state["consultor_logado"] = None
            st.rerun()
            
        st.divider()
        
        # LOGMEIN EM EXPANDER
        with st.expander("🔑 LogMeIn", expanded=False):
            l_user, l_in_use = get_logmein_status()
            if l_in_use:
                st.error(f"Em uso: {l_user}")
                if st.button("Liberar", key="btn_lib_log_side"): set_logmein_status(None, False); st.rerun()
            else:
                st.success("Livre")
                meu_nome = st.session_state.get('consultor_selectbox')
                if meu_nome and meu_nome != "Selecione um nome":
                    if st.button("Assumir", key="btn_ass_log_side"): set_logmein_status(meu_nome, True); st.rerun()
                else: st.info("Selecione seu nome.")

        # FILA VIZINHA COM RAMAIS
        with st.expander(f"👀 Fila {other_team_name}", expanded=False):
            other_data = load_state_from_db(other_team_id)
            other_queue = other_data.get('bastao_queue', [])
            other_status = other_data.get('status_texto', {})
            
            if not other_queue: st.info("Fila vazia.")
            else:
                other_holder = next((c for c, s in other_status.items() if 'Bastão' in s), None)
                try: idx = other_queue.index(other_holder)
                except: idx = 0
                ordered = other_queue[idx:] + other_queue[:idx] if other_holder else other_queue
                
                for i, nome in enumerate(ordered):
                    extra = "🎭" if nome == other_holder else f"{i}º"
                    ramal = RAMAIS_MAP.get(nome, "----")
                    icons = ""
                    if "📞" in other_status.get(nome, ""): icons += "📞"
                    if "☕" in other_status.get(nome, ""): icons += "☕"
                    st.markdown(f"**{extra} {nome}** (Ramal {ramal}) {icons}")

    # --- HEADER ---
    sync_state_from_db()
    
    st.markdown(f"<div style='background:#f0f2f6; padding:10px; border-radius:5px; margin-bottom:10px;'>👤 <b>Logado como:</b> {st.session_state.consultor_selectbox}</div>", unsafe_allow_html=True)

    col_l, col_r = st.columns([2, 1])
    with col_l:
        holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        st.title(f"{BASTAO_EMOJI} Painel {team_name}")
        if holder:
            start_t = st.session_state.bastao_start_time
            if isinstance(start_t, str): 
                try: start_t = datetime.fromisoformat(start_t)
                except: start_t = get_brazil_time()
            elif not start_t: start_t = get_brazil_time()
            dur = get_brazil_time() - start_t
            st.success(f"🎭 **BASTÃO COM: {holder}** ({format_time_duration(dur)})")
        else: st.info("Ninguém com o bastão.")
    
    with col_r:
        st.subheader("Fila")
        vis_queue = get_ordered_visual_queue(st.session_state.bastao_queue, st.session_state.status_texto)
        if vis_queue:
            for q in vis_queue:
                s = st.session_state.status_texto.get(q, "")
                badges = ""
                if "Sessão" in s: badges += " <span class='status-badge badge-green'>Sessão</span>"
                if "Almoço" in s: badges += " <span class='status-badge badge-red'>Almoço</span>"
                if "Projeto" in s: badges += " <span class='status-badge badge-blue'>Proj</span>"
                if "Atividade" in s: badges += " <span class='status-badge badge-orange'>Ativ</span>"
                if "📞" in s: badges += " 📞"
                if "☕" in s: badges += " ☕"
                st.markdown(f"- {q} {badges}", unsafe_allow_html=True)
        else: st.caption("Fila vazia")

    # AÇÕES
    st.markdown("---")
    st.selectbox("Mudar Consultor (Se necessário):", ["Selecione um nome"] + CONSULTORES, key="consultor_selectbox", label_visibility="collapsed")
    
    c1, c2, c3 = st.columns(3)
    if c1.button("🎭 Entrar/Sair (Toggle)", use_container_width=True): 
        toggle_queue_logic(st.session_state.consultor_selectbox); st.rerun()
    if c2.button("🎯 Passar Bastão", use_container_width=True): 
        rotate_logic(); st.rerun()
    if c3.button("⏭️ Pular Vez", use_container_width=True): 
        c = st.session_state.consultor_selectbox
        st.session_state.skip_flags[c] = not st.session_state.skip_flags.get(c, False)
        save_state(); st.toast("Pulo alternado", icon="⏭️"); st.rerun()

    st.markdown("### Status Rápido")
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    # Almoço/Reunião -> manter_fila=False (SAI DO BASTÃO)
    if r1c1.button("🍽️ Almoço", use_container_width=True): update_status("Almoço", manter_fila=False); st.rerun()
    if r1c2.button("📅 Reunião", use_container_width=True): update_status("Reunião", manter_fila=False); st.rerun()
    if r1c3.button("🚶 Saída", use_container_width=True): update_status("Saída rápida", marcar_indisponivel=True); st.rerun()
    if r1c4.button("❌ Indisp.", use_container_width=True): update_status("Indisponível", marcar_indisponivel=True); st.rerun()

    st.markdown("### Menus de Ação")
    m1, m2, m3, m4 = st.columns(4)
    if m1.button("📋 Atividades", use_container_width=True): st.session_state.active_view = 'ativ'; st.rerun()
    if m2.button("🏗️ Projeto", use_container_width=True): st.session_state.active_view = 'proj'; st.rerun()
    if m3.button("🎓 Treino", use_container_width=True): st.session_state.active_view = 'treino'; st.rerun()
    if m4.button("🎙️ Sessão", use_container_width=True): st.session_state.active_view = 'sessao'; st.rerun()

    t1, t2 = st.columns(2)
    if t1.button("📞 Telefone (Toggle)", use_container_width=True): toggle_emoji("📞"); st.rerun()
    if t2.button("☕ Café (Toggle)", use_container_width=True): toggle_emoji("☕"); st.rerun()

    # RENDERIZAÇÃO DOS MENUS ABERTOS
    if st.session_state.active_view:
        st.divider()
        with st.container(border=True):
            if st.session_state.active_view == 'ativ':
                st.subheader("Nova Atividade")
                tipo = st.multiselect("Tipo", OPCOES_ATIVIDADES_STATUS)
                detalhe = st.text_input("Detalhe")
                manter = st.checkbox("Manter na fila do bastão?", value=True)
                if st.button("Confirmar", type="primary"):
                    update_status(f"Atividade: {','.join(tipo)} - {detalhe}", manter_fila=manter)
                    st.session_state.active_view = None; st.rerun()
            elif st.session_state.active_view == 'proj':
                st.subheader("Projeto")
                nome = st.text_input("Nome do Projeto")
                manter = st.checkbox("Manter na fila do bastão?", value=True)
                if st.button("Confirmar", type="primary"):
                    update_status(f"Projeto: {nome}", manter_fila=manter)
                    st.session_state.active_view = None; st.rerun()
            elif st.session_state.active_view == 'treino':
                st.subheader("Treinamento"); tema = st.text_input("Tema")
                if st.button("Inciar Treino"): update_status(f"Treinamento: {tema}", manter_fila=False); st.session_state.active_view = None; st.rerun()
            elif st.session_state.active_view == 'sessao':
                st.subheader("Sessão"); sessao = st.text_input("Câmara")
                if st.button("Confirmar"): update_status(f"Sessão: {sessao}", manter_fila=False); st.session_state.active_view = None; st.rerun()
            if st.button("Cancelar"): st.session_state.active_view = None; st.rerun()

    st.markdown("---")
    f1, f2, f3 = st.columns(3)
    if f1.button("🖨️ Certidão"): st.session_state.active_view = 'certidao'; st.rerun()

    if st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.header("🖨️ Registro de Certidão (2026)")
            c_data = st.date_input("Data do Evento:", value=get_brazil_time().date(), format="DD/MM/YYYY")
            tipo_cert = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"])
            c_motivo = st.text_area("Motivo/Detalhes:", height=100)
            c_hora = ""; c_proc = ""; c_chamado = ""; c_nome_parte = ""
            if tipo_cert == "Geral": 
                c_hora = st.text_input("Horário/Período:")
                if c_hora: c_motivo = f"{c_motivo} - Período: {c_hora}"
            else: 
                c1, c2 = st.columns(2); c_proc = c1.text_input("Processo:"); c_chamado = c2.text_input("Chamado:"); c_nome_parte = st.text_input("Parte/Advogado:")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📄 Gerar Word"): st.session_state.word_buffer = gerar_docx_certidao_internal(tipo_cert, c_proc, c_data.strftime("%d/%m/%Y"), st.session_state.consultor_selectbox, c_motivo, c_chamado, c_hora, c_nome_parte)
                if st.session_state.word_buffer: st.download_button("⬇️ Baixar", st.session_state.word_buffer, file_name="certidao.docx")
            with c2:
                if st.button("💾 Salvar BD", type="primary"):
                    payload = {"tipo": tipo_cert, "data": c_data.isoformat(), "consultor": st.session_state.consultor_selectbox, "incidente": c_chamado, "processo": c_proc, "motivo": c_motivo}
                    if salvar_certidao_db(payload): st.toast("Certidão Salva!", icon="✅"); st.session_state.active_view = None; st.rerun()
            if st.button("❌ Fechar"): st.session_state.active_view = None; st.rerun()

    st.markdown("---")
    df_chart, gerado_em = carregar_dados_grafico()
    if df_chart is not None:
        try: st.altair_chart(alt.Chart(df_chart.melt(id_vars=['relatorio'], value_vars=['Eproc', 'Legados'], var_name='Sistema', value_name='Qtd')).mark_bar().encode(x='relatorio', y='Qtd', color='Sistema', column='Sistema'), use_container_width=True)
        except: pass
