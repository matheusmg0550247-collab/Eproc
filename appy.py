# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta, date, time as dt_time
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json
import re
import threading
import random
import base64
import os

# --- Constantes de Consultores ---
CONSULTORES = sorted([
    "Alex Paulo da Silva",
    "Dirceu Gonçalves Siqueira Neto",
    "Douglas de Souza Gonçalves",
    "Farley Leandro de Oliveira Juliano", 
    "Gleis da Silva Rodrigues",
    "Hugo Leonardo Murta",
    "Igor Dayrell Gonçalves Correa",
    "Jerry Marcos dos Santos Neto",
    "Jonatas Gomes Saraiva",
    "Leandro Victor Catharino",
    "Luiz Henrique Barros Oliveira",
    "Marcelo dos Santos Dutra",
    "Marina Silva Marques",
    "Marina Torres do Amaral",
    "Vanessa Ligiane Pimenta Santos"
])

# --- FUNÇÃO DE CACHE GLOBAL ---
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    print("--- Inicializando o Cache de Estado GLOBAL (Executa Apenas 1x) ---")
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        'lunch_warning_info': None,
        'auxilio_ativo': False, 
        'daily_logs': [],
        'simon_ranking': [] 
    }

# --- Constantes (Webhooks) ---
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQA5CyNolU/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zolqmc0YfJ5bPzsqLrefwn8yBbNQLLfFBzLTwIkr7W4" 
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"

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

OPCOES_ATIVIDADES_STATUS = [
    "HP", "E-mail", "Whatsapp/Plantão", 
    "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"
]
# Atividades que exigem complemento
ATIVIDADES_EXIGEM_DETALHE = ["Treinamento", "Homologação", "Redação Documentos", "Outros"]

GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUSES_DE_SAIDA = ['Atendimento', 'Almoço', 'Saída rápida', 'Ausente', 'Sessão'] 
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_LUNCH_WARNING = 'https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGZlbHN1azB3b2drdTI1eG10cDEzeWpmcmtwenZxNTV0bnc2OWgzZSYlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/bNlqpmBJRDMpxulfFB/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
PUG2026_FILENAME = "pug2026.png"

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return None

def load_logs(): return st.session_state.daily_logs

def date_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    if isinstance(obj, timedelta): return obj.total_seconds()
    if isinstance(obj, (date, dt_time)): return obj.isoformat()
    return str(obj)

def save_state():
    global_data = get_global_state_cache()
    try:
        global_data['status_texto'] = st.session_state.status_texto.copy()
        global_data['bastao_queue'] = st.session_state.bastao_queue.copy()
        global_data['skip_flags'] = st.session_state.skip_flags.copy()
        global_data['current_status_starts'] = st.session_state.current_status_starts.copy()
        global_data['bastao_counts'] = st.session_state.bastao_counts.copy()
        global_data['priority_return_queue'] = st.session_state.priority_return_queue.copy()
        global_data['bastao_start_time'] = st.session_state.bastao_start_time
        global_data['report_last_run_date'] = st.session_state.report_last_run_date
        global_data['rotation_gif_start_time'] = st.session_state.get('rotation_gif_start_time')
        global_data['lunch_warning_info'] = st.session_state.get('lunch_warning_info')
        global_data['auxilio_ativo'] = st.session_state.get('auxilio_ativo', False) 
        global_data['daily_logs'] = json.loads(json.dumps(st.session_state.daily_logs, default=date_serializer))
        if 'simon_ranking' in st.session_state: global_data['simon_ranking'] = st.session_state.simon_ranking.copy()
    except Exception as e: print(f'Erro ao salvar estado GLOBAL: {e}')

