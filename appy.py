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
        # --- Ranking Global do Jogo ---
        'simon_ranking': [] # Lista de dicts: {'nome': str, 'score': int}
    }

# --- Constantes (Webhooks) ---
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k" 
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
WEBHOOK_ERROS = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"

LISTA_PROJETOS = ["Projeto Soma", "Manuais Eproc", "Treinamentos Eproc", "IA nos Cartórios", "Notebook Lm"]

TEMPLATE_ERRO = """TITULO: 
OBJETIVO: 
RELATO DO ERRO/TESTE: 
RESULTADO: 
OBSERVAÇÃO (SE TIVER): """

EXEMPLO_TEXTO = """**TITULO** - Melhoria na Gestão das Procuradorias
**OBJETIVO**
Permitir que os perfis de Procurador Chefe e Gerente de Procuradoria possam gerenciar os usuários das procuradorias...
**RELATO DO TESTE**
Foram realizados testes no menu “Gerenciar Procuradores”...
**RESULTADO**
O teste não foi bem-sucedido: erro ao cadastrar novos usuários."""

# Listas para o formulário de atendimento
REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]

# Dados das Câmaras
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
BASTAO_EMOJI = "??" 
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
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro no envio assíncrono: {e}")

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        message_template = "?? **BASTÃO GIRADO!** ?? \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {app_url}"
        message_text = message_template.format(consultor=consultor, app_url=APP_URL_CLOUD) 
        chat_message = {"text": message_text}
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, chat_message)).start()
        return True
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    if not GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS: return False
    data_formatada = data.strftime("%d/%m/%Y")
    inicio_formatado = inicio.strftime("%H:%M")
    msg = (
        f"? **Registro de Horas Extras**\n\n"
        f"?? **Consultor:** {consultor}\n"
        f"?? **Data:** {data_formatada}\n"
        f"?? **Início:** {inicio_formatado}\n"
        f"?? **Tempo Total:** {tempo}\n"
        f"?? **Motivo:** {motivo}"
    )
    chat_message = {"text": msg}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS, chat_message)).start()
    return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO: return False
    data_formatada = data.strftime("%d/%m/%Y")
    jira_str = f"\n?? **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = (
        f"?? **Novo Registro de Atendimento**\n\n"
        f"?? **Consultor:** {consultor}\n"
        f"?? **Data:** {data_formatada}\n"
        f"?? **Usuário:** {usuario}\n"
        f"?? **Nome/Setor:** {nome_setor}\n"
        f"?? **Sistema:** {sistema}\n"
        f"?? **Descrição:** {descricao}\n"
        f"?? **Canal:** {canal}\n"
        f"? **Desfecho:** {desfecho}"
        f"{jira_str}"
    )
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
    .firework,
    .firework::before,
    .firework::after {
      --initialSize: 0.5vmin;
      --finalSize: 45vmin;
      --particleSize: 0.2vmin;
      --color1: #ff0000;
      --color2: #ffd700;
      --color3: #b22222;
      --color4: #daa520;
      --color5: #ff4500;
      --color6: #b8860b;
      --y: -30vmin;
      --x: -50%;
      --initialY: 60vmin;
      content: "";
      animation: firework 2s infinite;
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, var(--y));
      width: var(--initialSize);
      aspect-ratio: 1;
      background: 
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%,
        radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%,
        radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 50% 100%,
        radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 0% 50%,
        radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 80% 90%,
        radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 95% 90%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 90% 70%,
        radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 60%,
        radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 55% 80%,
        radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 70% 77%,
        radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 22% 90%,
        radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 45% 90%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 33% 70%,
        radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 10% 60%,
        radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 31% 80%,
        radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 28% 77%,
        radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 13% 72%,
        radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 80% 10%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 95% 14%,
        radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 90% 23%,
        radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 100% 43%,
        radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 85% 27%,
        radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 77% 37%,
        radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 60% 7%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 22% 14%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 45% 20%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 33% 34%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 10% 29%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 31% 37%,
        radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 28% 7%;
      background-size: var(--initialSize) var(--initialSize);
      background-repeat: no-repeat;
    }
    .firework::before {
      --x: -50%;
      --y: -50%;
      --initialY: -50%;
      transform: translate(-50%, -50%) rotate(40deg) scale(1.3) rotateY(40deg);
    }
    .firework::after {
      --x: -50%;
      --y: -50%;
      --initialY: -50%;
      transform: translate(-50%, -50%) rotate(170deg) scale(1.15) rotateY(-30deg);
    }
    .firework:nth-child(2) {
      --x: 30vmin;
    }
    .firework:nth-child(2),
    .firework:nth-child(2)::before,
    .firework:nth-child(2)::after {
      --color1: #ff0000;
      --color2: #ffd700;
      --color3: #8b0000;
      --color4: #daa520;
      --color5: #ff6347;
      --color6: #f0e68c;  
      --finalSize: 40vmin;
      left: 30%;
      top: 60%;
      animation-delay: -0.25s;
    }
    .firework:nth-child(3) {
      --x: -30vmin;
      --y: -50vmin;
    }
    .firework:nth-child(3),
    .firework:nth-child(3)::before,
    .firework:nth-child(3)::after {
      --color1: #ffd700;
      --color2: #ff4500;
      --color3: #b8860b;
      --color4: #cd5c5c;
      --color5: #800000;
      --color6: #ffa500;
      --finalSize: 35vmin;
      left: 70%;
      top: 60%;
      animation-delay: -0.4s;
    }
    </style>
    <div class="firework"></div>
    <div class="firework"></div>
    <div class="firework"></div>
    """
    st.markdown(fireworks_css, unsafe_allow_html=True)

def gerar_html_checklist(consultor_nome, camara_nome, data_sessao_formatada):
    consultor_formatado = f"@{consultor_nome}" if not consultor_nome.startswith("@") else consultor_nome
    html_template = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="UTF-8"><title>Acompanhamento de Sessão - {camara_nome}</title></head>
<body><div style="font-family: Arial, sans-serif; padding: 20px;"><h2>Checklist para {camara_nome}</h2><p>Responsável: {consultor_formatado}</p><p>Data: {data_sessao_formatada}</p></div></body>
</html>"""
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
            consultor = log['consultor']
            status = log['old_status']
            duration = log.get('duration', timedelta(0))
            if not isinstance(duration, timedelta):
                try: duration = timedelta(seconds=float(duration))
                except: duration = timedelta(0)
            if status and consultor in aggregated_data:
                current_duration = aggregated_data[consultor].get(status, timedelta(0))
                aggregated_data[consultor][status] = current_duration + duration
        except: pass

    today_str = datetime.now().strftime("%d/%m/%Y")
    report_text = f"?? **Relatório Diário de Atividades - {today_str}** ??\n\n"
    
    for nome in CONSULTORES:
        counts = bastao_counts.get(nome, 0)
        times = aggregated_data.get(nome, {})
        bastao_time = times.get('Bastão', timedelta(0))
        if counts > 0 or times:
            report_text += f"**?? {nome}**\n"
            report_text += f"- {BASTAO_EMOJI} Bastão Recebido: **{counts}** vez(es)\n"
            report_text += f"- ?? Tempo com Bastão: **{format_time_duration(bastao_time)}**\n"
            other_statuses = [f"{s}: **{format_time_duration(t)}**" for s, t in sorted(times.items()) if s != 'Bastão']
            if other_statuses: report_text += f"- ? Outros: {', '.join(other_statuses)}\n\n"
            else: report_text += "\n"

    if GOOGLE_CHAT_WEBHOOK_BACKUP:
        threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_BACKUP, {'text': report_text})).start()
    
    st.session_state['report_last_run_date'] = datetime.now()
    st.session_state['daily_logs'] = []
    st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
    save_state()

