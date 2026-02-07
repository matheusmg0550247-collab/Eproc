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

from utils import (get_brazil_time, get_secret, send_to_chat)

# =============================================================================
# MAPEAMENTO DE RAMAIS (CORRIGIDO COM NOMES COMPLETOS DO SISTEMA)
# =============================================================================
RAMAIS_MAP = {
    # Equipe Eproc (Cesupe)
    "Alex Paulo": "2510", 
    "Barbara Mara": "2517", 
    "Bruno Glaicon": "2644", 
    "Claudio": "2667", # Verifique se o nome completo é Claudio ou Claudia Luiza
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

# =============================================================================
# FUNÇÃO PRINCIPAL DO DASHBOARD (MOTOR UNIFICADO)
# =============================================================================
def render_dashboard(team_id, team_name, consultores_list, webhook_key, app_url, other_team_id, other_team_name, usuario_logado):
    
    # 1. CSS PROFISSIONAL INJETADO (BADGES E COMPACTAÇÃO)
    st.markdown("""
    <style>
        /* Badges de Status */
        .status-badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 600;
            color: #333;
            margin-left: 5px;
        }
        .badge-green { background-color: #C8E6C9; color: #1B5E20; } /* Sessão */
        .badge-red { background-color: #FFCDD2; color: #B71C1C; } /* Almoço/Saída */
        .badge-blue { background-color: #BBDEFB; color: #0D47A1; } /* Projeto */
        .badge-orange { background-color: #FFECB3; color: #E65100; } /* Atividade */
        
        /* Botões mais responsivos */
        div.stButton > button {
            width: 100%;
            height: auto;
            min-height: 45px;
        }
        
        /* Ajuste de toast */
        div[data-testid="stToast"] {
            padding: 10px;
            border-radius: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

    # 2. CONFIGURAÇÕES
    DB_APP_ID = team_id
    LOGMEIN_DB_ID = 1
    CONSULTORES = sorted(consultores_list)
    
    REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
    REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
    REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
    REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]
    OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]

    GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
    GIF_LOGMEIN_TARGET = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZjFvczlzd3ExMWc2cWJrZ3EwNmplM285OGFqOHE1MXlzdnd4cndibiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/mcsPU3SkKrYDdW3aAU/giphy.gif"
    BASTAO_EMOJI = "🎭" 
    PUG2026_FILENAME = "Carnaval.gif" 

    CHAT_WEBHOOK_BASTAO = get_secret("chat", webhook_key)
    WEBHOOK_STATE_DUMP = get_secret("webhook", "test_state")

    # ============================================
    # 3. SUPABASE E CACHE
    # ============================================
    @st.cache_resource(ttl=3600)
    def get_supabase():
        try: return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
        except: st.cache_resource.clear(); return None

    # TTL Configurado para 10 minutos no gráfico para não pesar
    @st.cache_data(ttl=600) 
    def carregar_dados_grafico():
        sb = get_supabase()
        if not sb: return None, None
        try:
            res = sb.table("atendimentos_resumo").select("data").eq("id", DB_APP_ID).execute()
            if res.data:
                json_data = res.data[0]['data']
                if 'totais_por_relatorio' in json_data:
                    return pd.DataFrame(json_data['totais_por_relatorio']), json_data.get('gerado_em', '-')
        except: pass
        return None, None

    @st.cache_data
    def get_img_as_base64_cached(file_path):
        try:
            with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
        except: return None

    # ============================================
    # 4. FUNÇÕES DE BANCO (CRUD)
    # ============================================
    def clean_data_for_db(obj):
        if isinstance(obj, dict): return {k: clean_data_for_db(v) for k, v in obj.items()}
        elif isinstance(obj, list): return [clean_data_for_db(i) for i in obj]
        elif isinstance(obj, (datetime, date)): return obj.isoformat()
        elif isinstance(obj, timedelta): return obj.total_seconds()
        else: return obj

    # CACHE INTELIGENTE: TTL DE 3 SEGUNDOS (Atualização rápida para 30 pessoas)
    @st.cache_data(ttl=3) 
    def load_state_from_db_cached(target_id):
        sb = get_supabase()
        if not sb: return {}
        try:
            response = sb.table("app_state").select("data").eq("id", target_id).execute()
            if response.data: return response.data[0].get("data", {})
            return {}
        except: return {}

    def save_state_to_db(state_data):
        sb = get_supabase()
        if not sb: return
        try:
            sanitized = clean_data_for_db(state_data)
            sb.table("app_state").upsert({"id": DB_APP_ID, "data": sanitized}).execute()
            # Limpa cache imediatamente após salvar para refletir mudança
            load_state_from_db_cached.clear()
        except Exception as e: st.error(f"Erro Salvar DB: {e}")

    # LogMeIn
    def get_logmein_status():
        sb = get_supabase()
        if not sb: return None, False
        try:
            res = sb.table("controle_logmein").select("*").eq("id", LOGMEIN_DB_ID).execute()
            if res.data: return res.data[0].get('consultor_atual'), res.data[0].get('em_uso', False)
        except: pass
        return None, False

    def set_logmein_status(consultor, em_uso):
        sb = get_supabase()
        if not sb: return
        try:
            dados = {"consultor_atual": consultor if em_uso else None, "em_uso": em_uso, "data_inicio": datetime.now().isoformat()}
            sb.table("controle_logmein").update(dados).eq("id", LOGMEIN_DB_ID).execute()
        except: pass

    # ============================================
    # 5. UTILITÁRIOS
    # ============================================
    def get_browser_id():
        if st_javascript is None: return "no_js"
        js = """(function() {
            let id = localStorage.getItem("device_id");
            if (!id) { id = "id_" + Math.random().toString(36).substr(2, 9); localStorage.setItem("device_id", id); }
            return id;
        })();"""
        try: return st_javascript(js, key=f"bid_{team_id}")
        except: return "unknown"

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
        if time.time() - st.session_state.get('last_cleanup', 0) > 300:
            gc.collect(); st.session_state.last_cleanup = time.time()
        if time.time() - st.session_state.get('last_hard_cleanup', 0) > 14400:
            st.cache_data.clear(); st.session_state.last_hard_cleanup = time.time()

    def get_ordered_visual_queue(queue, status_dict):
        if not queue: return []
        holder = next((c for c, s in status_dict.items() if 'Bastão' in (s or '')), None)
        if not holder or holder not in queue: return list(queue)
        try: idx = queue.index(holder); return queue[idx:] + queue[:idx]
        except: return list(queue)

    def format_time_duration(duration):
        if not isinstance(duration, timedelta): return '--:--:--'
        s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
        return f'{h:02}:{m:02}:{s:02}'

    # ============================================
    # 6. DOCUMENTOS (WORD) - MODELOS FIÉIS AO ANEXO
    # ============================================
    def verificar_duplicidade_certidao(tipo, processo=None, data=None):
        sb = get_supabase()
        if not sb or not processo: return False
        try: return len(sb.table("certidoes_registro").select("*").eq("processo", str(processo).strip()).execute().data) > 0
        except: return False

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
        except: return False

    # GERADOR DE WORD COM TEXTOS EXATOS DOS ANEXOS
    def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado="", hora="", nome_parte=""):
        try:
            doc = Document()
            section = doc.sections[0]
            section.top_margin = Cm(2.5); section.bottom_margin = Cm(2.0)
            section.left_margin = Cm(3.0); section.right_margin = Cm(3.0)
            style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
            
            # CABEÇALHO PADRÃO
            head_p = doc.add_paragraph(); head_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            runner = head_p.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
            runner.bold = True
            head_p.add_run("Rua Ouro Preto, N° 1564 - Bairro Santo Agostinho - CEP 30170-041 - Belo Horizonte - MG\nwww.tjmg.jus.br - Andar: 3º e 4º PV")
            doc.add_paragraph("\n")
            
            # NUMERAÇÃO E ASSUNTO (PARECER TÉCNICO)
            if tipo == 'Geral': 
                p_num = doc.add_paragraph(f"Parecer GEJUD/DIRTEC/TJMG nº ____/2026.")
            else: 
                p_num = doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2026.")
            p_num.runs[0].bold = True
            
            p_assunto = doc.add_paragraph(f"Assunto: Notifica erro no “JPe – 2ª Instância” ao peticionar.")
            
            # DATA
            doc.add_paragraph(f"Belo Horizonte, {data}")
            
            doc.add_paragraph(f"Exmo(a). Senhor(a) Relator(a),")
            
            # CORPO DO TEXTO - BASEADO NOS ARQUIVOS ENVIADOS
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
            sanitized = clean_data_for_db(state_data)
            headers = {'Content-Type': 'application/json'}
            requests.post(WEBHOOK_STATE_DUMP, data=json.dumps(sanitized), headers=headers, timeout=5)
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
    # 7. FUNÇÕES DE ESTADO (CORE LOGIC)
    # ============================================
    def save_state():
        try:
            last_run = st.session_state.report_last_run_date
            visual_queue = get_ordered_visual_queue(st.session_state.bastao_queue, st.session_state.status_texto)
            state_to_save = {
                'status_texto': st.session_state.status_texto, 'bastao_queue': st.session_state.bastao_queue,
                'visual_queue': visual_queue, 'skip_flags': st.session_state.skip_flags, 
                'current_status_starts': st.session_state.current_status_starts,
                'bastao_counts': st.session_state.bastao_counts, 'priority_return_queue': st.session_state.priority_return_queue,
                'bastao_start_time': st.session_state.bastao_start_time, 'report_last_run_date': last_run, 
                'daily_logs': st.session_state.daily_logs, 'previous_states': st.session_state.get('previous_states', {})
            }
            save_state_to_db(state_to_save)
        except Exception as e: print(f"Erro save: {e}")

    def sync_state_from_db():
        try:
            db = load_state_from_db_cached(DB_APP_ID)
            if not db: return
            for k in ['status_texto', 'bastao_queue', 'skip_flags', 'bastao_counts', 'daily_logs', 'previous_states']:
                if k in db: st.session_state[k] = db[k]
            
            # CORREÇÃO DE DATA (CRÍTICO)
            if 'bastao_start_time' in db and db['bastao_start_time']:
                val = db['bastao_start_time']
                if isinstance(val, str):
                    try: st.session_state.bastao_start_time = datetime.fromisoformat(val)
                    except: st.session_state.bastao_start_time = get_brazil_time()
                else: st.session_state.bastao_start_time = val
            
            if 'current_status_starts' in db: st.session_state.current_status_starts = db['current_status_starts']
        except: pass

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

    def check_baton():
        queue = st.session_state.bastao_queue
        holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        
        if not holder or holder not in queue:
            next_c = next((c for c in queue if not st.session_state.skip_flags.get(c, False)), None)
            if next_c:
                st.session_state.status_texto[next_c] = "Bastão"
                st.session_state.bastao_start_time = get_brazil_time()
                send_to_chat("bastao", f"🎉 **Bastão automático:** {next_c}", webhook_url=CHAT_WEBHOOK_BASTAO)
                save_state()

    # --- LÓGICA ATUALIZADA (REGRA DE STATUS x FILA x BASTÃO) ---
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
        
        # Só recebe o prefixo "Bastão |" se a pessoa AINDA estiver na fila
        # Como Almoço/Reunião removem da fila (passo 2), eles nunca terão "Bastão | Almoço"
        current_holder = next((k for k,v in st.session_state.status_texto.items() if 'Bastão' in v), None)
        
        if c == current_holder and c in st.session_state.bastao_queue:
             if final: final = f"Bastão | {final}"
             else: final = "Bastão"

        log_status_change(c, current, final)
        st.session_state.status_texto[c] = final
        check_baton() # Se o bastão foi perdido no passo 2, isso passa pro próximo
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
        
        # CASO 3: Não está na fila e vazio -> Entra na fila
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

    # --- INICIALIZAÇÃO ---
    def reset_day_state():
        st.session_state.bastao_queue = []
        st.session_state.status_texto = {n: '' for n in CONSULTORES}
        st.session_state.daily_logs = []
        st.session_state.report_last_run_date = get_brazil_time()

    def ensure_daily_reset():
        now = get_brazil_time()
        last = st.session_state.report_last_run_date
        if isinstance(last, str): 
            try: last = datetime.fromisoformat(last)
            except: last = datetime.min
        if now.date() > last.date():
            if st.session_state.daily_logs: send_state_dump_webhook({'logs': st.session_state.daily_logs})
            reset_day_state(); save_state()

    if 'init' not in st.session_state:
        st.session_state.update({
            'bastao_queue': [], 'status_texto': {}, 'daily_logs': [], 'skip_flags': {},
            'consultor_selectbox': usuario_logado if usuario_logado else "Selecione um nome", 
            'active_view': None, 'current_status_starts': {}, 'init': True
        })
        sync_state_from_db()
        memory_sweeper()
        ensure_daily_reset()

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 🏢 {team_name}")
        st.caption("Central Unificada 2026")
        
        if st.button("🚪 Sair (Voltar)", use_container_width=True):
            st.session_state["time_selecionado"] = None; st.session_state["consultor_logado"] = None
            st.rerun()
            
        st.divider()
        
        # LOGMEIN (Expander)
        with st.expander("🔑 LogMeIn", expanded=False):
            l_user, l_in_use = get_logmein_status()
            if l_in_use:
                st.error(f"Em uso: {l_user}")
                if st.button("Liberar", key="btn_lib"): set_logmein_status(None, False); st.rerun()
            else:
                st.success("Livre")
                if st.button("Assumir", key="btn_ass"): set_logmein_status(st.session_state.consultor_selectbox, True); st.rerun()

        # FILA VIZINHA (Expander com Ramais)
        with st.expander(f"👀 Fila {other_team_name}", expanded=False):
            other_data = load_state_from_db_cached(other_team_id)
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

    # --- INTERFACE PRINCIPAL ---
    sync_state_from_db()
    
    # Header com Identidade Fixa
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
    
    # Dropdown backup
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
            
            # ATIVIDADES (Com opção de manter fila)
            if st.session_state.active_view == 'ativ':
                st.subheader("Nova Atividade")
                tipo = st.multiselect("Tipo", OPCOES_ATIVIDADES_STATUS)
                detalhe = st.text_input("Detalhe")
                manter = st.checkbox("Manter na fila do bastão?", value=True)
                if st.button("Confirmar", type="primary"):
                    update_status(f"Atividade: {','.join(tipo)} - {detalhe}", manter_fila=manter)
                    st.session_state.active_view = None; st.rerun()
            
            # PROJETO (Com opção de manter fila)
            elif st.session_state.active_view == 'proj':
                st.subheader("Projeto")
                nome = st.text_input("Nome do Projeto")
                manter = st.checkbox("Manter na fila do bastão?", value=True)
                if st.button("Confirmar", type="primary"):
                    update_status(f"Projeto: {nome}", manter_fila=manter)
                    st.session_state.active_view = None; st.rerun()

            elif st.session_state.active_view == 'treino':
                st.subheader("Treinamento")
                tema = st.text_input("Tema")
                if st.button("Inciar Treino"):
                    update_status(f"Treinamento: {tema}", manter_fila=False) 
                    st.session_state.active_view = None; st.rerun()
            
            elif st.session_state.active_view == 'sessao':
                st.subheader("Sessão")
                sessao = st.text_input("Câmara")
                if st.button("Confirmar"):
                    update_status(f"Sessão: {sessao}", manter_fila=False)
                    st.session_state.active_view = None; st.rerun()
            
            if st.button("Cancelar / Fechar"):
                st.session_state.active_view = None; st.rerun()

    # FERRAMENTAS EXTRAS
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
                c1, c2 = st.columns(2)
                c_proc = c1.text_input("Processo:")
                c_chamado = c2.text_input("Chamado:")
                c_nome_parte = st.text_input("Parte/Advogado:")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📄 Gerar Word"): 
                    st.session_state.word_buffer = gerar_docx_certidao_internal(tipo_cert, c_proc, c_data.strftime("%d/%m/%Y"), st.session_state.consultor_selectbox, c_motivo, c_chamado, c_hora, c_nome_parte)
                if st.session_state.word_buffer: 
                    st.download_button("⬇️ Baixar", st.session_state.word_buffer, file_name="certidao.docx")
            with c2:
                if st.button("💾 Salvar BD", type="primary"):
                    payload = {"tipo": tipo_cert, "data": c_data.isoformat(), "consultor": st.session_state.consultor_selectbox, "incidente": c_chamado, "processo": c_proc, "motivo": c_motivo}
                    if salvar_certidao_db(payload): 
                        st.toast("Certidão Salva!", icon="✅"); st.session_state.active_view = None; st.rerun()
            
            if st.button("❌ Fechar"): st.session_state.active_view = None; st.rerun()

    # GRÁFICO
    st.markdown("---")
    df_chart, gerado_em = carregar_dados_grafico()
    if df_chart is not None:
        try:
            st.altair_chart(alt.Chart(df_chart.melt(id_vars=['relatorio'], value_vars=['Eproc', 'Legados'], var_name='Sistema', value_name='Qtd')).mark_bar().encode(
                x='relatorio', y='Qtd', color='Sistema', column='Sistema'
            ), use_container_width=True)
        except: pass