def load_state():
    global_data = get_global_state_cache()
    loaded_logs = global_data.get('daily_logs', [])
    if loaded_logs and isinstance(loaded_logs[0], dict): deserialized_logs = loaded_logs
    else:
        try: deserialized_logs = json.loads(loaded_logs)
        except: deserialized_logs = loaded_logs 
    final_logs = []
    for log in deserialized_logs:
        if isinstance(log, dict):
            if 'duration' in log and not isinstance(log['duration'], timedelta):
                try: log['duration'] = timedelta(seconds=float(log['duration']))
                except: log['duration'] = timedelta(0)
            if 'timestamp' in log and isinstance(log['timestamp'], str):
                try: log['timestamp'] = datetime.fromisoformat(log['timestamp'])
                except: log['timestamp'] = datetime.min
            final_logs.append(log)
    loaded_data = {k: v for k, v in global_data.items() if k != 'daily_logs'}
    loaded_data['daily_logs'] = final_logs
    return loaded_data

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    entry = {
        'timestamp': datetime.now(),
        'consultor': consultor,
        'old_status': old_status, 
        'new_status': new_status,
        'duration': duration,
        'duration_s': duration.total_seconds()
    }
    st.session_state.daily_logs.append(entry)
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def _send_webhook_thread(url, payload):
    try: requests.post(url, json=payload, timeout=5)
    except: pass

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        message_text = f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {APP_URL_CLOUD}"
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, {"text": message_text})).start()
        return True
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    if not GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS: return False
    msg = (f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n"
           f"🕐 **Início:** {inicio.strftime('%H:%M')}\n⏱️ **Tempo Total:** {tempo}\n📝 **Motivo:** {motivo}")
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS, {"text": msg})).start()
    return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO: return False
    jira_str = f"\n🔢 **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = (f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n"
           f"👥 **Usuário:** {usuario}\n🏢 **Nome/Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {descricao}\n"
           f"📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{jira_str}")
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_REGISTRO, {"text": msg})).start()
    return True

def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'

def render_fireworks():
    fireworks_css = """
    <style>
    @keyframes firework {
      0% { transform: translate(var(--x), var(--initialY)); width: var(--initialSize); opacity: 1; }
      50% { width: 0.5vmin; opacity: 1; }
      100% { width: var(--finalSize); opacity: 0; }
    }
    .firework, .firework::before, .firework::after {
      --initialSize: 0.5vmin; --finalSize: 45vmin; --particleSize: 0.2vmin;
      --color1: #ff0000; --color2: #ffd700; --color3: #b22222; --color4: #daa520; --color5: #ff4500; --color6: #b8860b;
      --y: -30vmin; --x: -50%; --initialY: 60vmin; content: ""; animation: firework 2s infinite; position: absolute;
      top: 50%; left: 50%; transform: translate(-50%, var(--y)); width: var(--initialSize); aspect-ratio: 1;
      background: radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%, 
      radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 50% 100%,
      radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 0% 50%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 80% 90%,
      radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 95% 90%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 90% 70%,
      radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 60%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 55% 80%,
      radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 70% 77%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 22% 90%,
      radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 45% 90%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 33% 70%,
      radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 10% 60%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 31% 80%,
      radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 28% 77%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 13% 72%,
      radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 80% 10%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 95% 14%,
      radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 90% 23%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 100% 43%,
      radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 85% 27%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 77% 37%,
      radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 60% 7%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 22% 14%,
      radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 45% 20%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 33% 34%,
      radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 10% 29%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 31% 37%,
      radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 28% 7%;
      background-size: var(--initialSize) var(--initialSize); background-repeat: no-repeat;
    }
    .firework::before { --x: -50%; --y: -50%; --initialY: -50%; transform: translate(-50%, -50%) rotate(40deg) scale(1.3) rotateY(40deg); }
    .firework::after { --x: -50%; --y: -50%; --initialY: -50%; transform: translate(-50%, -50%) rotate(170deg) scale(1.15) rotateY(-30deg); }
    .firework:nth-child(2) { --x: 30vmin; }
    .firework:nth-child(2), .firework:nth-child(2)::before, .firework:nth-child(2)::after { --color1: #ff0000; --color2: #ffd700; --finalSize: 40vmin; left: 30%; top: 60%; animation-delay: -0.25s; }
    .firework:nth-child(3) { --x: -30vmin; --y: -50vmin; }
    .firework:nth-child(3), .firework:nth-child(3)::before, .firework:nth-child(3)::after { --color1: #ffd700; --color2: #ff4500; --finalSize: 35vmin; left: 70%; top: 60%; animation-delay: -0.4s; }
    </style>
    <div class="firework"></div><div class="firework"></div><div class="firework"></div>
    """
    st.markdown(fireworks_css, unsafe_allow_html=True)

