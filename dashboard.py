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

# Tenta importar javascript, se falhar, define como None
try:
    from streamlit_javascript import st_javascript
except ImportError:
    st_javascript = None

# Importa utilitários locais
from utils import (get_brazil_time, get_secret, send_to_chat)

# =============================================================================
# FUNÇÃO PRINCIPAL DO DASHBOARD (VERSÃO COMPLETA / ROBUSTA)
# =============================================================================
def render_dashboard(team_id, team_name, consultores_list, webhook_key, app_url, other_team_id, other_team_name):
    
    # -------------------------------------------------------------------------
    # 1. CONFIGURAÇÕES INICIAIS E CONSTANTES
    # -------------------------------------------------------------------------
    DB_APP_ID = team_id
    LOGMEIN_DB_ID = 1  # ID compartilhado para o LogMeIn
    CONSULTORES = sorted(consultores_list)
    APP_URL_CLOUD = app_url
    
    # Listas de Opções para os Formulários
    REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
    REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
    REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
    REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]
    OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]

    # URLs de Imagens e Gifs
    GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
    GIF_LOGMEIN_TARGET = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZjFvczlzd3ExMWc2cWJrZ3EwNmplM285OGFqOHE1MXlzdnd4cndibiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/mcsPU3SkKrYDdW3aAU/giphy.gif"
    BASTAO_EMOJI = "🎭" 
    PUG2026_FILENAME = "Carnaval.gif" 

    # Carregamento de Chaves Secretas
    CHAT_WEBHOOK_BASTAO = get_secret("chat", webhook_key)
    WEBHOOK_STATE_DUMP = get_secret("webhook", "test_state")

    # -------------------------------------------------------------------------
    # 2. CONEXÃO COM BANCO DE DADOS (SUPABASE) E CACHE
    # -------------------------------------------------------------------------
    @st.cache_resource(ttl=3600)
    def get_supabase():
        try: 
            return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
        except Exception as e: 
            st.error(f"Erro ao conectar Supabase: {e}")
            return None

    @st.cache_data(ttl=3600, show_spinner=False)
    def carregar_dados_grafico():
        """Carrega dados para o gráfico de resumo operacional"""
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
        """Carrega imagem local convertida para base64"""
        try:
            with open(file_path, "rb") as f: return base64.b64encode(f.read()).decode()
        except: return None

    # -------------------------------------------------------------------------
    # 3. FUNÇÕES DE CRUD E PERSISTÊNCIA DE ESTADO
    # -------------------------------------------------------------------------
    def clean_data_for_db(obj):
        """Prepara objetos Python para serem salvos em JSON no banco"""
        if isinstance(obj, dict): return {k: clean_data_for_db(v) for k, v in obj.items()}
        elif isinstance(obj, list): return [clean_data_for_db(i) for i in obj]
        elif isinstance(obj, (datetime, date)): return obj.isoformat()
        elif isinstance(obj, timedelta): return obj.total_seconds()
        else: return obj

    def load_state_from_db(target_id=None):
        """Carrega o estado do app. Permite carregar de OUTRA equipe se target_id for passado."""
        use_id = target_id if target_id else DB_APP_ID
        sb = get_supabase()
        if not sb: return {}
        try:
            response = sb.table("app_state").select("data").eq("id", use_id).execute()
            if response.data: return response.data[0].get("data", {})
            return {}
        except: return {}

    def save_state_to_db(state_data):
        """Salva o estado atual no banco"""
        sb = get_supabase()
        if not sb: return
        try:
            sanitized = clean_data_for_db(state_data)
            sb.table("app_state").upsert({"id": DB_APP_ID, "data": sanitized}).execute()
        except Exception as e: st.error(f"Erro Salvar: {e}")

    # --- FUNÇÕES ESPECÍFICAS DO LOGMEIN ---
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

    # -------------------------------------------------------------------------
    # 4. UTILITÁRIOS GERAIS
    # -------------------------------------------------------------------------
    def get_browser_id():
        if st_javascript is None: return "no_js"
        js = """(function() {
            let id = localStorage.getItem("device_id");
            if (!id) { id = "id_" + Math.random().toString(36).substr(2, 9); localStorage.setItem("device_id", id); }
            return id;
        })();"""
        try: return st_javascript(js, key=f"bid_{team_id}")
        except: return "unknown"

    def memory_sweeper():
        """Limpa memória periodicamente"""
        if time.time() - st.session_state.get('last_cleanup', 0) > 300:
            gc.collect(); st.session_state.last_cleanup = time.time()
        if time.time() - st.session_state.get('last_hard_cleanup', 0) > 14400:
            st.cache_data.clear(); st.session_state.last_hard_cleanup = time.time()

    def get_ordered_visual_queue(queue, status_dict):
        """Organiza a fila visualmente colocando quem tem o bastão no topo"""
        if not queue: return []
        holder = next((c for c, s in status_dict.items() if 'Bastão' in (s or '')), None)
        if not holder or holder not in queue: return list(queue)
        try: idx = queue.index(holder); return queue[idx:] + queue[:idx]
        except: return list(queue)

    def format_time_duration(duration):
        if not isinstance(duration, timedelta): return '--:--:--'
        s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
        return f'{h:02}:{m:02}:{s:02}'

    # -------------------------------------------------------------------------
    # 5. GERENCIAMENTO DE ESTADO E LÓGICA DE NEGÓCIO
    # -------------------------------------------------------------------------
    def reset_day_state():
        st.session_state.bastao_queue = []
        # CORREÇÃO: Reseta para Vazio, não Indisponível
        st.session_state.status_texto = {n: '' for n in CONSULTORES} 
        st.session_state.daily_logs = []
        st.session_state.report_last_run_date = get_brazil_time()

    def ensure_daily_reset():
        """Verifica se mudou o dia e reseta o estado"""
        now = get_brazil_time()
        last = st.session_state.report_last_run_date
        if isinstance(last, str): last = datetime.fromisoformat(last)
        if now.date() > last.date():
            if st.session_state.daily_logs: send_state_dump_webhook({'logs': st.session_state.daily_logs})
            reset_day_state(); save_state()

    def auto_manage_time():
        ensure_daily_reset()

    # -------------------------------------------------------------------------
    # 6. FUNÇÕES DE DOCUMENTOS (WORD) E NOTIFICAÇÕES (WEBHOOKS)
    # -------------------------------------------------------------------------
    def verificar_duplicidade_certidao(tipo, processo=None, data=None):
        sb = get_supabase()
        if not sb or not processo: return False
        try: return len(sb.table("certidoes_registro").select("*").eq("processo", str(processo).strip()).execute().data) > 0
        except: return False

    def salvar_certidao_db(dados):
        sb = get_supabase()
        if not sb: return False
        try:
            # Normalização de chaves
            if 'hora_periodo' in dados: del dados['hora_periodo']
            if 'n_processo' in dados: dados['processo'] = dados.pop('n_processo')
            if 'n_chamado' in dados: dados['incidente'] = dados.pop('n_chamado')
            if 'data_evento' in dados: dados['data'] = dados.pop('data_evento')
            sb.table("certidoes_registro").insert(dados).execute(); return True
        except: return False

    def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado="", hora="", nome_parte=""):
        try:
            doc = Document()
            section = doc.sections[0]
            section.top_margin = Cm(2.5); section.bottom_margin = Cm(2.0)
            section.left_margin = Cm(3.0); section.right_margin = Cm(3.0)
            style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
            
            head_p = doc.add_paragraph(); head_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            runner = head_p.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
            runner.bold = True
            head_p.add_run("Rua Ouro Preto, N° 1564 - Bairro Santo Agostinho - CEP 30170-041 - Belo Horizonte - MG\nwww.tjmg.jus.br - Andar: 3º e 4º PV")
            doc.add_paragraph("\n")
            
            if tipo == 'Geral': p_num = doc.add_paragraph(f"Parecer GEJUD/DIRTEC/TJMG nº ____/2026. Assunto: Notifica erro no “JPe – 2ª Instância” ao peticionar.")
            else: p_num = doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2026. Assunto: Notifica erro no “JPe – 2ª Instância” ao peticionar.")
            p_num.runs[0].bold = True
            
            doc.add_paragraph(f"Belo Horizonte, {data}")
            doc.add_paragraph(f"Exmo(a). Senhor(a) Relator(a),")
            
            if tipo == 'Geral':
                corpo = doc.add_paragraph(); corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                txt = (f"Para fins de cumprimento dos artigos 13 e 14 da Resolução nº 780/2014 do Tribunal de Justiça do Estado de Minas Gerais, "
                    f"informamos que em {data} houve indisponibilidade do portal JPe, superior a uma hora, {hora}, que impossibilitou o peticionamento eletrônico de recursos em processos que já tramitavam no sistema.")
                corpo.add_run(txt)
            elif tipo in ['Eletrônica', 'Eletrônico']:
                corpo = doc.add_paragraph(); corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                corpo.add_run(f"Informamos que de {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}")
                if nome_parte: corpo.add_run(f", Parte/Advogado: {nome_parte}")
                corpo.add_run(".\n\n")
                corpo.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC.\n\n")
            elif tipo in ['Física', 'Físico']:
                corpo1 = doc.add_paragraph(); corpo1.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                corpo1.add_run(f"Informamos que no dia {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}")
                if nome_parte: corpo1.add_run(f", Parte/Advogado: {nome_parte}")
                corpo1.add_run(".")
                doc.add_paragraph("Diante da indisponibilidade específica, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos.")

            doc.add_paragraph("Colocamo-nos à disposição para outras informações.")
            doc.add_paragraph("\nRespeitosamente,")
            sign = doc.add_paragraph("\n___________________________________\nWaner Andrade Silva\n0-009020-9\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN")
            sign.runs[0].bold = True 
            
            buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
            return buffer
        except: return None

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

    # -------------------------------------------------------------------------
    # 7. SINCRONIZAÇÃO E MANIPULAÇÃO DO ESTADO (CORE LOGIC)
    # -------------------------------------------------------------------------
    def save_state():
        try:
            last_run = st.session_state.report_last_run_date
            visual_queue = get_ordered_visual_queue(st.session_state.bastao_queue, st.session_state.status_texto)
            state_to_save = {
                'status_texto': st.session_state.status_texto, 
                'bastao_queue': st.session_state.bastao_queue,
                'visual_queue': visual_queue, 
                'skip_flags': st.session_state.skip_flags, 
                'current_status_starts': st.session_state.current_status_starts,
                'bastao_counts': st.session_state.bastao_counts, 
                'priority_return_queue': st.session_state.priority_return_queue,
                'bastao_start_time': st.session_state.bastao_start_time, 
                'report_last_run_date': last_run, 
                'daily_logs': st.session_state.daily_logs, 
                'previous_states': st.session_state.get('previous_states', {})
            }
            save_state_to_db(state_to_save)
            load_state_from_db.clear() # Limpa cache local
        except Exception as e: print(f"Erro save: {e}")

    def sync_state_from_db():
        try:
            db_data = load_state_from_db()
            if not db_data: return
            
            # Recupera campos básicos
            for k in ['status_texto', 'bastao_queue', 'skip_flags', 'bastao_counts', 'priority_return_queue', 'daily_logs', 'previous_states']:
                if k in db_data: st.session_state[k] = db_data[k]
            
            # CORREÇÃO DO BUG DE DATA (TypeError)
            # Verifica se bastao_start_time é string e converte para datetime
            if 'bastao_start_time' in db_data:
                val = db_data['bastao_start_time']
                if val and isinstance(val, str):
                    try: st.session_state['bastao_start_time'] = datetime.fromisoformat(val)
                    except: st.session_state['bastao_start_time'] = get_brazil_time()
                else:
                    st.session_state['bastao_start_time'] = val

            # Verifica current_status_starts
            if 'current_status_starts' in db_data: 
                st.session_state.current_status_starts = db_data['current_status_starts']

        except Exception as e: print(f"Erro sync: {e}")

    def log_status_change(consultor, old_status, new_status, duration):
        if not isinstance(duration, timedelta): duration = timedelta(0)
        now_br = get_brazil_time()
        st.session_state.daily_logs.append({
            'timestamp': now_br, 'consultor': consultor, 'old_status': old_status, 'new_status': new_status, 
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
        
        # Remove bastão de quem não é o alvo
        for c in CONSULTORES:
            if c != immune_consultant: 
                if c != target and 'Bastão' in st.session_state.status_texto.get(c, ''):
                    log_status_change(c, 'Bastão', '', now - st.session_state.current_status_starts.get(c, now))
                    st.session_state.status_texto[c] = ''; changed = True
        
        # Define novo portador
        if target:
            curr_s = st.session_state.status_texto.get(target, '')
            if 'Bastão' not in curr_s:
                new_s = f"Bastão | {curr_s}" if curr_s else "Bastão"
                log_status_change(target, curr_s, new_s, now - st.session_state.current_status_starts.get(target, now))
                st.session_state.status_texto[target] = new_s; st.session_state.bastao_start_time = now
                if current_holder != target: 
                    st.session_state.play_sound = True
                    send_chat_notification_internal(target, 'Bastão')
                st.session_state.skip_flags[target] = False
                changed = True
        
        if changed: save_state()
        return changed

    # MODIFICADO: LÓGICA DE ATUALIZAÇÃO DE STATUS
    def update_status(novo_status: str, marcar_indisponivel: bool = False, manter_fila_atual: bool = False):
        selected = st.session_state.get('consultor_selectbox')
        if not selected or selected == 'Selecione um nome': return
        
        ensure_daily_reset()
        now_br = get_brazil_time()
        current = st.session_state.status_texto.get(selected, '')
        current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in (s or '')), None)
        
        if marcar_indisponivel:
            st.session_state.skip_flags[selected] = True
            if selected in st.session_state.bastao_queue:
                st.session_state.bastao_queue.remove(selected)
        
        # Se for status Indisponível explicitamente
        if novo_status == 'Indisponível':
            if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)

        elif not manter_fila_atual:
            if selected not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(selected)
            st.session_state.skip_flags[selected] = False
        
        final_status = (novo_status or '').strip()
        
        # Mantém prefixo "Bastão" se for o dono
        if selected == current_holder and selected in st.session_state.bastao_queue:
            final_status = ('Bastão | ' + final_status).strip(' |') if final_status else 'Bastão'
        
        log_status_change(selected, current, final_status, now_br - st.session_state.current_status_starts.get(selected, now_br))
        
        st.session_state.status_texto[selected] = final_status
        check_and_assume_baton()
        save_state()

    # MODIFICADO: LÓGICA ENTRAR/SAIR (TOGGLE)
    def toggle_queue(consultor):
        ensure_daily_reset()
        if consultor in st.session_state.bastao_queue:
            # SAI DA FILA
            st.session_state.bastao_queue.remove(consultor)
            # MUDANÇA: NÃO COLOCA "INDISPONÍVEL". LIMPA O STATUS.
            current = st.session_state.status_texto.get(consultor, '')
            if "Bastão" in current: st.session_state.status_texto[consultor] = ""
            # Se não tem bastão, mantém o status atual ou limpa se for só fila? 
            # Assumindo que limpa status de "Fila" mas mantém atividades.
            # Se quiser limpar tudo:
            # st.session_state.status_texto[consultor] = ""
        else:
            # ENTRA NA FILA
            st.session_state.bastao_queue.append(consultor)
            st.session_state.skip_flags[consultor] = False
        
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
        else:
            check_and_assume_baton()

    def toggle_skip():
        selected = st.session_state.consultor_selectbox
        if selected in st.session_state.bastao_queue:
            st.session_state.skip_flags[selected] = not st.session_state.skip_flags.get(selected, False)
            save_state()

    def toggle_view(v):
        st.session_state.active_view = v

    def init_session_state():
        if 'db_loaded' not in st.session_state:
            db = load_state_from_db(); st.session_state.update(db); st.session_state['db_loaded'] = True
        defaults = {
            'bastao_start_time': None, 'report_last_run_date': datetime.min, 'consultor_selectbox': "Selecione um nome", 
            'status_texto': {n: '' for n in CONSULTORES}, 'bastao_queue': [], 'skip_flags': {}, 
            'current_status_starts': {n: get_brazil_time() for n in CONSULTORES}, 'bastao_counts': {n: 0 for n in CONSULTORES}, 
            'priority_return_queue': [], 'daily_logs': [], 'active_view': None, 'word_buffer': None, 'view_logmein_ui': False
        }
        for k, v in defaults.items():
            if k not in st.session_state: st.session_state[k] = v
        for n in CONSULTORES: st.session_state.skip_flags.setdefault(n, False)

    # -------------------------------------------------------------------------
    # 8. CONSTRUÇÃO DA INTERFACE GRÁFICA (SIDEBAR + HEADER + MAIN)
    # -------------------------------------------------------------------------
    
    # CSS Customizado
    st.markdown("""<style>div.stButton > button {width: 100%; height: 3rem;}</style>""", unsafe_allow_html=True)
    
    # Inicializa estado
    init_session_state(); memory_sweeper(); auto_manage_time()

    # --- SIDEBAR MODIFICADA (MENU SUSPENSO, SEM TROCAR EQUIPE) ---
    with st.sidebar:
        st.markdown(f"### 🏢 {team_name}")
        st.caption("Central Unificada 2026")
        
        # REMOVIDO: Botão "Trocar Equipe"
        
        # LOGMEIN EM EXPANDER (Menu Suspenso)
        with st.expander("🔑 LogMeIn", expanded=False):
            l_user, l_in_use = get_logmein_status()
            if l_in_use:
                st.error(f"Em uso: {l_user}")
                # Botão para liberar
                if st.button("Liberar LogMeIn", key="btn_lib_log_side"):
                    set_logmein_status(None, False); st.rerun()
            else:
                st.success("Livre")
                meu_nome = st.session_state.get('consultor_selectbox')
                if meu_nome and meu_nome != "Selecione um nome":
                    # Botão para assumir
                    if st.button("Assumir LogMeIn", key="btn_ass_log_side"):
                        set_logmein_status(meu_nome, True); st.rerun()
                else:
                    st.info("Selecione seu nome no painel.")

        # FILA VIZINHA EM EXPANDER (Menu Suspenso)
        with st.expander(f"👀 Fila {other_team_name}", expanded=False):
            # Carrega dados da outra equipe
            other_data = load_state_from_db(other_team_id)
            other_queue = other_data.get('bastao_queue', [])
            other_status = other_data.get('status_texto', {})
            
            if not other_queue:
                st.info("Fila vazia.")
            else:
                other_holder = next((c for c, s in other_status.items() if 'Bastão' in s), None)
                # Ordenação visual da fila vizinha
                try: idx = other_queue.index(other_holder)
                except: idx = 0
                ordered = other_queue[idx:] + other_queue[:idx] if other_holder else other_queue
                
                for i, nome in enumerate(ordered):
                    extra = "🎭" if nome == other_holder else f"{i}º"
                    st.markdown(f"**{extra} {nome}**")

    # --- HEADER PRINCIPAL ---
    @st.fragment(run_every=15)
    def render_header():
        sync_state_from_db()
        c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
        with c_topo_esq:
            img = get_img_as_base64_cached(PUG2026_FILENAME); src = f"data:image/png;base64,{img}" if img else GIF_BASTAO_HOLDER
            st.markdown(f"""<div style="display: flex; align-items: center; gap: 15px;"><h1 style="margin: 0; padding: 0; font-size: 2.2rem; color: #FF8C00;">Painel {team_name} {BASTAO_EMOJI}</h1><img src="{src}" style="width: 100px; height: 100px; border-radius: 10px; border: 4px solid #FF8C00; object-fit: cover;"></div>""", unsafe_allow_html=True)
        with c_topo_dir:
            # Botão de entrada rápida
            c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
            with c_sub1: 
                novo_responsavel = st.selectbox("Assumir (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
            with c_sub2:
                if st.button("🚀", use_container_width=True, key="btn_entrar_header"):
                    if novo_responsavel != "Selecione": toggle_queue(novo_responsavel); st.rerun()

        # Resumo Responsável com Cálculo de Tempo Seguro
        resp = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        st.markdown("###")
        if resp:
            # CORREÇÃO DE CÁLCULO DE TEMPO
            start_t = st.session_state.bastao_start_time
            if start_t and isinstance(start_t, str):
                try: start_t = datetime.fromisoformat(start_t)
                except: start_t = get_brazil_time()
            elif not start_t:
                start_t = get_brazil_time()

            dur = get_brazil_time() - start_t
            st.success(f"🎭 **BASTÃO COM: {resp}** (Tempo: {format_time_duration(dur)})")
        else:
            st.info("Ninguém com o bastão.")
    
    render_header()
    
    # --- FRAGMENTO DE LISTA LATERAL (DIREITA) ---
    @st.fragment(run_every=15)
    def render_status_list():
        sync_state_from_db()
        queue = st.session_state.bastao_queue
        skips = st.session_state.skip_flags
        responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)

        st.header('Status dos(as) Consultores(as)')
        # Separação em listas (Preservado do original)
        ui_lists = {'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade_especifica': [], 'sessao_especifica': [], 'projeto_especifico': [], 'reuniao_especifica': [], 'treinamento_especifico': [], 'indisponivel': [], 'presencial_especifico': []}
        for nome in CONSULTORES:
            if nome in st.session_state.bastao_queue: ui_lists['fila'].append(nome)
            status = st.session_state.status_texto.get(nome, ''); status = status if status is not None else ''
            if status in ('', None): pass
            elif status == 'Almoço': ui_lists['almoco'].append(nome)
            elif status == 'Saída rápida': ui_lists['saida'].append(nome)
            elif status == 'Indisponível' and nome not in st.session_state.bastao_queue: ui_lists['indisponivel'].append(nome)
            if isinstance(status, str):
                if 'Sessão:' in status or status.strip() == 'Sessão': ui_lists['sessao_especifica'].append((nome, status.replace('Sessão:', '').strip()))
                if 'Reunião:' in status or status.strip() == 'Reunião': ui_lists['reuniao_especifica'].append((nome, status.replace('Reunião:', '').strip()))
                if 'Projeto:' in status or status.strip() == 'Projeto': ui_lists['projeto_especifico'].append((nome, status.replace('Projeto:', '').strip()))
                if 'Treinamento:' in status or status.strip() == 'Treinamento': ui_lists['treinamento_especifico'].append((nome, status.replace('Treinamento:', '').strip()))
                if 'Atividade:' in status or status.strip() == 'Atendimento': ui_lists['atividade_especifica'].append((nome, status.replace('Atividade:', '').strip()))
                if 'Atendimento Presencial:' in status: ui_lists['presencial_especifico'].append((nome, status.replace('Atendimento Presencial:', '').strip()))

        # Renderização das listas
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
                    col_n, col_c = st.columns([0.85, 0.15], vertical_alignment='center')
                    # Botãozinho para voltar da indisponibilidade
                    if titulo == 'Indisponível': 
                         # OBS: Como não tenho a função 'enter_from_indisponivel' definida no escopo global dessa versão simplificada,
                         # chamarei toggle_queue se checkbox for marcado
                         if col_c.checkbox(' ', key=f'chk_{titulo}_{nome}_frag', value=False, label_visibility='collapsed'):
                            toggle_queue(nome); st.rerun()
                    col_n.markdown(f"<div style='font-size: 16px; margin: 2px 0;'><strong>{nome}</strong><span style='background-color: {bg_hex}; color: #333; padding: 2px 8px; border-radius: 12px; font-size: 14px; margin-left: 8px;'>{desc}</span></div>", unsafe_allow_html=True)
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

    # --- ÁREA PRINCIPAL DE AÇÃO ---
    col_principal, col_disponibilidade = st.columns([1.5, 1])

    with col_disponibilidade:
        render_status_list()

    with col_principal:
        st.markdown("### 🎮 Painel de Ação")
        c_nome, c_act1, c_act2, c_act3 = st.columns([2, 1, 1, 1], vertical_alignment="bottom")
        with c_nome:
            st.selectbox('Selecione:', ['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
        with c_act1:
            if st.button("🎭 Entrar/Sair Fila", use_container_width=True): 
                toggle_queue(st.session_state.consultor_selectbox); st.rerun()
        with c_act2:
            if st.button('🎯 Passar', use_container_width=True): 
                rotate_bastao(); st.rerun()
        with c_act3:
            if st.button('⏭️ Pular', use_container_width=True): 
                toggle_skip(); st.rerun()
        
        # GRADE DE BOTÕES (Preservada Original)
        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        if r2c1.button('📋 Atividades'): st.session_state.active_view = 'menu_atividades'; st.rerun()
        if r2c2.button('🏗️ Projeto'): st.session_state.active_view = 'menu_projetos'; st.rerun()
        if r2c3.button('🎓 Treino'): st.session_state.active_view = 'menu_treinamento'; st.rerun()
        if r2c4.button('📅 Reunião'): st.session_state.active_view = 'menu_reuniao'; st.rerun()
        if r2c5.button('🍽️ Almoço'): update_status('Almoço', manter_fila_atual=True); st.rerun()
        
        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        if r3c1.button('🎙️ Sessão'): st.session_state.active_view = 'menu_sessao'; st.rerun()
        if r3c2.button('🚶 Saída'): update_status('Saída rápida', marcar_indisponivel=True); st.rerun()
        if r3c3.button('🏃 Sair Geral'): update_status('Indisponível', marcar_indisponivel=True); st.rerun()
        if r3c4.button("🤝 Presencial"): st.session_state.active_view = 'menu_presencial'; st.rerun()

        # RENDERIZAÇÃO DE MENUS EXPANSÍVEIS
        if st.session_state.active_view:
            st.divider()
            with st.container(border=True):
                if st.session_state.active_view == 'menu_atividades':
                    at_t = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS); at_e = st.text_input("Detalhe:")
                    if st.button("Confirmar", type="primary"): 
                        update_status(f"Atividade: {', '.join(at_t)} - {at_e}", manter_fila_atual=True)
                        st.session_state.active_view = None; st.rerun()

                elif st.session_state.active_view == 'menu_projetos':
                    proj_nome = st.text_input('Nome do Projeto:')
                    manter = st.checkbox("Manter na fila?")
                    if st.button("Confirmar"):
                        update_status(f"Projeto: {proj_nome}", manter_fila_atual=manter)
                        st.session_state.active_view = None; st.rerun()

                elif st.session_state.active_view == 'menu_treinamento':
                    tema = st.text_input('Tema:'); obs = st.text_input('Obs:')
                    if st.button("Confirmar"):
                        update_status(f"Treinamento: {tema} {obs}", marcar_indisponivel=True)
                        st.session_state.active_view = None; st.rerun()

                elif st.session_state.active_view == 'menu_reuniao':
                    assunto = st.text_input('Assunto:')
                    if st.button("Confirmar"):
                        update_status(f"Reunião: {assunto}", marcar_indisponivel=True)
                        st.session_state.active_view = None; st.rerun()
                
                elif st.session_state.active_view == 'menu_sessao':
                    sessao = st.text_input('Câmara/Sessão:')
                    if st.button("Confirmar"):
                        update_status(f"Sessão: {sessao}", marcar_indisponivel=True)
                        st.session_state.active_view = None; st.rerun()

                elif st.session_state.active_view == 'menu_presencial':
                    local = st.text_input('Local:'); obj = st.text_input('Objetivo:')
                    if st.button("Confirmar"):
                        update_status(f"Presencial: {local} - {obj}", marcar_indisponivel=True)
                        st.session_state.active_view = None; st.rerun()
                
                elif st.session_state.active_view == 'checklist':
                    st.header("Gerador de Checklist")
                    camara = st.text_input("Câmara:")
                    if st.button("Gerar HTML"): 
                        send_to_chat("sessao", f"Consultor {st.session_state.consultor_selectbox} acompanhando {camara}")
                        st.success("Enviado!"); st.session_state.active_view = None; st.rerun()

                elif st.session_state.active_view == 'chamados':
                    st.header('Chamados / Jira')
                    txt = st.text_area('Texto:')
                    if st.button('Enviar'):
                        if handle_chamado_submission(): st.success('Enviado!'); st.session_state.active_view = None; st.rerun()

                elif st.session_state.active_view == 'atendimentos':
                    st.header('Registro de Atendimentos')
                    at_d = st.date_input('Data', value=date.today()); at_u = st.selectbox('Usuário', REG_USUARIO_OPCOES)
                    at_s = st.text_input('Setor'); at_sys = st.selectbox('Sistema', REG_SISTEMA_OPCOES)
                    at_desc = st.text_input('Descrição'); at_c = st.selectbox('Canal', REG_CANAL_OPCOES)
                    at_r = st.selectbox('Desfecho', REG_DESFECHO_OPCOES); at_j = st.text_input('Jira')
                    if st.button('Enviar'):
                        send_atendimento_to_chat(st.session_state.consultor_selectbox, at_d, at_u, at_s, at_sys, at_desc, at_c, at_r, at_j)
                        st.success('Enviado!'); st.session_state.active_view = None; st.rerun()

                elif st.session_state.active_view == 'hextras':
                    st.header("Horas Extras")
                    h_d = st.date_input("Data"); h_i = st.time_input("Início"); h_t = st.text_input("Total"); h_m = st.text_input("Motivo")
                    if st.button("Registrar"):
                        send_horas_extras_to_chat(st.session_state.consultor_selectbox, h_d, h_i, h_t, h_m)
                        st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
                
                elif st.session_state.active_view == 'erro_novidade':
                    st.header("Erro / Novidade")
                    t1 = st.text_input("Título"); t2 = st.text_area("Objetivo"); t3 = st.text_area("Relato"); t4 = st.text_area("Resultado")
                    if st.button("Enviar"):
                        handle_erro_novidade_submission(st.session_state.consultor_selectbox, t1, t2, t3, t4)
                        st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
                
                elif st.session_state.active_view == 'sugestao':
                    st.header("Sugestão")
                    stxt = st.text_area("Texto")
                    if st.button("Enviar"):
                        handle_sugestao_submission(st.session_state.consultor_selectbox, stxt)
                        st.success("Enviado!"); st.session_state.active_view = None; st.rerun()

                elif st.session_state.active_view == "certidao":
                    st.header("🖨️ Registro de Certidão (2026)")
                    c_data = st.date_input("Data do Evento:", value=get_brazil_time().date(), format="DD/MM/YYYY")
                    tipo_cert = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"])
                    c_cons = st.session_state.consultor_selectbox
                    c_motivo = st.text_area("Motivo/Detalhes:", height=100)
                    
                    if tipo_cert == "Geral": 
                        c_hora = st.text_input("Horário/Período:")
                        c_proc = ""; c_chamado = ""; c_nome_parte = ""; c_peticao = ""
                        if c_hora: c_motivo = f"{c_motivo} - Período: {c_hora}"
                    else: 
                        c1, c2 = st.columns(2)
                        c_proc = c1.text_input("Processo:")
                        c_chamado = c2.text_input("Chamado:")
                        c3, c4 = st.columns(2)
                        c_nome_parte = c3.text_input("Parte/Advogado:")
                        c_peticao = c4.selectbox("Petição:", ["Inicial", "Recursal", "Intermediária", "Outros"])
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("📄 Gerar Word"): 
                            st.session_state.word_buffer = gerar_docx_certidao_internal(tipo_cert, c_proc, c_data.strftime("%d/%m/%Y"), c_cons, c_motivo, c_chamado, c_hora, c_nome_parte)
                        if st.session_state.word_buffer: 
                            st.download_button("⬇️ Baixar", st.session_state.word_buffer, file_name="certidao.docx")
                    with c2:
                        if st.button("💾 Salvar", type="primary"):
                            if verificar_duplicidade_certidao(tipo_cert, c_proc, c_data): st.error("Duplicidade!")
                            else:
                                payload = {"tipo": tipo_cert, "data": c_data.isoformat(), "consultor": c_cons, "incidente": c_chamado, "processo": c_proc, "motivo": c_motivo, "nome_parte": c_nome_parte, "peticao": c_peticao}
                                if salvar_certidao_db(payload):
                                    send_to_chat("certidao", f"Nova Certidão: {c_cons} - {c_proc}")
                                    st.success("Salvo!"); st.session_state.active_view = None; st.rerun()

                # Botão Cancelar Geral
                if st.button("❌ Fechar Menu", use_container_width=True):
                    st.session_state.active_view = None; st.rerun()

        # BARRA DE FERRAMENTAS INFERIOR
        st.markdown("---")
        c_t1, c_t2, c_t3, c_t4 = st.columns(4)
        if c_t1.button("📑 Checklist"): st.session_state.active_view = 'checklist'; st.rerun()
        if c_t2.button("🆘 Chamados"): st.session_state.active_view = 'chamados'; st.rerun()
        if c_t3.button("📝 Atendimentos"): st.session_state.active_view = 'atendimentos'; st.rerun()
        if c_t4.button("⏰ H. Extras"): st.session_state.active_view = 'hextras'; st.rerun()
        
        c_t5, c_t6, c_t7 = st.columns(3)
        if c_t5.button("🐛 Erro/Novidade"): st.session_state.active_view = 'erro_novidade'; st.rerun()
        if c_t6.button("🖨️ Certidão"): st.session_state.active_view = 'certidao'; st.rerun()
        if c_t7.button("💡 Sugestão"): st.session_state.active_view = 'sugestao'; st.rerun()

    # --- GRÁFICO OPERACIONAL (PRESERVADO) ---
    st.markdown("---")
    st.subheader("📊 Resumo Operacional")
    
    df_chart, gerado_em = carregar_dados_grafico()
    
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