def init_session_state():
    persisted_state = load_state()
    defaults = {
        'bastao_start_time': None, 
        'report_last_run_date': datetime.min, 
        'rotation_gif_start_time': None,
        'play_sound': False,
        'gif_warning': False,
        'lunch_warning_info': None,
        'last_reg_status': None, 
        'chamado_guide_step': 0, 
        'sessao_msg_preview': "", 
        'html_download_ready': False, 
        'html_content_cache': "", 
        'auxilio_ativo': False,
        'active_view': None, 
        'last_jira_number': "",
        'simon_sequence': [],
        'simon_user_input': [],
        'simon_status': 'start',
        'simon_level': 1
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = persisted_state.get(key, default)

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
        if nome not in st.session_state.current_status_starts:
                  st.session_state.current_status_starts[nome] = datetime.now()

    checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
    if not st.session_state.bastao_queue and checked_on:
        st.session_state.bastao_queue = sorted(list(checked_on))

    check_and_assume_baton()

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    num = len(queue)
    next_idx = (current_index + 1) % num
    attempts = 0
    while attempts < num:
        consultor = queue[next_idx]
        if not skips.get(consultor, False) and st.session_state.get(f'check_{consultor}'):
            return next_idx
        next_idx = (next_idx + 1) % num
        attempts += 1
    return -1

def check_and_assume_baton():
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    is_current_valid = (current_holder_status and current_holder_status in queue and st.session_state.get(f'check_{current_holder_status}'))
    first_eligible_index = find_next_holder_index(-1, queue, skips)
    first_eligible_holder = queue[first_eligible_index] if first_eligible_index != -1 else None
    
    should_have_baton = current_holder_status if is_current_valid else first_eligible_holder
    changed = False

    for c in CONSULTORES:
        if c != should_have_baton and st.session_state.status_texto.get(c) == 'Bastão':
            duration = datetime.now() - st.session_state.current_status_starts.get(c, datetime.now())
            log_status_change(c, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[c] = 'Indisponível'
            changed = True

    if should_have_baton and st.session_state.status_texto.get(should_have_baton) != 'Bastão':
        old_status = st.session_state.status_texto.get(should_have_baton, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(should_have_baton, datetime.now())
        log_status_change(should_have_baton, old_status, 'Bastão', duration)
        st.session_state.status_texto[should_have_baton] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.play_sound = True 
        send_chat_notification_internal(should_have_baton, 'Bastão') 
        st.session_state.skip_flags[should_have_baton] = False
        changed = True
    elif not should_have_baton:
        if current_holder_status:
            duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
            log_status_change(current_holder_status, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[current_holder_status] = 'Indisponível' 
            changed = True
        st.session_state.bastao_start_time = None

    if changed: save_state()
    return changed

def update_queue(consultor):
    st.session_state.gif_warning = False
    st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    is_checked = st.session_state.get(f'check_{consultor}') 
    old_status_text = st.session_state.status_texto.get(consultor, '')
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())

    if is_checked: 
        log_status_change(consultor, old_status_text or 'Indisponível', '', duration)
        st.session_state.status_texto[consultor] = '' 
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor) 
        st.session_state.skip_flags[consultor] = False 
    else: 
        if old_status_text not in STATUSES_DE_SAIDA and old_status_text != 'Bastão':
            log_status_change(consultor, old_status_text , 'Indisponível', duration)
            st.session_state.status_texto[consultor] = 'Indisponível' 
        if consultor in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(consultor)
        st.session_state.skip_flags.pop(consultor, None) 
        
    if not check_and_assume_baton(): save_state()

def rotate_bastao(): 
    selected = st.session_state.consultor_selectbox
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder:
        st.session_state.gif_warning = True
        return 

    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_index = queue.index(current_holder) if current_holder in queue else -1
    next_idx = find_next_holder_index(current_index, queue, skips)

    if next_idx != -1:
        next_holder = queue[next_idx]
        duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        log_status_change(current_holder, 'Bastão', '', duration)
        st.session_state.status_texto[current_holder] = '' 
        st.session_state.status_texto[next_holder] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True 
        st.session_state.rotation_gif_start_time = datetime.now()
        send_chat_notification_internal(next_holder, 'Bastão')
        save_state()

def toggle_skip(): 
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': return
    current_skip = st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = not current_skip
    if selected == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None) and st.session_state.skip_flags[selected]:
        rotate_bastao()
    save_state() 

def manual_rerun():
    st.session_state.gif_warning = False
    st.session_state.rotation_gif_start_time = None
    st.rerun() 

def handle_sessao_submission(consultor_sel, camara_sel, data_obj):
    if not data_obj: return False
    data_f = data_obj.strftime("%d/%m/%Y")
    msg = f"Prezada equipe do {camara_sel}, acompanhamento de sessão {data_f} por {consultor_sel}."
    if send_sessao_to_chat(consultor_sel, msg):
        st.session_state.last_reg_status = "success_sessao"
        st.session_state.html_content_cache = gerar_html_checklist(consultor_sel, camara_sel, data_f)
        st.session_state.html_download_ready = True
        return True
    return False

def set_chamado_step(step_num):
    st.session_state.chamado_guide_step = step_num

def handle_chamado_submission():
    st.toast("Chamado registrado.", icon="?")
    st.session_state.chamado_guide_step = 0

def update_status(status_text, available=False): 
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': return
    old_s = st.session_state.status_texto.get(selected, '')
    dur = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, old_s, status_text, dur)
    st.session_state.status_texto[selected] = status_text 
    st.session_state[f'check_{selected}'] = available
    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    check_and_assume_baton()
    save_state()