def gerar_html_checklist(consultor_nome, camara_nome, data_sessao_formatada):
    consultor_formatado = f"@{consultor_nome}" if not consultor_nome.startswith("@") else consultor_nome
    return f"""<html><body style='font-family: Arial;'><h2>Checklist Sessão - {camara_nome}</h2><p>Resp: {consultor_formatado}</p><p>Data: {data_sessao_formatada}</p></body></html>"""

def send_sessao_to_chat(consultor, texto_mensagem):
    if not GOOGLE_CHAT_WEBHOOK_SESSAO or not consultor or consultor == 'Selecione um nome': return False
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_SESSAO, {'text': texto_mensagem})).start()
    return True

def send_daily_report(): 
    logs = load_logs(); bastao_counts = st.session_state.bastao_counts.copy()
    aggregated_data = {nome: {} for nome in CONSULTORES}
    for log in logs:
        try:
            consultor = log['consultor']; status = log['old_status']; duration = log.get('duration', timedelta(0))
            if status and consultor in aggregated_data: aggregated_data[consultor][status] = aggregated_data[consultor].get(status, timedelta(0)) + duration
        except: pass
    report_text = f"📊 **Relatório Diário - {datetime.now().strftime('%d/%m/%Y')}** 📊\n\n"
    for nome in CONSULTORES:
        counts = bastao_counts.get(nome, 0); times = aggregated_data.get(nome, {}); bastao_time = times.get('Bastão', timedelta(0))
        if counts > 0 or times:
            report_text += f"**👤 {nome}**\n- Bastão: {counts}x | Tempo: {format_time_duration(bastao_time)}\n"
    if GOOGLE_CHAT_WEBHOOK_BACKUP: threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_BACKUP, {'text': report_text})).start()
    st.session_state['report_last_run_date'] = datetime.now(); st.session_state['daily_logs'] = []
    st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}; save_state()

def init_session_state():
    persisted_state = load_state()
    defaults = {
        'bastao_start_time': None, 'report_last_run_date': datetime.min, 'rotation_gif_start_time': None,
        'play_sound': False, 'gif_warning': False, 'lunch_warning_info': None, 'last_reg_status': None, 
        'chamado_guide_step': 0, 'sessao_msg_preview': "", 'html_download_ready': False, 'html_content_cache': "", 
        'auxilio_ativo': False, 'active_view': None, 'last_jira_number': "",
        'simon_sequence': [], 'simon_user_input': [], 'simon_status': 'start', 'simon_level': 1
    }
    for key, default in defaults.items():
        if key not in st.session_state: st.session_state[key] = persisted_state.get(key, default)
    st.session_state['bastao_queue'] = persisted_state.get('bastao_queue', []).copy()
    st.session_state['priority_return_queue'] = persisted_state.get('priority_return_queue', []).copy()
    st.session_state['bastao_counts'] = persisted_state.get('bastao_counts', {}).copy()
    st.session_state['skip_flags'] = persisted_state.get('skip_flags', {}).copy()
    st.session_state['status_texto'] = persisted_state.get('status_texto', {}).copy()
    st.session_state['current_status_starts'] = persisted_state.get('current_status_starts', {}).copy()
    st.session_state['daily_logs'] = persisted_state.get('daily_logs', []).copy() 
    st.session_state['auxilio_ativo'] = persisted_state.get('auxilio_ativo', False)
    st.session_state['simon_ranking'] = persisted_state.get('simon_ranking', [])
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0); st.session_state.skip_flags.setdefault(nome, False)
        current_status = st.session_state.status_texto.get(nome, 'Indisponível')
        st.session_state.status_texto.setdefault(nome, current_status)
        st.session_state[f'check_{nome}'] = (current_status == 'Bastão' or current_status == '') and nome not in st.session_state.priority_return_queue
        if nome not in st.session_state.current_status_starts: st.session_state.current_status_starts[nome] = datetime.now()
    if not st.session_state.bastao_queue:
        checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
        if checked_on: st.session_state.bastao_queue = sorted(list(checked_on))
    check_and_assume_baton()

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    num = len(queue)
    if current_index >= num or current_index < -1: current_index = -1
    next_idx = (current_index + 1) % num
    for _ in range(num):
        c = queue[next_idx]
        if not skips.get(c, False) and st.session_state.get(f'check_{c}'): return next_idx
        next_idx = (next_idx + 1) % num
    return -1

