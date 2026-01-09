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
  "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

PROJETOS_OPCOES = [
    "Soma", "Treinamentos Eproc", "Manuais Eproc", 
    "Cartilhas Gabinetes", "Notebook Lm", "Inteligência artifical cartórios"
]

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
CHAT_WEBHOOK_BASTAO = "" 
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
    "HP", "E-mail", "WhatsApp Plantão", 
    "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"
]
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUS_SAIDA_PRIORIDADE = ['Saída rápida']
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
    except Exception as e:
        print(f"Erro ao ler imagem local {file_path}: {e}")
        return None

def load_logs():
    return st.session_state.daily_logs

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
        if 'simon_ranking' in st.session_state:
            global_data['simon_ranking'] = st.session_state.simon_ranking.copy()
    except Exception as e: 
        print(f'Erro ao salvar estado GLOBAL: {e}')

def load_state():
    global_data = get_global_state_cache()
    loaded_logs = global_data.get('daily_logs', [])
    if loaded_logs and isinstance(loaded_logs[0], dict):
             deserialized_logs = loaded_logs
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
    print(f'LOG: {consultor} de "{old_status or "-"}" para "{new_status or "-"}" após {duration}')
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
    if consultor not in st.session_state.current_status_starts:
        st.session_state.current_status_starts[consultor] = datetime.now()
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def _send_webhook_thread(url, payload):
    try: requests.post(url, json=payload, timeout=5)
    except Exception as e: print(f"Erro no envio assíncrono: {e}")

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        message_template = "🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {app_url}"
        message_text = message_template.format(consultor=consultor, app_url=APP_URL_CLOUD) 
        chat_message = {"text": message_text}
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, chat_message)).start()
        return True
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    if not GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS: return False
    data_formatada = data.strftime("%d/%m/%Y")
    inicio_formatado = inicio.strftime("%H:%M")
    msg = (f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data_formatada}\n🕐 **Início:** {inicio_formatado}\n⏱️ **Tempo Total:** {tempo}\n📝 **Motivo:** {motivo}")
    chat_message = {"text": msg}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS, chat_message)).start()
    return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO: return False
    data_formatada = data.strftime("%d/%m/%Y")
    jira_str = f"\n🔢 **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = (f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data_formatada}\n👥 **Usuário:** {usuario}\n🏢 **Nome/Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {at_descricao}\n📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{jira_str}")
    chat_message = {"text": msg}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_REGISTRO, chat_message)).start()
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
      --y: -30vmin; --x: -50%; --initialY: 60vmin;
      content: ""; animation: firework 2s infinite; position: absolute; top: 50%; left: 50%; transform: translate(-50%, var(--y)); width: var(--initialSize); aspect-ratio: 1;
      background: radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 50% 100%, radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 0% 50%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 80% 90%, radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 95% 90%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 90% 70%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 60%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 55% 80%, radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 70% 77%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 22% 90%, radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 45% 90%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 33% 70%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 10% 60%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 31% 80%, radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 28% 77%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 13% 72%, radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 80% 10%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 95% 14%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 90% 23%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 100% 43%, radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 85% 27%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 77% 37%, radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 60% 7%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 22% 14%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 45% 20%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 33% 34%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 10% 29%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 31% 37%, radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 28% 7%;
      background-size: var(--initialSize) var(--initialSize); background-repeat: no-repeat;
    }
    .firework::before { --x: -50%; --y: -50%; --initialY: -50%; transform: translate(-50%, -50%) rotate(40deg) scale(1.3) rotateY(40deg); }
    .firework::after { --x: -50%; --y: -50%; --initialY: -50%; transform: translate(-50%, -50%) rotate(170deg) scale(1.15) rotateY(-30deg); }
    .firework:nth-child(2) { --x: 30vmin; }
    .firework:nth-child(2), .firework:nth-child(2)::before, .firework:nth-child(2)::after { --color1: #ff0000; --color2: #ffd700; --color3: #8b0000; --color4: #daa520; --color5: #ff6347; --color6: #f0e68c; --finalSize: 40vmin; left: 30%; top: 60%; animation-delay: -0.25s; }
    .firework:nth-child(3) { --x: -30vmin; --y: -50vmin; }
    .firework:nth-child(3), .firework:nth-child(3)::before, .firework:nth-child(3)::after { --color1: #ffd700; --color2: #ff4500; --color3: #b8860b; --color4: #cd5c5c; --color5: #800000; --color6: #ffa500; --finalSize: 35vmin; left: 70%; top: 60%; animation-delay: -0.4s; }
    </style>
    <div class="firework"></div><div class="firework"></div><div class="firework"></div>
    """
    st.markdown(fireworks_css, unsafe_allow_html=True)

def gerar_html_checklist(consultor_nome, camara_nome, data_sessao_formatada):
    consultor_formatado = f"@{consultor_nome}" if not consultor_nome.startswith("@") else consultor_nome
    html_template = f"""
<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8"><title>Acompanhamento de Sessão - {camara_nome}</title></head>
<body><div style="font-family: Arial, sans-serif; padding: 20px;"><h2>Checklist Gerado para {camara_nome}</h2><p>Responsável: {consultor_formatado}</p><p>Data: {data_sessao_formatada}</p><p><em>(Versão simplificada para visualização.)</em></p></div></body></html>
    """
    return html_template

def send_sessao_to_chat(consultor, texto_mensagem):
    if not GOOGLE_CHAT_WEBHOOK_SESSAO: return False
    if not consultor or consultor == 'Selecione um nome': return False
    chat_message = {'text': texto_mensagem}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_SESSAO, chat_message)).start()
    return True

def send_daily_report(): 
    logs = load_logs() 
    bastao_counts = st.session_state.bastao_counts.copy()
    aggregated_data = {nome: {} for nome in CONSULTORES}
    for log in logs:
        try:
            consultor = log['consultor']; status = log['old_status']; duration = log.get('duration', timedelta(0))
            if not isinstance(duration, timedelta):
                try: duration = timedelta(seconds=float(duration))
                except: duration = timedelta(0)
            if status and consultor in aggregated_data:
                current_duration = aggregated_data[consultor].get(status, timedelta(0))
                aggregated_data[consultor][status] = current_duration + duration
        except: pass

    today_str = datetime.now().strftime("%d/%m/%Y")
    report_text = f"📊 **Relatório Diário de Atividades - {today_str}** 📊\n\n"
    consultores_com_dados = []
    for nome in CONSULTORES:
        counts = bastao_counts.get(nome, 0); times = aggregated_data.get(nome, {}); bastao_time = times.get('Bastão', timedelta(0))
        if counts > 0 or times:
            consultores_com_dados.append(nome)
            report_text += f"**👤 {nome}**\n- {BASTAO_EMOJI} Bastão Recebido: **{counts}** vez(es)\n- ⏱️ Tempo com Bastão: **{format_time_duration(bastao_time)}**\n"
            other_statuses = []; sorted_times = sorted(times.items(), key=itemgetter(0)) 
            for status, time in sorted_times:
                if status != 'Bastão' and status: other_statuses.append(f"{status}: **{format_time_duration(time)}**")
            if other_statuses: report_text += f"- ⏳ Outros Tempos: {', '.join(other_statuses)}\n\n"
            else: report_text += "\n"
    if not consultores_com_dados: report_text = f"📊 **Relatório Diário - {today_str}** 📊\n\nNenhuma atividade registrada hoje."
    if not GOOGLE_CHAT_WEBHOOK_BACKUP: return 
    chat_message = {'text': report_text}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_BACKUP, chat_message)).start()
    st.session_state['report_last_run_date'] = datetime.now(); st.session_state['daily_logs'] = []; st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
    save_state()

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
        st.session_state.bastao_counts.setdefault(nome, 0)
        st.session_state.skip_flags.setdefault(nome, False)
        current_status = st.session_state.status_texto.get(nome, 'Indisponível') 
        st.session_state.status_texto.setdefault(nome, current_status)
        is_available = (current_status == 'Bastão' or current_status == '') and nome not in st.session_state.priority_return_queue
        st.session_state[f'check_{nome}'] = is_available
        if nome not in st.session_state.current_status_starts: st.session_state.current_status_starts[nome] = datetime.now()

    checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
    if not st.session_state.bastao_queue and checked_on: st.session_state.bastao_queue = sorted(list(checked_on))
    check_and_assume_baton()

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    num_consultores = len(queue)
    if num_consultores == 0: return -1
    if current_index >= num_consultores or current_index < -1: current_index = -1
    next_idx = (current_index + 1) % num_consultores
    attempts = 0
    while attempts < num_consultores:
        consultor = queue[next_idx]
        if not skips.get(consultor, False) and st.session_state.get(f'check_{consultor}'): return next_idx
        next_idx = (next_idx + 1) % num_consultores
        attempts += 1
    return -1

def check_and_assume_baton():
    queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    is_current_valid = (current_holder_status and current_holder_status in queue and st.session_state.get(f'check_{current_holder_status}'))
    first_eligible_index = find_next_holder_index(-1, queue, skips)
    first_eligible_holder = queue[first_eligible_index] if first_eligible_index != -1 else None
    
    should_have_baton = current_holder_status if is_current_valid else first_eligible_holder
    changed = False; previous_holder = current_holder_status 

    for c in CONSULTORES:
        if c != should_have_baton and st.session_state.status_texto.get(c) == 'Bastão':
            duration = datetime.now() - st.session_state.current_status_starts.get(c, datetime.now())
            log_status_change(c, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[c] = 'Indisponível'; changed = True

    if should_have_baton and st.session_state.status_texto.get(should_have_baton) != 'Bastão':
        old_status = st.session_state.status_texto.get(should_have_baton, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(should_have_baton, datetime.now())
        log_status_change(should_have_baton, old_status, 'Bastão', duration)
        st.session_state.status_texto[should_have_baton] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        if previous_holder != should_have_baton: 
            st.session_state.play_sound = True; send_chat_notification_internal(should_have_baton, 'Bastão') 
        if st.session_state.skip_flags.get(should_have_baton): st.session_state.skip_flags[should_have_baton] = False
        changed = True
    elif not should_have_baton:
        if current_holder_status:
            duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
            log_status_change(current_holder_status, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[current_holder_status] = 'Indisponível'; changed = True
        st.session_state.bastao_start_time = None
    if changed: save_state()
    return changed

def update_queue(consultor):
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None; st.session_state.lunch_warning_info = None 
    is_checked = st.session_state.get(f'check_{consultor}'); old_status_text = st.session_state.status_texto.get(consultor, '')
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())

    if is_checked: 
        log_status_change(consultor, old_status_text or 'Indisponível', '', duration)
        st.session_state.status_texto[consultor] = '' 
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor) 
        st.session_state.skip_flags[consultor] = False 
        if consultor in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(consultor)
    else: 
        if old_status_text not in STATUSES_DE_SAIDA and old_status_text != 'Bastão':
            log_status_change(consultor, old_status_text , 'Indisponível', duration)
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
    eligible_in_queue = [p for p in queue if st.session_state.get(f'check_{p}')]
    if len(eligible_in_queue) > 1 and all(skips.get(p, False) for p in eligible_in_queue if p != current_holder):
        for c in queue: st.session_state.skip_flags[c] = False
        skips = st.session_state.skip_flags; st.toast("Ciclo reiniciado!", icon="🔄")
    next_idx = find_next_holder_index(current_index, queue, skips)
    if next_idx != -1:
        next_holder = queue[next_idx]
        skipped_over = queue[current_index+1 : next_idx] if next_idx > current_index else queue[current_index+1:] + queue[:next_idx]
        for person in skipped_over: st.session_state.skip_flags[person] = False 
        st.session_state.skip_flags[next_holder] = False
        duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        log_status_change(current_holder, 'Bastão', '', duration); st.session_state.status_texto[current_holder] = '' 
        log_status_change(next_holder, st.session_state.status_texto.get(next_holder, ''), 'Bastão', timedelta(0))
        st.session_state.status_texto[next_holder] = 'Bastão'; st.session_state.bastao_start_time = datetime.now()
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True; st.session_state.rotation_gif_start_time = datetime.now(); send_chat_notification_internal(next_holder, 'Bastão'); save_state()
    else: st.warning('Não há próximo(a) elegível.'); check_and_assume_baton() 

def toggle_skip(): 
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None; st.session_state.lunch_warning_info = None 
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    if not st.session_state.get(f'check_{selected}'): st.warning(f'{selected} não está disponível.'); return
    st.session_state.skip_flags[selected] = not st.session_state.skip_flags.get(selected, False)
    if selected == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None) and st.session_state.skip_flags[selected]:
        save_state(); rotate_bastao(); return 
    save_state() 

def update_status(status_text, change_to_available=False): 
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    if status_text != 'Almoço': st.session_state.lunch_warning_info = None
    
    is_second_try = False
    if st.session_state.get('lunch_warning_info') and st.session_state.get('lunch_warning_info').get('consultor') == selected:
        if (datetime.now() - st.session_state.lunch_warning_info.get('start_time', datetime.min)).total_seconds() < 30: is_second_try = True 

    if status_text == 'Almoço' and not is_second_try:
        all_s = st.session_state.status_texto; ativos = sum(1 for s in all_s.values() if s in ['', 'Bastão', 'Atendimento'])
        if ativos > 0 and sum(1 for s in all_s.values() if s == 'Almoço') >= (ativos / 2.0):
            st.session_state.lunch_warning_info = {'consultor': selected, 'start_time': datetime.now(), 'message': f'Metade ativa já em almoço. Clique novamente para confirmar.'}
            save_state(); return 
            
    st.session_state.lunch_warning_info = None; st.session_state[f'check_{selected}'] = False 
    was_holder = (st.session_state.status_texto.get(selected) == 'Bastão')
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if was_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, old_status, status_text, duration); st.session_state.status_texto[selected] = status_text 
    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skip_flags.pop(selected, None)
    if status_text == 'Saída rápida':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)
    if was_holder: check_and_assume_baton()
    else: save_state() 

def manual_rerun(): st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None; st.rerun() 
def on_auxilio_change(): save_state()

def handle_sessao_submission(consultor_sel, camara_sel, data_obj):
    if not data_obj: st.error("Selecione uma data."); return False
    df = data_obj.strftime("%d/%m/%Y"); dfa = data_obj.strftime("%d-%m-%Y"); email = CAMARAS_DICT.get(camara_sel, "")
    nc = consultor_sel if consultor_sel and consultor_sel != "Selecione um nome" else "[NOME]"
    msg = (f"Prezada equipe do {camara_sel},\n\nMeu nome é {nc}, sou assistente CESUPE/TJMG e serei responsável pelo acompanhamento técnico da sessão de {df}...\n\nEmail do setor: {email}")
    if send_sessao_to_chat(consultor_sel, msg):
        st.session_state.last_reg_status = "success_sessao"; st.session_state.html_content_cache = gerar_html_checklist(consultor_sel, camara_sel, df); st.session_state.html_download_ready = True; st.session_state.html_filename = f"Checklist_{dfa}.html"
        return True
    st.session_state.last_reg_status = "error_sessao"; return False

def set_chamado_step(step_num): st.session_state.chamado_guide_step = step_num
def handle_chamado_submission(): 
    st.toast("Chamado simulado.", icon="✅"); st.session_state.last_reg_status = "success_chamado"; st.session_state.chamado_guide_step = 0; st.session_state.chamado_textarea = ""

def handle_horas_extras_submission(consultor_sel, data, inicio, tempo, motivo):
    if not consultor_sel or consultor_sel == "Selecione um nome": st.error("Selecione um consultor."); return
    if send_horas_extras_to_chat(consultor_sel, data, inicio, tempo, motivo):
        st.success("Registrado!"); st.session_state.active_view = None; time.sleep(1); st.rerun()
    else: st.error("Erro no Webhook.")

def handle_atendimento_submission(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    if not consultor or consultor == "Selecione um nome": st.error("Selecione um consultor."); return
    if send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional):
        st.success("Registrado!"); st.session_state.active_view = None; time.sleep(1); st.rerun()
    else: st.error("Erro no Webhook.")

# ============================================
# 3. LÓGICA DO JOGO SIMON
# ============================================

def handle_simon_game():
    COLORS = ["🔴", "🔵", "🟢", "🟡"]
    st.markdown("### 🧠 Simon Game"); st.caption("Repita a sequência!")
    if st.session_state.simon_status == 'start':
        if st.button("▶️ Iniciar Jogo", use_container_width=True):
            st.session_state.simon_sequence = [random.choice(COLORS)]; st.session_state.simon_user_input = []; st.session_state.simon_level = 1; st.session_state.simon_status = 'showing'; st.rerun()
    elif st.session_state.simon_status == 'showing':
        st.info(f"Nível {st.session_state.simon_level}: Memorize!"); cols = st.columns(len(st.session_state.simon_sequence))
        for i, color in enumerate(st.session_state.simon_sequence):
            with cols[i]: st.markdown(f"<h1 style='text-align: center;'>{color}</h1>", unsafe_allow_html=True)
        if st.button("🙈 Responder", type="primary", use_container_width=True): st.session_state.simon_status = 'playing'; st.rerun()
    elif st.session_state.simon_status == 'playing':
        st.markdown(f"**Nível {st.session_state.simon_level}**"); c1, c2, c3, c4 = st.columns(4); pressed = None
        if c1.button("🔴", use_container_width=True): pressed = "🔴"
        if c2.button("🔵", use_container_width=True): pressed = "🔵"
        if c3.button("🟢", use_container_width=True): pressed = "🟢"
        if c4.button("🟡", use_container_width=True): pressed = "🟡"
        if pressed:
            st.session_state.simon_user_input.append(pressed); current_idx = len(st.session_state.simon_user_input) - 1
            if st.session_state.simon_user_input[current_idx] != st.session_state.simon_sequence[current_idx]: st.session_state.simon_status = 'lost'; st.rerun()
            elif len(st.session_state.simon_user_input) == len(st.session_state.simon_sequence):
                st.success("Correto!"); time.sleep(0.5); st.session_state.simon_sequence.append(random.choice(COLORS)); st.session_state.simon_user_input = []; st.session_state.simon_level += 1; st.session_state.simon_status = 'showing'; st.rerun()
        if st.session_state.simon_user_input: st.markdown(f"Resposta: {' '.join(st.session_state.simon_user_input)}")
    elif st.session_state.simon_status == 'lost':
        st.error(f"❌ Nível {st.session_state.simon_level}"); st.markdown(f"Correto: {' '.join(st.session_state.simon_sequence)}")
        consultor = st.session_state.consultor_selectbox
        if consultor and consultor != 'Selecione um nome':
            score = st.session_state.simon_level; ranking = st.session_state.simon_ranking; found = False
            for entry in ranking:
                if entry['nome'] == consultor:
                    if score > entry['score']: entry['score'] = score
                    found = True; break
            if not found: ranking.append({'nome': consultor, 'score': score})
            st.session_state.simon_ranking = sorted(ranking, key=lambda x: x['score'], reverse=True)[:5]; save_state(); st.success(f"Score salvo!")
        if st.button("Tentar Novamente"): st.session_state.simon_status = 'start'; st.rerun()
    st.markdown("---"); st.subheader("🏆 Ranking Global"); ranking = st.session_state.simon_ranking
    if not ranking: st.markdown("_Sem recordes._")
    else: st.table(pd.DataFrame(ranking))

# ============================================
# 4. EXECUÇÃO PRINCIPAL
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
render_fireworks()

c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img_data = get_img_as_base64(PUG2026_FILENAME); img_src = f"data:image/png;base64,{img_data}" if img_data else GIF_BASTAO_HOLDER
    st.markdown(f'<div style="display: flex; align-items: center; gap: 15px;"><h1 style="margin: 0; font-size: 2.2rem; color: #FFD700; text-shadow: 1px 1px 2px #B8860B;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{img_src}" style="width: 120px; height: 120px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;"></div>', unsafe_allow_html=True)

with c_topo_dir:
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_sub1: novo_responsavel = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
    with c_sub2:
        if st.button("🚀 Entrar"):
            if novo_responsavel and novo_responsavel != "Selecione":
                st.session_state[f'check_{novo_responsavel}'] = True; update_queue(novo_responsavel); st.session_state.consultor_selectbox = novo_responsavel; st.success("Na fila!"); st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True) 

gif_start_time = st.session_state.get('rotation_gif_start_time'); lunch_warning_info = st.session_state.get('lunch_warning_info') 
show_gif = False; show_lunch_warning = False; refresh_interval = 8000 

if gif_start_time and (datetime.now() - gif_start_time).total_seconds() < 20: show_gif = True; refresh_interval = 2000 
if lunch_warning_info and lunch_warning_info.get('start_time') and (datetime.now() - lunch_warning_info['start_time']).total_seconds() < 30: show_lunch_warning = True; refresh_interval = 2000 
        
st_autorefresh(interval=refresh_interval, key='auto_rerun_key') 
if st.session_state.get('play_sound', False): st.components.v1.html(play_sound_html(), height=0, width=0); st.session_state.play_sound = False 
if show_gif: st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')
if show_lunch_warning: st.warning(f"🔔 **{lunch_warning_info['message']}**"); st.image(GIF_URL_LUNCH_WARNING, width=200)
if st.session_state.get('gif_warning', False): st.error('🚫 Inválido!'); st.image(GIF_URL_WARNING, width=150)

col_principal, col_disponibilidade = st.columns([1.5, 1])
queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags; responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
current_index = queue.index(responsavel) if responsavel in queue else -1; proximo_index = find_next_holder_index(current_index, queue, skips); proximo = queue[proximo_index] if proximo_index != -1 else None
restante = []
if proximo_index != -1: 
    num_q = len(queue); cur = (proximo_index + 1) % num_q; checked = 0
    while checked < num_q:
        if cur == (proximo_index + 1) % num_q and checked > 0: break
        c = queue[cur]
        if c not in [responsavel, proximo] and not skips.get(c, False) and st.session_state.get(f'check_{c}'): restante.append(c)
        cur = (cur + 1) % num_q; checked += 1

with col_principal:
    st.header("Responsável pelo Bastão")
    if responsavel:
        st.markdown(f'<div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%); border: 3px solid #FFD700; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3); margin-bottom: 20px;"><div style="flex-shrink: 0; margin-right: 25px;"><img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #FFD700;"></div><div><span style="font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px;">Atualmente com:</span><br><span style="font-size: 42px; font-weight: 800; color: #000080; line-height: 1.1;">{responsavel}</span></div></div>', unsafe_allow_html=True)
        dur = datetime.now() - st.session_state.bastao_start_time if st.session_state.bastao_start_time else timedelta(0)
        st.caption(f"⏱️ Tempo: **{format_time_duration(dur)}**")
    else: st.markdown('<h2>(Ninguém)</h2>', unsafe_allow_html=True)
    st.header("Próximos da Fila")
    if proximo: st.markdown(f'### 1º: **{proximo}**')
    if restante: st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    skipped = [c for c, is_sk in skips.items() if is_sk and st.session_state.get(f'check_{c}')]
    if skipped: st.markdown(f'<div style="margin-top: 15px;"><span style="color: #FFC107; font-weight: bold;">Pulou:</span><br>{", ".join(sorted(skipped))} pulou o bastão!</div>', unsafe_allow_html=True)
    
    st.header("**Consultor(a)**")
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("**Ações:**")
    
    def toggle_view(view_name): st.session_state.active_view = view_name if st.session_state.active_view != view_name else None; (setattr(st.session_state, 'chamado_guide_step', 1) if view_name == 'chamados' else None)

    # AJUSTE: 8 Colunas para incluir Projeto
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8) 
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True)
    c3.button('📋 Ativ.', on_click=toggle_view, args=('menu_atividades',), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=update_status, args=('Almoço',), use_container_width=True)
    c5.button('👤 Ausent', on_click=update_status, args=('Ausente',), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=lambda: update_status("Sessão"), use_container_width=True)
    c7.button('🚶 Saída', on_click=update_status, args=('Saída rápida',), use_container_width=True)
    c8.button('🚀 Projeto', on_click=toggle_view, args=('menu_projetos',), use_container_width=True) # Novo Botão

    # MODAL PROJETOS
    if st.session_state.active_view == 'menu_projetos':
        with st.container(border=True):
            st.markdown("### Selecionar Projeto")
            proj_sel = st.selectbox("Escolha o projeto:", PROJETOS_OPCOES)
            if st.button("Confirmar Projeto", type="primary", use_container_width=True):
                update_status(f"Projeto: {proj_sel}"); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            st.markdown("### Selecione a Atividade")
            atv_sel = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS)
            if st.button("Confirmar Atividade", type="primary", use_container_width=True):
                if atv_sel: update_status(f"Atividade: {', '.join(atv_sel)}"); st.session_state.active_view = None; st.rerun()
                else: st.warning("Selecione uma atividade.")
    
    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)
    st.markdown("---")
    c_tool1, c_tool2, c_tool3, c_tool4, c_tool5 = st.columns(5)
    c_tool1.button("📑 Checklist", use_container_width=True, on_click=toggle_view, args=("checklist",))
    c_tool2.button("🆘 Chamados", use_container_width=True, on_click=toggle_view, args=("chamados",))
    c_tool3.button("📝 Atend.", use_container_width=True, on_click=toggle_view, args=("atendimentos",))
    c_tool4.button("⏰ H.Extras", use_container_width=True, on_click=toggle_view, args=("hextras",))
    c_tool5.button("🧠 Descanso", use_container_width=True, on_click=toggle_view, args=("descanso",))

    if st.session_state.active_view == "checklist":
        with st.container(border=True):
            st.header("Gerador Checklist"); data_ep = st.date_input("Data Sessão:"); cam_ep = st.selectbox("Câmara:", CAMARAS_OPCOES)
            if st.button("Gerar/Enviar"):
                if st.session_state.consultor_selectbox != 'Selecione um nome': handle_sessao_submission(st.session_state.consultor_selectbox, cam_ep, data_ep)
    elif st.session_state.active_view == "atendimentos":
        with st.container(border=True):
            st.markdown("### Novo Atendimento"); at_u = st.selectbox("Usuário:", REG_USUARIO_OPCOES); at_s = st.text_input("Setor:"); at_sys = st.selectbox("Sistema:", REG_SISTEMA_OPCOES); at_desc = st.text_input("Descrição:"); at_c = st.selectbox("Canal:", REG_CANAL_OPCOES); at_d = st.selectbox("Desfecho:", REG_DESFECHO_OPCOES); at_j = st.text_input("Jira:")
            if st.button("Enviar"): handle_atendimento_submission(st.session_state.consultor_selectbox, date.today(), at_u, at_s, at_sys, at_desc, at_c, at_d, at_j)
    elif st.session_state.active_view == "descanso": handle_simon_game()

with col_disponibilidade:
    st.markdown("###"); st.toggle("Auxílio HP/Emails", key='auxilio_ativo', on_change=on_auxilio_change)
    if st.session_state.get('auxilio_ativo'): st.warning("HP/Emails para bastão"); st.image(GIF_URL_NEDRY, width=300)
    st.markdown("---"); st.header('Status dos Consultores')
    ui_lists = {'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade': [], 'sessao': [], 'projeto': [], 'indisponivel': []} 
    for nome in CONSULTORES:
        st_txt = st.session_state.status_texto.get(nome, 'Indisponível')
        if st_txt == 'Bastão': ui_lists['fila'].insert(0, nome)
        elif st_txt == '': ui_lists['fila'].append(nome)
        elif st_txt == 'Almoço': ui_lists['almoco'].append(nome)
        elif st_txt == 'Ausente': ui_lists['ausente'].append(nome)
        elif st_txt == 'Saída rápida': ui_lists['saida'].append(nome)
        elif st_txt.startswith('Projeto:'): ui_lists['projeto'].append((nome, st_txt.replace('Projeto: ', '')))
        elif st_txt.startswith('Sessão'): ui_lists['sessao'].append((nome, st_txt.replace('Sessão: ', '')))
        elif st_txt.startswith('Atividade') or st_txt == 'Atendimento': ui_lists['atividade'].append((nome, st_txt.replace('Atividade: ', '')))
        else: ui_lists['indisponivel'].append(nome)

    st.subheader(f'✅ Na Fila ({len(ui_lists["fila"])})')
    for nome in [c for c in queue if c in ui_lists['fila']] + [c for c in ui_lists['fila'] if c not in queue]:
        c_n, c_c = st.columns([0.8, 0.2]); c_c.checkbox(' ', key=f'check_{nome}', on_change=update_queue, args=(nome,), label_visibility='collapsed')
        if nome == responsavel: c_n.markdown(f'<span style="background-color: #FFD700; color: #000; padding: 2px 6px; border-radius: 5px; font-weight: bold;">🥂 {nome}</span>', unsafe_allow_html=True)
        elif skips.get(nome): c_n.markdown(f'**{nome}** :orange-background[Pulando ⏭️]')
        else: c_n.markdown(f'**{nome}** :blue-background[Aguardando]')
    
    st.markdown('---')
    # SEÇÃO PROJETOS NA BARRA LATERAL
    st.subheader(f'🚀 Em Projeto ({len(ui_lists["projeto"])})')
    if not ui_lists['projeto']: st.markdown('_Nenhum projeto ativo._')
    else:
        for nome, proj in sorted(ui_lists['projeto']):
            c_n, c_c = st.columns([0.8, 0.2]); c_c.checkbox(' ', key=f'check_{nome}', value=False, on_change=update_queue, args=(nome,), label_visibility='collapsed')
            c_n.markdown(f'**{nome}** :blue-background[{proj}]', unsafe_allow_html=True)
    st.markdown('---')

    st.subheader(f'📋 Atividades ({len(ui_lists["atividade"])})')
    for nome, dsc in sorted(ui_lists['atividade']):
        c_n, c_c = st.columns([0.8, 0.2]); c_c.checkbox(' ', key=f'check_{nome}', value=False, on_change=update_queue, args=(nome,), label_visibility='collapsed')
        c_n.markdown(f'**{nome}** :orange-background[{dsc}]')
    
    st.markdown('---')
    def rnd_sec(t, i, n, cl):
        st.subheader(f'{i} {t} ({len(n)})')
        if n:
            for nm in sorted(n):
                c_n, c_c = st.columns([0.8, 0.2]); c_c.checkbox(' ', key=f'check_{nm}', value=False, on_change=update_queue, args=(nm,), label_visibility='collapsed')
                c_n.markdown(f'**{nm}** :{cl}-background[{t}]')
        else: st.markdown(f'_Vazio_'); st.markdown('---')

    rnd_sec('Almoço', '🍽️', ui_lists['almoco'], 'red')
    rnd_sec('Saída rápida', '🚶', ui_lists['saida'], 'red')
    rnd_sec('Ausente', '👤', ui_lists['ausente'], 'violet')
    rnd_sec('Indisponível', '❌', ui_lists['indisponivel'], 'grey')

now_br = datetime.utcnow() - timedelta(hours=3)
if now_br.hour >= 20 and now_br.date() > (st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()):
    send_daily_report()