def handle_horas_extras_submission(c, d, i, t, m):
    if send_horas_extras_to_chat(c, d, i, t, m):
        st.success("Registrado!")
        st.session_state.active_view = None
        time.sleep(1); st.rerun()

def handle_atendimento_submission(c, d, u, s, sys, ds, cn, df, j):
    if send_atendimento_to_chat(c, d, u, s, sys, ds, cn, df, j):
        st.success("Registrado!")
        st.session_state.active_view = None
        time.sleep(1); st.rerun()

# ============================================
# 3. JOGO SIMON
# ============================================

def handle_simon_game():
    COLORS = ["??", "??", "??", "??"]
    st.markdown("### ?? Jogo da Memória")
    if st.session_state.simon_status == 'start':
        if st.button("?? Iniciar"):
            st.session_state.simon_sequence = [random.choice(COLORS)]
            st.session_state.simon_status = 'showing'; st.rerun()
    elif st.session_state.simon_status == 'showing':
        st.info("Memorize!")
        cols = st.columns(len(st.session_state.simon_sequence))
        for i, c in enumerate(st.session_state.simon_sequence): cols[i].markdown(f"## {c}")
        if st.button("Responder"): st.session_state.simon_status = 'playing'; st.rerun()
    elif st.session_state.simon_status == 'playing':
        c1, c2, c3, c4 = st.columns(4)
        p = None
        if c1.button("??"): p = "??"
        if c2.button("??"): p = "??"
        if c3.button("??"): p = "??"
        if c4.button("??"): p = "??"
        if p:
            st.session_state.simon_user_input.append(p)
            idx = len(st.session_state.simon_user_input) - 1
            if st.session_state.simon_user_input[idx] != st.session_state.simon_sequence[idx]:
                st.session_state.simon_status = 'lost'; st.rerun()
            elif len(st.session_state.simon_user_input) == len(st.session_state.simon_sequence):
                st.session_state.simon_sequence.append(random.choice(COLORS))
                st.session_state.simon_user_input = []; st.session_state.simon_level += 1
                st.session_state.simon_status = 'showing'; st.rerun()
    elif st.session_state.simon_status == 'lost':
        st.error(f"Fim de jogo! Nível: {st.session_state.simon_level}")
        if st.button("Tentar Novamente"):
            st.session_state.simon_status = 'start'; st.session_state.simon_level = 1; st.rerun()