def check_and_assume_baton():
    queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    is_valid = (current_holder and current_holder in queue and st.session_state.get(f'check_{current_holder}'))
    first_idx = find_next_holder_index(-1, queue, skips)
    should_have = current_holder if is_valid else (queue[first_idx] if first_idx != -1 else None)
    changed = False
    for c in CONSULTORES:
        if c != should_have and st.session_state.status_texto.get(c) == 'Bastão':
            log_status_change(c, 'Bastão', 'Indisponível', datetime.now() - st.session_state.current_status_starts.get(c, datetime.now()))
            st.session_state.status_texto[c] = 'Indisponível'; changed = True
    if should_have and st.session_state.status_texto.get(should_have) != 'Bastão':
        log_status_change(should_have, st.session_state.status_texto.get(should_have, ''), 'Bastão', datetime.now() - st.session_state.current_status_starts.get(should_have, datetime.now()))
        st.session_state.status_texto[should_have] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        if current_holder != should_have: st.session_state.play_sound = True; send_chat_notification_internal(should_have, 'Bastão')
        if st.session_state.skip_flags.get(should_have): st.session_state.skip_flags[should_have] = False
        changed = True
    elif not should_have and current_holder:
        log_status_change(current_holder, 'Bastão', 'Indisponível', datetime.now() - st.session_state.current_status_starts.get(current_holder, datetime.now()))
        st.session_state.status_texto[current_holder] = 'Indisponível'; changed = True; st.session_state.bastao_start_time = None
    if changed: save_state()
    return changed

def update_queue(consultor):
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None; st.session_state.lunch_warning_info = None
    is_checked = st.session_state.get(f'check_{consultor}')
    old_status = st.session_state.status_texto.get(consultor, '')
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())
    if is_checked:
        log_status_change(consultor, old_status or 'Indisponível', '', duration)
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
        st.session_state.skip_flags[consultor] = False
        if consultor in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(consultor)
    else:
        if old_status not in STATUSES_DE_SAIDA and old_status != 'Bastão':
            log_status_change(consultor, old_status, 'Indisponível', duration)
            st.session_state.status_texto[consultor] = 'Indisponível'
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
        st.session_state.skip_flags.pop(consultor, None)
    if not check_and_assume_baton(): save_state()

def rotate_bastao():
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None; st.session_state.lunch_warning_info = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder: st.session_state.gif_warning = True; return
    try: current_index = queue.index(current_holder)
    except: check_and_assume_baton(); return
    next_idx = find_next_holder_index(current_index, queue, skips)
    if next_idx != -1:
        next_holder = queue[next_idx]
        log_status_change(current_holder, 'Bastão', '', datetime.now() - (st.session_state.bastao_start_time or datetime.now()))
        st.session_state.status_texto[current_holder] = ''
        log_status_change(next_holder, st.session_state.status_texto.get(next_holder, ''), 'Bastão', timedelta(0))
        st.session_state.status_texto[next_holder] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True; st.session_state.rotation_gif_start_time = datetime.now()
        send_chat_notification_internal(next_holder, 'Bastão'); save_state()
    else: st.warning('Não há próximo(a) consultor(a) elegível.'); check_and_assume_baton()

def toggle_skip():
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    if not st.session_state.get(f'check_{selected}'): st.warning('Consultor indisponível.'); return
    st.session_state.skip_flags[selected] = not st.session_state.skip_flags.get(selected, False)
    if selected == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None) and st.session_state.skip_flags[selected]: rotate_bastao()
    else: save_state()

