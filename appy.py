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

from repository import load_state_from_db, save_state_to_db
from utils import (get_brazil_time, get_secret, send_to_chat, gerar_docx_certidao, get_img_as_base64)

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

# ============================================
# 2. FUNÇÕES BASE
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
    msg = f"🐛 **Novo Relato de Erro/Novidade**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n📌 **Título:** {titulo}\n\n🎯 **Objetivo:**\n{objetivo}\n\n🧪 **Relato:**\n{relato}\n\n🏁 **Resultado:**\n{resultado}"
    send_to_chat("erro", msg); return True

def send_sessao_to_chat_fn(consultor, texto_mensagem):
    if not consultor or consultor == 'Selecione um nome': return False
    send_to_chat("sessao", texto_mensagem); return True

def send_certidao_notification_to_chat(consultor, tipo):
    msg = f"Consultor {consultor} solicitou uma certidão ({tipo}) de indisponibilidade."
    send_to_chat("certidao", msg); return True

def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'
def render_fireworks(): st.markdown("""<style>...</style>""", unsafe_allow_html=True)
def gerar_html_checklist(c, m, d): return "..."
def gerar_docx_certidao(t, n, d, c, m): 
    from docx import Document; import io; document = Document(); buffer = io.BytesIO(); document.save(buffer); buffer.seek(0); return buffer

def send_daily_report():
    logs = load_logs(); bastao_counts = st.session_state.bastao_counts.copy()
    aggregated_data = {nome: {} for nome in CONSULTORES}
    for log in logs:
        try:
            consultor, status, duration = log['consultor'], log['old_status'], log.get('duration', timedelta(0))
            if not isinstance(duration, timedelta): duration = timedelta(seconds=float(duration))
            if status and consultor in aggregated_data: aggregated_data[consultor][status] = aggregated_data[consultor].get(status, timedelta(0)) + duration
        except: pass
    now_br = get_brazil_time(); today_str = now_br.strftime("%d/%m/%Y")
    report_text = f"📊 **Relatório Diário - {today_str}** 📊\n\n"; has_data = False
    for nome in CONSULTORES:
        counts, times = bastao_counts.get(nome, 0), aggregated_data.get(nome, {})
        if counts > 0 or times:
            has_data = True; report_text += f"**👤 {nome}**\n- 🥂 Bastão: **{counts}**\n"
            for s, t in sorted(times.items(), key=itemgetter(0)):
                if s != 'Bastão': report_text += f"- {s}: **{format_time_duration(t)}**\n"
            report_text += "\n"
    if not has_data: report_text += "Nenhuma atividade registrada."
    send_to_chat("backup", report_text)
    st.session_state['report_last_run_date'] = now_br
    st.session_state['daily_logs'] = []; st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
    save_state()

# --- LÓGICA DE FILA BLINDADA (AGRESSIVA) ---
def find_next_holder_index(current_index, queue, skips):
    """
    Retorna o índice do próximo ELEGÍVEL na fila. 
    Se todos estiverem pulando, força o vizinho.
    """
    if not queue: return -1
    n = len(queue)
    start_index = (current_index + 1) % n
    
    # 1. Tenta achar alguém que NÃO esteja pulando
    for i in range(n):
        idx = (start_index + i) % n
        consultor = queue[idx]
        if consultor == queue[current_index] and n > 1:
            continue
        if not skips.get(consultor, False):
            return idx
            
    # 2. SE NINGUÉM FOR ACHADO (todos pulando), PEGA O PRÓXIMO NA MARRA
    if n > 1:
        proximo_imediato_idx = (current_index + 1) % n
        # Força o reset do skip do escolhido
        nome_escolhido = queue[proximo_imediato_idx]
        st.session_state.skip_flags[nome_escolhido] = False 
        return proximo_imediato_idx

    return -1

def check_and_assume_baton(forced_successor=None, immune_consultant=None):