# ============================================
# 4. EXECUÇÃO PRINCIPAL
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="??")
init_session_state()
render_fireworks()

c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")

with c_topo_esq:
    img_data = get_img_as_base64(PUG2026_FILENAME)
    img_src = f"data:image/png;base64,{img_data}" if img_data else GIF_BASTAO_HOLDER
    st.markdown(f'<div style="display: flex; align-items: center; gap: 15px;"><h1 style="color: #FFD700; margin: 0;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{img_src}" style="width: 120px; height: 120px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;"></div>', unsafe_allow_html=True)

with c_topo_dir:
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_sub1: nv_resp = st.selectbox("Assumir Bastão", options=["Selecione"] + CONSULTORES, label_visibility="collapsed")
    with c_sub2:
        if st.button("?? Entrar"):
            if nv_resp != "Selecione":
                st.session_state[f'check_{nv_resp}'] = True
                update_queue(nv_resp); st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700; margin: 5px 0 20px 0;'>", unsafe_allow_html=True)
st_autorefresh(interval=8000, key='auto_rerun')

if st.session_state.rotation_gif_start_time:
    if (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 12:
        st.image(GIF_URL_ROTATION, width=200)

col_principal, col_disponibilidade = st.columns([1.5, 1])

with col_principal:
    responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    st.header("Responsável pelo Bastão")
    if responsavel:
        st.markdown(f'<div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%); border: 3px solid #FFD700; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);"><img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; margin-right: 25px;"><span style="font-size: 42px; font-weight: 800; color: #000080;">{responsavel}</span></div>', unsafe_allow_html=True)
    
    st.subheader("Consultor(a)")
    st.selectbox('Selecione seu nome:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("**Ações:**")
    
    def toggle_view(view):
        st.session_state.active_view = view if st.session_state.active_view != view else None

    # BOTÕES DE AÇÃO (8 COLUNAS)
    c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
    c1.button('?? Passar', on_click=rotate_bastao, use_container_width=True)
    c2.button('?? Pular', on_click=toggle_skip, use_container_width=True)
    c3.button('?? Atividades', on_click=toggle_view, args=('menu_atividades',), use_container_width=True)
    c4.button('??? Almoço', on_click=update_status, args=('Almoço',), use_container_width=True)
    c5.button('?? Ausente', on_click=update_status, args=('Ausente',), use_container_width=True)
    c6.button('??? Sessão', on_click=lambda: update_status("Sessão"), use_container_width=True)
    c7.button('?? Saída', on_click=update_status, args=('Saída rápida',), use_container_width=True)
    c8.button('?? Projetos', on_click=toggle_view, args=('projetos',), use_container_width=True)

    # --- VIEWS DINÂMICAS ---
    if st.session_state.active_view == 'projetos':
        with st.container(border=True):
            p_sel = st.selectbox("Escolha o Projeto:", LISTA_PROJETOS)
            if st.button("Confirmar Projeto"):
                update_status(f"Projeto: {p_sel}"); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            atvs = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS)
            if st.button("Gravar"):
                update_status(f"Atividade: {', '.join(atvs)}"); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'erro_novidade':
        with st.container(border=True):
            st.subheader("?? Relatar Erro ou Novidade")
            t1, t2 = st.tabs(["?? Preencher", "?? Exemplo"])
            with t1:
                tp = st.radio("Tipo:", ["Erro", "Novidade"], horizontal=True)
                txt = st.text_area("Relato:", value=(TEMPLATE_ERRO if tp == "Erro" else ""), height=200)
                if st.button("Enviar"):
                    threading.Thread(target=_send_webhook_thread, args=(WEBHOOK_ERROS, {"text": f"?? {tp} por {st.session_state.consultor_selectbox}\n{txt}"})).start()
                    st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
            with t2: st.markdown(EXEMPLO_TEXTO)

    st.markdown("---")
    # FERRAMENTAS INFERIORES (6 COLUNAS)
    tcols = st.columns(6)
    tcols[0].button("?? Checklist", on_click=toggle_view, args=("checklist",), use_container_width=True)
    tcols[1].button("?? Chamados", on_click=toggle_view, args=("chamados",), use_container_width=True)
    tcols[2].button("?? Atendimento", on_click=toggle_view, args=("atendimentos",), use_container_width=True)
    tcols[3].button("? H. Extras", on_click=toggle_view, args=("hextras",), use_container_width=True)
    tcols[4].button("?? Descanso", on_click=toggle_view, args=("descanso",), use_container_width=True)
    tcols[5].button("?? Erro/Novidade", on_click=toggle_view, args=("erro_novidade",), use_container_width=True)

with col_disponibilidade:
    st.header('Status da Equipe')
    ui_lists = {'fila': [], 'projetos': [], 'demanda': [], 'outros': []}
    for n in CONSULTORES:
        s = st.session_state.status_texto.get(n, 'Indisponível')
        if s == 'Bastão' or s == '': ui_lists['fila'].append(n)
        elif 'Projeto:' in s: ui_lists['projetos'].append((n, s.replace('Projeto: ', '')))
        elif 'Atividade:' in s: ui_lists['demanda'].append(n)
        else: ui_lists['outros'].append(n)

    st.subheader(f"? Na Fila ({len(ui_lists['fila'])})")
    queue = st.session_state.bastao_queue
    for idx, n in enumerate([c for c in queue if c in ui_lists['fila']]):
        cn, cc = st.columns([0.8, 0.2])
        cc.checkbox(' ', key=f'check_{n}', value=True, on_change=update_queue, args=(n,))
        pref = "?? " if n == responsavel else f"{idx+1}º "
        cn.markdown(f"**{pref}{n}**")

    st.subheader(f"?? Projetos ({len(ui_lists['projetos'])})")
    for n, p in ui_lists['projetos']:
        st.markdown(f"**{n}** :violet-background[{p}]")

    st.subheader(f"?? Demanda ({len(ui_lists['demanda'])})")
    for n in ui_lists['demanda']: st.caption(f"• {n}")

# RESET DIÁRIO 20H
now = datetime.now()
if now.hour >= 20 and st.session_state.report_last_run_date.date() < date.today():
    send_daily_report()