def update_status(status_text, change_to_available=False):
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    st.session_state[f'check_{selected}'] = False
    was_holder = (st.session_state.status_texto.get(selected) == 'Bastão')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, st.session_state.status_texto.get(selected, ''), status_text, duration)
    st.session_state.status_texto[selected] = status_text
    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skip_flags.pop(selected, None)
    if status_text == 'Saída rápida' and selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)
    if was_holder: check_and_assume_baton()
    else: save_state()

# ============================================
# 3. LÓGICA DO JOGO SIMON
# ============================================

def handle_simon_game():
    COLORS = ["🔴", "🔵", "🟢", "🟡"]
    st.markdown("### 🧠 Jogo da Memória")
    if st.session_state.simon_status == 'start':
        if st.button("▶️ Iniciar", use_container_width=True):
            st.session_state.simon_sequence, st.session_state.simon_user_input, st.session_state.simon_level, st.session_state.simon_status = [random.choice(COLORS)], [], 1, 'showing'
            st.rerun()
    elif st.session_state.simon_status == 'showing':
        st.info(f"Nível {st.session_state.simon_level}: Memorize!")
        cols = st.columns(len(st.session_state.simon_sequence))
        for i, c in enumerate(st.session_state.simon_sequence): cols[i].markdown(f"<h1 style='text-align: center;'>{c}</h1>", unsafe_allow_html=True)
        if st.button("🙈 Responder", type="primary", use_container_width=True): st.session_state.simon_status = 'playing'; st.rerun()
    elif st.session_state.simon_status == 'playing':
        st.markdown(f"**Nível {st.session_state.simon_level}** - Ordem:")
        cols = st.columns(4); pressed = None
        for i, c in enumerate(COLORS):
            if cols[i].button(c, use_container_width=True): pressed = c
        if pressed:
            st.session_state.simon_user_input.append(pressed)
            idx = len(st.session_state.simon_user_input) - 1
            if st.session_state.simon_user_input[idx] != st.session_state.simon_sequence[idx]: st.session_state.simon_status = 'lost'; st.rerun()
            elif len(st.session_state.simon_user_input) == len(st.session_state.simon_sequence):
                st.session_state.simon_sequence.append(random.choice(COLORS)); st.session_state.simon_user_input, st.session_state.simon_level, st.session_state.simon_status = [], st.session_state.simon_level + 1, 'showing'
                st.rerun()
    elif st.session_state.simon_status == 'lost':
        st.error(f"❌ Nível {st.session_state.simon_level}"); consultor = st.session_state.consultor_selectbox
        if consultor and consultor != 'Selecione um nome':
            rank = st.session_state.simon_ranking; found = False
            for entry in rank:
                if entry['nome'] == consultor:
                    if st.session_state.simon_level > entry['score']: entry['score'] = st.session_state.simon_level
                    found = True; break
            if not found: rank.append({'nome': consultor, 'score': st.session_state.simon_level})
            st.session_state.simon_ranking = sorted(rank, key=lambda x: x['score'], reverse=True)[:5]; save_state()
        if st.button("Tentar Novamente"): st.session_state.simon_status = 'start'; st.rerun()
    st.markdown("---"); st.subheader("🏆 Top 5")
    if st.session_state.simon_ranking: st.table(pd.DataFrame(st.session_state.simon_ranking))

# ============================================
# 4. EXECUÇÃO PRINCIPAL
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
render_fireworks()

c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img_data = get_img_as_base64(PUG2026_FILENAME)
    img_src = f"data:image/png;base64,{img_data}" if img_data else GIF_BASTAO_HOLDER
    st.markdown(f'<div style="display: flex; align-items: center; gap: 15px;"><h1 style="color: #FFD700;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1>'
                f'<img src="{img_src}" style="width: 100px; height: 100px; border-radius: 50%; border: 3px solid #FFD700;"></div>', unsafe_allow_html=True)
with c_topo_dir:
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    novo_resp = c_sub1.selectbox("Entrar na Fila", options=["Selecione"] + CONSULTORES, label_visibility="collapsed")
    if c_sub2.button("🚀 Entrar"):
        if novo_resp != "Selecione": st.session_state[f'check_{novo_resp}'] = True; update_queue(novo_resp); st.session_state.consultor_selectbox = novo_resp; st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700;'>", unsafe_allow_html=True)
st_autorefresh(interval=8000, key='auto_rerun')
if st.session_state.get('play_sound'): st.components.v1.html(play_sound_html(), height=0); st.session_state.play_sound = False

col_principal, col_disponibilidade = st.columns([1.5, 1])
queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)

with col_principal:
    st.header("Responsável Atual")
    if responsavel:
        st.markdown(f'<div style="background: #FFF8DC; border: 3px solid #FFD700; padding: 20px; border-radius: 15px; display: flex; align-items: center;">'
                    f'<img src="{GIF_BASTAO_HOLDER}" style="width: 70px; margin-right: 20px; border-radius: 50%;"><div>'
                    f'<span style="font-size: 32px; font-weight: bold; color: #000080;">{responsavel}</span></div></div>', unsafe_allow_html=True)
        dur = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        st.caption(f"⏱️ Tempo: {format_time_duration(dur)}")
    else: st.subheader("(Ninguém com o bastão)")
    
    st.header("Próximos")
    nxt_idx = find_next_holder_index(queue.index(responsavel) if responsavel in queue else -1, queue, skips)
    if nxt_idx != -1: st.markdown(f"### 1º: **{queue[nxt_idx]}**")
    
    st.header("**Consultor(a)**")
    st.selectbox('Selecione seu nome:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    def toggle_view(v): st.session_state.active_view = None if st.session_state.active_view == v else v

    st.markdown("**Ações:**")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True)
    c3.button('📋 Atividades', on_click=lambda: toggle_view('menu_atividades'), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=lambda: update_status('Almoço'), use_container_width=True)
    c5.button('👤 Ausente', on_click=lambda: update_status('Ausente'), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=lambda: toggle_view('form_sessao'), use_container_width=True)
    c7.button('🚶 Saída', on_click=lambda: update_status('Saída rápida'), use_container_width=True)

    # --- SUB-TELAS DE ATIVIDADES ---
    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            st.markdown("### Selecione a Atividade")
            escolhas = st.multiselect("Escolha as opções:", OPCOES_ATIVIDADES_STATUS, placeholder="Escolha as opções")
            detalhe_texto = ""
            precisa_detalhe = any(x in ATIVIDADES_EXIGEM_DETALHE for x in escolhas)
            if precisa_detalhe:
                detalhe_texto = st.text_input("Tipo/Setor/Descrição (Obrigatório):", placeholder="Ex: Treinamento Sistema - Setor X - Descrição Y")
            
            col_conf, col_can = st.columns(2)
            if col_conf.button("Confirmar Atividade", type="primary", use_container_width=True):
                if escolhas:
                    if precisa_detalhe and not detalhe_texto.strip():
                        st.error("Por favor, preencha o campo Tipo/Setor/Descrição.")
                    else:
                        status_final = f"Atividade: {', '.join(escolhas)}"
                        if detalhe_texto: status_final += f" [{detalhe_texto}]"
                        update_status(status_final); st.session_state.active_view = None; st.rerun()
                else: st.warning("Selecione uma atividade.")
            if col_can.button("Cancelar", use_container_width=True): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'form_sessao':
        with st.container(border=True):
            st.markdown("### Registrar Sessão")
            setor_sessao = st.text_input("Setor (Obrigatório):", placeholder="Ex: 5ª Câmara Cível")
            if st.button("Confirmar Sessão", type="primary", use_container_width=True):
                if setor_sessao.strip():
                    update_status(f"Sessão: {setor_sessao}"); st.session_state.active_view = None; st.rerun()
                else: st.error("O Setor é obrigatório.")

    st.markdown("---")
    c_tool1, c_tool2, c_tool3, c_tool4, c_tool5 = st.columns(5)
    c_tool1.button("📑 Checklist", use_container_width=True, on_click=lambda: toggle_view('checklist'))
    c_tool2.button("🆘 Chamados", use_container_width=True, on_click=lambda: toggle_view('chamados'))
    c_tool3.button("📝 Atendimento", use_container_width=True, on_click=lambda: toggle_view('atendimentos'))
    c_tool4.button("⏰ H. Extras", use_container_width=True, on_click=lambda: toggle_view('hextras'))
    c_tool5.button("🧠 Descanso", use_container_width=True, on_click=lambda: toggle_view('descanso'))

    # Renderização de ferramentas (Checklist, Simon, etc) seguem a lógica anterior...
    if st.session_state.active_view == "descanso":
        with st.container(border=True): handle_simon_game()
    elif st.session_state.active_view == "atendimentos":
        with st.container(border=True):
            st.markdown("### Registro de Atendimento")
            at_data = st.date_input("Data:", value=date.today()); at_usuario = st.selectbox("Usuário:", REG_USUARIO_OPCOES)
            at_setor = st.text_input("Nome/Setor:"); at_sistema = st.selectbox("Sistema:", REG_SISTEMA_OPCOES)
            at_desc = st.text_input("Descrição:"); at_canal = st.selectbox("Canal:", REG_CANAL_OPCOES)
            at_desf = st.selectbox("Desfecho:", REG_DESFECHO_OPCOES); at_jira = st.text_input("Jira:")
            if st.button("Enviar", type="primary"):
                if send_atendimento_to_chat(st.session_state.consultor_selectbox, at_data, at_usuario, at_setor, at_sistema, at_desc, at_canal, at_desf, at_jira):
                    st.success("Enviado!"); st.session_state.active_view = None; time.sleep(1); st.rerun()

with col_disponibilidade:
    st.markdown("### Status dos Consultores")
    st.toggle("Auxílio HP/Emails/Whatsapp", key='auxilio_ativo', on_change=save_state)
    if st.session_state.auxilio_ativo: st.warning("Auxílio Ativo"); st.image(GIF_URL_NEDRY, width=150)
    st.markdown("---")
    
    ui_lists = {'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade': [], 'sessao': [], 'indisp': []}
    for nome in CONSULTORES:
        status = st.session_state.status_texto.get(nome, 'Indisponível')
        if status == 'Bastão' or status == '': ui_lists['fila'].append(nome)
        elif 'Atividade:' in status: ui_lists['atividade'].append((nome, status.replace('Atividade: ', '')))
        elif 'Sessão:' in status: ui_lists['sessao'].append((nome, status.replace('Sessão: ', '')))
        elif status == 'Almoço': ui_lists['almoco'].append(nome)
        elif status == 'Saída rápida': ui_lists['saida'].append(nome)
        elif status == 'Ausente': ui_lists['ausente'].append(nome)
        else: ui_lists['indisp'].append(nome)

    def render_list(title, items, color, is_tuple=False):
        st.subheader(f"{title} ({len(items)})")
        for item in items:
            nome = item[0] if is_tuple else item; info = item[1] if is_tuple else title
            c_n, c_c = st.columns([0.7, 0.3])
            c_c.checkbox(" ", key=f"c_{nome}", value=st.session_state.get(f"check_{nome}"), on_change=update_queue, args=(nome,), label_visibility="collapsed")
            if nome == responsavel: c_n.markdown(f"🥂 **{nome}**")
            else: c_n.markdown(f"**{nome}** :{color}-background[{info}]", unsafe_allow_html=True)
        st.markdown("---")

    render_list("Na Fila", ui_lists['fila'], "blue")
    render_list("Em Atividade", ui_lists['atividade'], "orange", True)
    render_list("Sessão", ui_lists['sessao'], "green", True)
    render_list("Almoço", ui_lists['almoco'], "red")
    render_list("Saída Rápida", ui_lists['saida'], "red")
    render_list("Ausente", ui_lists['ausente'], "grey")

# Trigger Relatório
now_br = datetime.utcnow() - timedelta(hours=3)
if now_br.hour >= 20 and now_br.date() > st.session_state.report_last_run_date.date(): send_daily_report()
