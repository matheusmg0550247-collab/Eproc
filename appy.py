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

# --- FUNÇÃO DE HORÁRIO BRASIL (UTC-3) ---
def get_brazil_time():
    # Ajusta UTC para UTC-3 (Brasília)
    return datetime.utcnow() - timedelta(hours=3)

# --- FUNÇÃO DE CACHE GLOBAL ---
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    print("--- Inicializando o Cache de Estado GLOBAL (Executa Apenas 1x) ---")
    now_br = get_brazil_time()
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: now_br for nome in CONSULTORES},
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        'lunch_warning_info': None,
        'auxilio_ativo': False, 
        'daily_logs': [],
        # --- Ranking Global do Jogo ---
        'simon_ranking': [] 
    }

# --- Constantes (Webhooks) ---
# [SEGURANÇA] Idealmente, mova estas chaves para st.secrets em produção
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "" 
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
GOOGLE_CHAT_WEBHOOK_ERRO_NOVIDADE = "https://chat.googleapis.com/v1/spaces/AAQAp4gdyUE/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=vnI4C_jTeF0UQINXiVYpRrnEsYaO4-Nnvs8RC-PTj0k"

# URL do Web App da Planilha
SHEETS_WEBHOOK_URL = ""

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
    "Homologação", "Redação Documentos", "Outros"
]
ATIVIDADES_COM_DETALHE = ["Homologação", "Redação Documentos", "Outros"]

OPCOES_PROJETOS = [
    "Soma", "Treinamentos Eproc", "Manuais Eproc", 
    "Cartilhas Gabinetes", "Notebook Lm", "Inteligência artifical cartórios"
]

GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "??" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUS_SAIDA_PRIORIDADE = ['Saída rápida']
# [ALTERAÇÃO] Adicionado Treinamento como status de saída
STATUSES_DE_SAIDA = ['Almoço', 'Saída rápida', 'Ausente', 'Sessão', 'Treinamento'] 
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

def _send_webhook_thread(url, payload):
    try:
        headers = {'Content-Type': 'application/json'}
        requests.post(url, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print(f"Erro no envio assíncrono: {e}")

def send_log_to_sheets(timestamp_str, consultor, old_status, new_status, duration_str):
    if not SHEETS_WEBHOOK_URL: return
    payload = {
        "data_hora": timestamp_str,
        "consultor": consultor,
        "status_anterior": old_status,
        "status_atual": new_status,
        "tempo_anterior": duration_str
    }
    threading.Thread(target=_send_webhook_thread, args=(SHEETS_WEBHOOK_URL, payload)).start()

def log_status_change(consultor, old_status, new_status, duration):
    print(f'LOG: {consultor} de "{old_status or "-"}" para "{new_status or "-"}" após {duration}')
    if not isinstance(duration, timedelta): duration = timedelta(0)

    # 1. REGRA DO HORÁRIO: Início às 08:00
    now_br = get_brazil_time()
    start_t = st.session_state.current_status_starts.get(consultor, now_br)
    today_8am = now_br.replace(hour=8, minute=0, second=0, microsecond=0)
    final_duration = duration
    
    # Se começou antes das 8h e agora é depois das 8h, conta a partir das 8h
    if start_t < today_8am and now_br >= today_8am:
         final_duration = now_br - today_8am
         if final_duration.total_seconds() < 0:
             final_duration = timedelta(0)
    
    # 2. DEFINIÇÃO DO RÓTULO DO STATUS
    old_lbl = old_status if old_status else 'Fila Bastão'
    new_lbl = new_status if new_status else 'Fila Bastão'

    # [CORREÇÃO LOG STATUS COMPOSTO]: Garante que "Fila | Projeto" apareça no log
    # Verifica se a pessoa está na fila mas não tem a palavra "Bastão" explicitamente
    # (ou seja, está na fila mas não é o dono)
    if consultor in st.session_state.bastao_queue:
        if 'Bastão' not in new_lbl and new_lbl != 'Fila Bastão':
             # Se não for o dono, mas está na fila e tem atividade (ex: Projeto), adiciona "Fila | "
             new_lbl = f"Fila | {new_lbl}"
    
    # Se for "Bastão" puro ou com algo, já está certo no new_status vindo do update_status

    entry = {
        'timestamp': now_br,
        'consultor': consultor,
        'old_status': old_lbl, 
        'new_status': new_lbl,
        'duration': final_duration,
        'duration_s': final_duration.total_seconds()
    }
    st.session_state.daily_logs.append(entry)
    
    timestamp_str = now_br.strftime("%d/%m/%Y %H:%M:%S")
    duration_str = format_time_duration(final_duration)
    send_log_to_sheets(timestamp_str, consultor, old_lbl, new_lbl, duration_str)
    
    if consultor not in st.session_state.current_status_starts:
        st.session_state.current_status_starts[consultor] = now_br
    st.session_state.current_status_starts[consultor] = now_br

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

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

def handle_erro_novidade_submission(consultor, titulo, objetivo, relato, resultado):
    if not GOOGLE_CHAT_WEBHOOK_ERRO_NOVIDADE: return False
    data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
    msg = (
        f"?? **Novo Relato de Erro/Novidade**\n"
        f"?? **Data:** {data_envio}\n\n"
        f"?? **Autor:** {consultor}\n"
        f"?? **Título:** {titulo}\n\n"
        f"?? **Objetivo:**\n{objetivo}\n\n"
        f"?? **Relato:**\n{relato}\n\n"
        f"?? **Resultado:**\n{resultado}"
    )
    chat_message = {"text": msg}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_ERRO_NOVIDADE, chat_message)).start()
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
      --color1: #ff0000; --color2: #ffd700; --color3: #b22222; --color4: #daa520; --color5: #ff4500; --color6: #b8860b;
      --y: -30vmin; --x: -50%; --initialY: 60vmin;
      content: ""; animation: firework 2s infinite; position: absolute; top: 50%; left: 50%;
      transform: translate(-50%, var(--y)); width: var(--initialSize); aspect-ratio: 1;
      background: radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%,
        radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%,
        radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 50% 100%,
        radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 0% 50%,
        radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 80% 90%,
        radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 95% 90%;
      background-size: var(--initialSize) var(--initialSize); background-repeat: no-repeat;
    }
    .firework::before { --x: -50%; --y: -50%; --initialY: -50%; transform: translate(-50%, -50%) rotate(40deg) scale(1.3) rotateY(40deg); }
    .firework::after { --x: -50%; --y: -50%; --initialY: -50%; transform: translate(-50%, -50%) rotate(170deg) scale(1.15) rotateY(-30deg); }
    .firework:nth-child(2) { --x: 30vmin; }
    .firework:nth-child(2), .firework:nth-child(2)::before, .firework:nth-child(2)::after {
      --color1: #ff0000; --color2: #ffd700; --color3: #8b0000; --color4: #daa520; --color5: #ff6347; --color6: #f0e68c;  
      --finalSize: 40vmin; left: 30%; top: 60%; animation-delay: -0.25s;
    }
    .firework:nth-child(3) { --x: -30vmin; --y: -50vmin; }
    .firework:nth-child(3), .firework:nth-child(3)::before, .firework:nth-child(3)::after {
      --color1: #ffd700; --color2: #ff4500; --color3: #b8860b; --color4: #cd5c5c; --color5: #800000; --color6: #ffa500;
      --finalSize: 35vmin; left: 70%; top: 60%; animation-delay: -0.4s;
    }
    </style>
    <div class="firework"></div><div class="firework"></div><div class="firework"></div>
    """
    st.markdown(fireworks_css, unsafe_allow_html=True)

def gerar_html_checklist(consultor_nome, camara_nome, data_sessao_formatada):
    consultor_formatado = f"@{consultor_nome}" if not consultor_nome.startswith("@") else consultor_nome
    html_template = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Acompanhamento de Sessão - {camara_nome}</title></head>
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

    now_br = get_brazil_time()
    today_str = now_br.strftime("%d/%m/%Y")
    report_text = f"?? **Relatório Diário de Atividades - {today_str}** ??\n\n"
    consultores_com_dados = []
    for nome in CONSULTORES:
        counts = bastao_counts.get(nome, 0)
        times = aggregated_data.get(nome, {})
        bastao_time = times.get('Bastão', timedelta(0))
        if counts > 0 or times:
            consultores_com_dados.append(nome)
            report_text += f"**?? {nome}**\n"
            report_text += f"- {BASTAO_EMOJI} Bastão Recebido: **{counts}** vez(es)\n"
            report_text += f"- ?? Tempo com Bastão: **{format_time_duration(bastao_time)}**\n"
            other_statuses = []
            sorted_times = sorted(times.items(), key=itemgetter(0)) 
            for status, time in sorted_times:
                if status != 'Bastão' and status:
                    other_statuses.append(f"{status}: **{format_time_duration(time)}**")
            if other_statuses: report_text += f"- ? Outros Tempos: {', '.join(other_statuses)}\n\n"
            else: report_text += "\n"

    if not consultores_com_dados: report_text = f"?? **Relatório Diário - {today_str}** ??\n\nNenhuma atividade registrada hoje."
    if not GOOGLE_CHAT_WEBHOOK_BACKUP: return 
    chat_message = {'text': report_text}
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_BACKUP, chat_message)).start()
    st.session_state['report_last_run_date'] = now_br
    st.session_state['daily_logs'] = []
    st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
    save_state()

# ============================================
# [CORREÇÃO 1: init_session_state robusto]
# ============================================
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

    now_br = get_brazil_time()
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0)
        st.session_state.skip_flags.setdefault(nome, False)
        
        current_status = st.session_state.status_texto.get(nome, 'Indisponível') 
        if current_status is None: current_status = 'Indisponível'
        st.session_state.status_texto[nome] = current_status
        
        # [MODIFICAÇÃO] Lógica de Disponibilidade (Checkboxes)
        # Prioriza quem já está na fila, a menos que tenha status de bloqueio
        blocking_keywords = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento']
        is_hard_blocked = any(kw in current_status for kw in blocking_keywords)
        
        if is_hard_blocked:
            is_available = False
        elif nome in st.session_state.priority_return_queue:
            is_available = False
        # Se já está na fila e não tem bloqueio rígido, PRESERVA (Evita o bug de reset)
        elif nome in st.session_state.bastao_queue:
            is_available = True
        else:
            is_available = 'Indisponível' not in current_status

        st.session_state[f'check_{nome}'] = is_available
        
        if nome not in st.session_state.current_status_starts: st.session_state.current_status_starts[nome] = now_br

    check_and_assume_baton()

# ============================================
# [CORREÇÃO 2: find_next_holder_index com busca circular]
# ============================================
def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue)
    
    # Começa a busca a partir da próxima posição (ou 0 se current_index for -1)
    start_index = (current_index + 1) % n
    
    # Percorre a lista inteira uma vez (n vezes)
    for i in range(n):
        idx = (start_index + i) % n
        consultor = queue[idx]
        
        # Critérios: Disponível (Check=True) E Não Pular
        is_available = st.session_state.get(f'check_{consultor}', False)
        is_skipping = skips.get(consultor, False)
        
        if is_available and not is_skipping:
            return idx
            
    return -1

def check_and_assume_baton(forced_successor=None):
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    is_current_valid = (current_holder_status and current_holder_status in queue and st.session_state.get(f'check_{current_holder_status}'))
    
    # [CORREÇÃO ROTAÇÃO] Se forçado a um sucessor, use-o. Caso contrário, busca na fila.
    should_have_baton = None
    if forced_successor:
        should_have_baton = forced_successor
    elif is_current_valid: 
        should_have_baton = current_holder_status
    else:
        # Se ninguém tem o bastão ou o atual saiu, procura o primeiro elegível (fallback)
        first_eligible_index = find_next_holder_index(-1, queue, skips)
        should_have_baton = queue[first_eligible_index] if first_eligible_index != -1 else None

    changed = False
    previous_holder = current_holder_status 
    now_br = get_brazil_time()

    for c in CONSULTORES:
        s_text = st.session_state.status_texto.get(c, '')
        if c != should_have_baton and 'Bastão' in s_text:
            duration = now_br - st.session_state.current_status_starts.get(c, now_br)
            log_status_change(c, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[c] = 'Indisponível'
            changed = True

    if should_have_baton:
        s_current = st.session_state.status_texto.get(should_have_baton, '')
        if 'Bastão' not in s_current:
            old_status = s_current
            duration = now_br - st.session_state.current_status_starts.get(should_have_baton, now_br)
            # Mantém status anteriores se for acumulativo
            new_status = f"Bastão | {old_status}" if old_status and old_status != "Indisponível" else "Bastão"
            log_status_change(should_have_baton, old_status, new_status, duration)
            st.session_state.status_texto[should_have_baton] = new_status
            st.session_state.bastao_start_time = now_br
            if previous_holder != should_have_baton: 
                st.session_state.play_sound = True 
                send_chat_notification_internal(should_have_baton, 'Bastão') 
            if st.session_state.skip_flags.get(should_have_baton):
                st.session_state.skip_flags[should_have_baton] = False
            changed = True
    elif not should_have_baton:
        if current_holder_status:
            duration = now_br - st.session_state.current_status_starts.get(current_holder_status, now_br)
            log_status_change(current_holder_status, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[current_holder_status] = 'Indisponível' 
            changed = True
        if st.session_state.bastao_start_time is not None: changed = True
        st.session_state.bastao_start_time = None

    if changed: save_state()
    return changed

# ============================================
# [CORREÇÃO 3: toggle_queue limpa flag de skip]
# ============================================
def toggle_queue(consultor):
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    now_br = get_brazil_time()
    
    if consultor in st.session_state.bastao_queue:
        # SAINDO DA FILA
        current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        forced_successor = None
        
        if consultor == current_holder:
            current_idx = -1
            try: current_idx = st.session_state.bastao_queue.index(consultor)
            except ValueError: pass
            
            if current_idx != -1:
                next_idx = find_next_holder_index(current_idx, st.session_state.bastao_queue, st.session_state.skip_flags)
                if next_idx != -1:
                    forced_successor = st.session_state.bastao_queue[next_idx]
                    
        st.session_state.bastao_queue.remove(consultor)
        st.session_state[f'check_{consultor}'] = False
        current_s = st.session_state.status_texto.get(consultor, '')
        
        if current_s == '' or current_s == 'Bastão':
            duration = now_br - st.session_state.current_status_starts.get(consultor, now_br)
            log_status_change(consultor, current_s, 'Indisponível', duration)
            st.session_state.status_texto[consultor] = 'Indisponível'
            
        check_and_assume_baton(forced_successor=forced_successor)
    else:
        # ENTRANDO NA FILA
        st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True
        
        # [MODIFICAÇÃO] Reseta flag de Pular ao entrar na fila
        st.session_state.skip_flags[consultor] = False 
        
        if consultor in st.session_state.priority_return_queue:
            st.session_state.priority_return_queue.remove(consultor)
            
        current_s = st.session_state.status_texto.get(consultor, 'Indisponível')
        
        # Limpa o "Indisponível" visualmente
        if 'Indisponível' in current_s:
            duration = now_br - st.session_state.current_status_starts.get(consultor, now_br)
            log_status_change(consultor, current_s, '', duration)
            st.session_state.status_texto[consultor] = ''
            
        check_and_assume_baton()

    save_state()

def leave_specific_status(consultor, status_type_to_remove):
    # Remove apenas o tipo de status específico (Ex: Remove só 'Projeto: ...')
    st.session_state.gif_warning = False
    old_status = st.session_state.status_texto.get(consultor, '')
    now_br = get_brazil_time()
    duration = now_br - st.session_state.current_status_starts.get(consultor, now_br)
    
    parts = [p.strip() for p in old_status.split('|')]
    new_parts = []
    for p in parts:
        if status_type_to_remove in p: continue
        if not p: continue
        new_parts.append(p)
    
    new_status = " | ".join(new_parts)
    if not new_status and consultor not in st.session_state.bastao_queue: new_status = 'Indisponível'
    
    log_status_change(consultor, old_status, new_status, duration)
    st.session_state.status_texto[consultor] = new_status
    
    # [CORREÇÃO ALMOÇO] Se desmarcou Almoço, volta pra fila
    if status_type_to_remove == 'Almoço' or status_type_to_remove == 'Treinamento':
        if consultor not in st.session_state.bastao_queue:
            st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True
        st.session_state.skip_flags[consultor] = False
    
    check_and_assume_baton()
    save_state()

def enter_from_indisponivel(consultor):
    st.session_state.gif_warning = False
    if consultor not in st.session_state.bastao_queue:
        st.session_state.bastao_queue.append(consultor)
    st.session_state[f'check_{consultor}'] = True
    st.session_state.skip_flags[consultor] = False
    old_status = st.session_state.status_texto.get(consultor, 'Indisponível')
    now_br = get_brazil_time()
    duration = now_br - st.session_state.current_status_starts.get(consultor, now_br)
    log_status_change(consultor, old_status, '', duration)
    st.session_state.status_texto[consultor] = ''
    check_and_assume_baton()
    save_state()

def rotate_bastao(): 
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    if selected != current_holder: st.session_state.gif_warning = True; return 

    current_index = -1
    try: current_index = queue.index(current_holder)
    except ValueError:
        if check_and_assume_baton(): pass 
        return

    eligible_in_queue = [p for p in queue if st.session_state.get(f'check_{p}')]
    skippers_ahead = [p for p in eligible_in_queue if skips.get(p, False) and p != current_holder]
    if len(skippers_ahead) > 0 and len(skippers_ahead) == len([p for p in eligible_in_queue if p != current_holder]):
        for c in queue: st.session_state.skip_flags[c] = False
        skips = st.session_state.skip_flags 
        st.toast("Ciclo reiniciado! Todos os próximos pularam, fila resetada.", icon="??")

    next_idx = find_next_holder_index(current_index, queue, skips)
    if next_idx != -1:
        next_holder = queue[next_idx]
        if next_idx > current_index: skipped_over = queue[current_index+1 : next_idx]
        else: skipped_over = queue[current_index+1:] + queue[:next_idx]
        for person in skipped_over: st.session_state.skip_flags[person] = False 
        st.session_state.skip_flags[next_holder] = False

        now_br = get_brazil_time()
        duration = now_br - (st.session_state.bastao_start_time or now_br)
        # Tira Bastão do antigo, mantém resto
        old_h_status = st.session_state.status_texto[current_holder]
        new_h_status = old_h_status.replace('Bastão | ', '').replace('Bastão', '').strip()
        log_status_change(current_holder, old_h_status, new_h_status, duration)
        st.session_state.status_texto[current_holder] = new_h_status 
        
        # Dá Bastão pro novo
        old_n_status = st.session_state.status_texto.get(next_holder, '')
        new_n_status = f"Bastão | {old_n_status}" if old_n_status else "Bastão"
        log_status_change(next_holder, old_n_status, new_n_status, timedelta(0))
        st.session_state.status_texto[next_holder] = new_n_status
        st.session_state.bastao_start_time = now_br
        
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True 
        st.session_state.rotation_gif_start_time = now_br
        send_chat_notification_internal(next_holder, 'Bastão')
        save_state()
    else:
        st.warning('Não há próximo(a) consultor(a) elegível na fila no momento.')
        check_and_assume_baton() 

def toggle_skip(): 
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    if not st.session_state.get(f'check_{selected}'): st.warning(f'{selected} não está disponível para marcar/desmarcar.'); return
    current_skip_status = st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = not current_skip_status
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if selected == current_holder and st.session_state.skip_flags[selected]: save_state(); rotate_bastao(); return 
    save_state() 

def manual_rerun():
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    st.rerun() 
    
def on_auxilio_change(): save_state()

def handle_sessao_submission(consultor_sel, camara_sel, data_obj):
    if not data_obj: st.error("Por favor, selecione uma data."); return False
    data_formatada = data_obj.strftime("%d/%m/%Y")
    data_nome_arquivo = data_obj.strftime("%d-%m-%Y")
    email_setor = CAMARAS_DICT.get(camara_sel, "")
    nome_consultor_txt = consultor_sel if consultor_sel and consultor_sel != "Selecione um nome" else "[NOME DO(A) CONSULTOR(A)]"
    texto_mensagem = f"Prezada equipe do {camara_sel},\n\nMeu nome é {nome_consultor_txt}, sou assistente de processos judiciais da CESUPE/TJMG e serei o(a) responsável pelo acompanhamento técnico da sessão de julgamento agendada para o dia {data_formatada}.\n\nCom o objetivo de agilizar o atendimento e a verificação de eventuais demandas, encaminharei um formulário em HTML para preenchimento de algumas informações prévias. As respostas retornarão diretamente para mim, permitindo a análise antecipada da situação e, sempre que possível, a definição prévia da orientação ou solução a ser adotada. O preenchimento não é obrigatório, mas contribuirá para tornar o suporte mais eficaz.\n\nRessalto que continuamos disponíveis para sanar quaisquer dúvidas por meio do nosso suporte. Caso eu esteja indisponível no momento do contato, retornarei o mais breve possível.\n\nApós a realização da sessão, o suporte técnico voltará a ser prestado de forma rotineira pelo nosso setor. Havendo dúvidas ou necessidade de suporte, entre em contato conosco pelo telefone **3232-2640**.\n\nPermaneço à disposição e agradeço a colaboração.\n\nAtenciosamente,\n{nome_consultor_txt}\nAssistente de Processos Judiciais – CESUPE/TJMG\n\nEmail do setor: {email_setor}"
    success = send_sessao_to_chat(consultor_sel, texto_mensagem)
    if success:
        st.session_state.last_reg_status = "success_sessao"
        html_content = gerar_html_checklist(consultor_sel, camara_sel, data_formatada)
        st.session_state.html_content_cache = html_content
        st.session_state.html_download_ready = True
        st.session_state.html_filename = f"Checklist_{data_nome_arquivo}.html"
        return True
    else: st.session_state.last_reg_status = "error_sessao"; st.session_state.html_download_ready = False; return False

def set_chamado_step(step_num): st.session_state.chamado_guide_step = step_num

def handle_chamado_submission():
    st.toast("Chamado simulado com sucesso.", icon="?")
    st.session_state.last_reg_status = "success_chamado" 
    st.session_state.chamado_guide_step = 0
    st.session_state.chamado_textarea = ""

# [STATUS ACUMULATIVO E BLOQUEANTE ATUALIZADO]
def update_status(new_status_part, force_exit_queue=False): 
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    
    if not selected or selected == 'Selecione um nome': 
        st.warning('Selecione um(a) consultor(a).')
        return

    # Aviso Almoço
    if new_status_part != 'Almoço': st.session_state.lunch_warning_info = None
    if new_status_part == 'Almoço':
        # Lógica de aviso de almoço aqui...
        pass 

    # [MODIFICADO] Lista de bloqueio inclui Sessão, Reunião e agora TREINAMENTO
    blocking_statuses = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento']
    should_exit_queue = False
    
    # Verifica se o novo status contém alguma palavra chave de bloqueio
    is_blocking = any(b in new_status_part for b in blocking_statuses)

    if is_blocking or force_exit_queue:
        should_exit_queue = True
        final_status = new_status_part 
    else:
        # Lógica Acumulativa: Adiciona novo status aos existentes
        current = st.session_state.status_texto.get(selected, '')
        parts = [p.strip() for p in current.split('|') if p.strip()]
        
        type_of_new = new_status_part.split(':')[0]
        cleaned_parts = []
        for p in parts:
            if p == 'Indisponível': continue
            if p.startswith(type_of_new): continue # Substitui status do mesmo tipo (ex: troca um projeto por outro)
            cleaned_parts.append(p)
        
        cleaned_parts.append(new_status_part)
        # Garante a ordem: Bastão primeiro, depois Atividade/Projeto
        cleaned_parts.sort(key=lambda x: 0 if 'Bastão' in x else 1 if 'Atividade' in x or 'Projeto' in x else 2)
        final_status = " | ".join(cleaned_parts)

    if should_exit_queue:
        st.session_state[f'check_{selected}'] = False 
        if selected in st.session_state.bastao_queue: 
            st.session_state.bastao_queue.remove(selected)
        st.session_state.skip_flags.pop(selected, None)
    
    # Lógica para garantir que Bastão permaneça se não for saída de fila
    was_holder = next((True for c, s in st.session_state.status_texto.items() if 'Bastão' in s and c == selected), False)
    old_status = st.session_state.status_texto.get(selected, '')
    
    if was_holder and not should_exit_queue:
        if 'Bastão' not in final_status:
            final_status = f"Bastão | {final_status}"

    now_br = get_brazil_time()
    duration = now_br - st.session_state.current_status_starts.get(selected, now_br)
    log_status_change(selected, old_status, final_status, duration)
    st.session_state.status_texto[selected] = final_status
    
    if new_status_part == 'Saída rápida':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)
    
    if was_holder: check_and_assume_baton() 
    save_state() 

def handle_horas_extras_submission(consultor_sel, data, inicio, tempo, motivo):
    if not consultor_sel or consultor_sel == "Selecione um nome": st.error("Selecione um consultor."); return
    if send_horas_extras_to_chat(consultor_sel, data, inicio, tempo, motivo):
        st.success("Horas extras registradas com sucesso!")
        st.session_state.active_view = None 
        time.sleep(1)
        st.rerun()
    else: st.error("Erro ao enviar. Verifique o Webhook.")

def handle_atendimento_submission(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    if not consultor or consultor == "Selecione um nome": st.error("Selecione um consultor."); return
    if send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional):
        st.success("Atendimento registrado com sucesso!")
        st.session_state.active_view = None 
        time.sleep(1)
        st.rerun()
    else: st.error("Erro ao enviar. Verifique o Webhook.")

def handle_simon_game():
    COLORS = ["??", "??", "??", "??"]
    st.markdown("### ?? Jogo da Memória (Simon)")
    st.caption("Repita a sequência de cores!")
    if st.session_state.simon_status == 'start':
        if st.button("?? Iniciar Jogo", use_container_width=True):
            st.session_state.simon_sequence = [random.choice(COLORS)]
            st.session_state.simon_user_input = []
            st.session_state.simon_level = 1
            st.session_state.simon_status = 'showing'
            st.rerun()
    elif st.session_state.simon_status == 'showing':
        st.info(f"Nível {st.session_state.simon_level}: Memorize a sequência!")
        cols = st.columns(len(st.session_state.simon_sequence))
        for i, color in enumerate(st.session_state.simon_sequence):
            with cols[i]: st.markdown(f"<h1 style='text-align: center;'>{color}</h1>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("?? Já decorei! Responder", type="primary", use_container_width=True):
            st.session_state.simon_status = 'playing'
            st.rerun()
    elif st.session_state.simon_status == 'playing':
        st.markdown(f"**Nível {st.session_state.simon_level}** - Clique na ordem:")
        c1, c2, c3, c4 = st.columns(4)
        pressed = None
        if c1.button("??", use_container_width=True): pressed = "??"
        if c2.button("??", use_container_width=True): pressed = "??"
        if c3.button("??", use_container_width=True): pressed = "??"
        if c4.button("??", use_container_width=True): pressed = "??"
        if pressed:
            st.session_state.simon_user_input.append(pressed)
            current_idx = len(st.session_state.simon_user_input) - 1
            if st.session_state.simon_user_input[current_idx] != st.session_state.simon_sequence[current_idx]:
                st.session_state.simon_status = 'lost'
                st.rerun()
            elif len(st.session_state.simon_user_input) == len(st.session_state.simon_sequence):
                st.success("Correto! Próximo nível...")
                time.sleep(0.5)
                st.session_state.simon_sequence.append(random.choice(COLORS))
                st.session_state.simon_user_input = []
                st.session_state.simon_level += 1
                st.session_state.simon_status = 'showing'
                st.rerun()
        if st.session_state.simon_user_input: st.markdown(f"Sua resposta: {' '.join(st.session_state.simon_user_input)}")
    elif st.session_state.simon_status == 'lost':
        st.error(f"? Errou! Você chegou ao Nível {st.session_state.simon_level}.")
        st.markdown(f"Sequência correta era: {' '.join(st.session_state.simon_sequence)}")
        consultor = st.session_state.consultor_selectbox
        if consultor and consultor != 'Selecione um nome':
            score = st.session_state.simon_level
            current_ranking = st.session_state.simon_ranking
            found = False
            for entry in current_ranking:
                if entry['nome'] == consultor:
                    if score > entry['score']: entry['score'] = score
                    found = True; break
            if not found: current_ranking.append({'nome': consultor, 'score': score})
            st.session_state.simon_ranking = sorted(current_ranking, key=lambda x: x['score'], reverse=True)[:5]
            save_state(); st.success(f"Pontuação salva para {consultor}!")
        else: st.warning("Selecione seu nome no menu superior para salvar no Ranking.")
        if st.button("Tentar Novamente"): st.session_state.simon_status = 'start'; st.rerun()
    st.markdown("---")
    st.subheader("?? Ranking Global (Top 5)")
    ranking = st.session_state.simon_ranking
    if not ranking: st.markdown("_Nenhum recorde ainda._")
    else: df_rank = pd.DataFrame(ranking); st.table(df_rank)

# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="??")
init_session_state()
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
render_fireworks()

c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img_data = get_img_as_base64(PUG2026_FILENAME)
    img_src = f"data:image/png;base64,{img_data}" if img_data else GIF_BASTAO_HOLDER
    st.markdown(f"""<div style="display: flex; align-items: center; gap: 15px;"><h1 style="margin: 0; padding: 0; font-size: 2.2rem; color: #FFD700; text-shadow: 1px 1px 2px #B8860B;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{img_src}" alt="Pug 2026" style="width: 120px; height: 120px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;"></div>""", unsafe_allow_html=True)

with c_topo_dir:
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_sub1: novo_responsavel = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
    with c_sub2:
        if st.button("?? Entrar", help="Ficar disponível na fila imediatamente"):
            if novo_responsavel and novo_responsavel != "Selecione":
                # Botão rápido força entrada na fila e limpa skips
                toggle_queue(novo_responsavel)
                st.session_state.consultor_selectbox = novo_responsavel 
                st.success(f"{novo_responsavel} agora está na fila!")
                st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True) 

gif_start_time = st.session_state.get('rotation_gif_start_time')
lunch_warning_info = st.session_state.get('lunch_warning_info') 
show_gif = False
show_lunch_warning = False
refresh_interval = 8000 

if gif_start_time:
    try:
        elapsed = (datetime.now() - gif_start_time).total_seconds()
        if elapsed < 20: show_gif = True; refresh_interval = 2000 
        else: st.session_state.rotation_gif_start_time = None; save_state() 
    except: st.session_state.rotation_gif_start_time = None
        
if lunch_warning_info and lunch_warning_info.get('start_time'):
    try:
        elapsed_lunch = (datetime.now() - lunch_warning_info['start_time']).total_seconds()
        if elapsed_lunch < 30: show_lunch_warning = True; refresh_interval = 2000 
        else: st.session_state.lunch_warning_info = None; save_state() 
    except Exception as e: print(f"Erro ao processar timer do aviso de almoço: {e}"); st.session_state.lunch_warning_info = None
        
st_autorefresh(interval=refresh_interval, key='auto_rerun_key') 

if st.session_state.get('play_sound', False):
    st.components.v1.html(play_sound_html(), height=0, width=0)
    st.session_state.play_sound = False 

if show_gif: st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')
if show_lunch_warning: st.warning(f"?? **{lunch_warning_info['message']}**"); st.image(GIF_URL_LUNCH_WARNING, width=200)
if st.session_state.get('gif_warning', False): st.error('?? Ação inválida! Verifique as regras.'); st.image(GIF_URL_WARNING, width=150)

col_principal, col_disponibilidade = st.columns([1.5, 1])
queue = st.session_state.bastao_queue
skips = st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)

current_index = queue.index(responsavel) if responsavel in queue else -1
proximo_index = find_next_holder_index(current_index, queue, skips)
proximo = queue[proximo_index] if proximo_index != -1 else None
restante = []

# --- LÓGICA CORRIGIDA: MOSTRAR TODOS DA FILA ---
if proximo_index != -1: 
    num_q = len(queue)
    # Começa logo após o "Próximo" para manter a ordem visual cíclica
    idx = (proximo_index + 1) % num_q 
    
    # Itera por toda a fila para garantir que todos sejam verificados
    for _ in range(num_q):
        person = queue[idx]
        # Adiciona todos que não sejam o Responsável e nem o Próximo
        # Sem filtros de 'skip' ou 'check' para garantir que espelhe a lista da direita
        if person != responsavel and person != proximo:
            restante.append(person)
        
        idx = (idx + 1) % num_q
# ------------------------------------------------

with col_principal:
    st.header("Responsável pelo Bastão")
    if responsavel:
        bg_color = "linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%)" 
        border_color = "#FFD700" 
        text_color = "#000080" 
        st.markdown(f"""<div style="background: {bg_color}; border: 3px solid {border_color}; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3); margin-bottom: 20px;"><div style="flex-shrink: 0; margin-right: 25px;"><img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid {border_color};"></div><div><span style="font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px;">Atualmente com:</span><br><span style="font-size: 42px; font-weight: 800; color: {text_color}; line-height: 1.1; font-family: 'Segoe UI', sans-serif;">{responsavel}</span></div></div>""", unsafe_allow_html=True)
        duration = timedelta()
        if st.session_state.bastao_start_time:
             try: duration = get_brazil_time() - st.session_state.bastao_start_time
             except: pass
        st.caption(f"?? Tempo com o bastão: **{format_time_duration(duration)}**")
    else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
    st.markdown("###")

    st.header("Próximos da Fila")
    if proximo: st.markdown(f'### 1º: **{proximo}**')
    if restante: st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    if not proximo and not restante:
        if responsavel: st.markdown('*Apenas o responsável atual é elegível.*')
        elif queue and all(skips.get(c, False) or not st.session_state.get(f'check_{c}') for c in queue) : st.markdown('*Todos disponíveis estão marcados para pular...*')
        else: st.markdown('*Ninguém elegível na fila.*')
    elif not restante and proximo: st.markdown("&nbsp;")

    skipped_consultants = [c for c, is_skipped in skips.items() if is_skipped and st.session_state.get(f'check_{c}')]
    if skipped_consultants:
        skipped_text = ', '.join(sorted(skipped_consultants))
        num_skipped = len(skipped_consultants)
        
        # Ajuste do texto conforme pedido
        lbl_consultor = 'Consultores' if num_skipped > 1 else 'Consultor(a)'
        lbl_acao = 'acionaram' if num_skipped > 1 else 'acionou'
        lbl_retorno = 'irão retornar' if num_skipped > 1 else 'irá retornar'

        st.markdown(f'''
        <div style="margin-top: 10px; padding: 10px; border-left: 5px solid #ff9800; background-color: #fff3e0;">
            <span style="color: #e65100; font-weight: bold;">?? {lbl_consultor} {lbl_acao} o botão pular:</span><br>
            <span style="color: #333;"><strong>{skipped_text}</strong></span><br>
            <span style="font-size: 0.9em; color: #555;">({lbl_retorno} na próxima rotação do bastão)</span>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("###")
    st.header("**Consultor(a)**")
    
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Ações:**")
    
    def toggle_view(view_name):
        if st.session_state.active_view == view_name: st.session_state.active_view = None
        else: st.session_state.active_view = view_name; 
        if view_name == 'chamados': st.session_state.chamado_guide_step = 1

    row1_c1, row1_c2, row1_c3, row1_c4 = st.columns(4)
    # [LAYOUT] Adicionado espaço para o novo botão de Treinamento na segunda linha (6 colunas agora)
    row2_c1, row2_c2, row2_c3, row2_c4, row2_c5, row2_c6 = st.columns(6)

    row1_c1.button('?? Passar', on_click=rotate_bastao, use_container_width=True, help='Passa o bastão.')
    row1_c2.button('?? Pular', on_click=toggle_skip, use_container_width=True, help='Pular vez.')
    row1_c3.button('?? Atividades', on_click=toggle_view, args=('menu_atividades',), use_container_width=True)
    row1_c4.button('??? Projeto', on_click=toggle_view, args=('menu_projetos',), use_container_width=True)
    
    # [NOVO BOTÃO]
    row2_c1.button('?? Treinamento', on_click=toggle_view, args=('menu_treinamento',), use_container_width=True)
    row2_c2.button('?? Reunião', on_click=toggle_view, args=('menu_reuniao',), use_container_width=True)
    row2_c3.button('??? Almoço', on_click=update_status, args=('Almoço', True,), use_container_width=True)
    row2_c4.button('??? Sessão', on_click=toggle_view, args=('menu_sessao',), use_container_width=True)
    row2_c5.button('?? Saída', on_click=update_status, args=('Saída rápida', True,), use_container_width=True)
    row2_c6.button('?? Ausente', on_click=update_status, args=('Ausente', True,), use_container_width=True)
    
    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            st.markdown("### Selecione a Atividade")
            c_a1, c_a2 = st.columns([1, 1], vertical_alignment="bottom")
            with c_a1:
                atividades_escolhidas = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS)
            with c_a2:
                texto_extra = st.text_input("Detalhe (se necessário):", placeholder="Ex: Assunto específico...")

            col_confirm_1, col_confirm_2 = st.columns(2)
            with col_confirm_1:
                if st.button("Confirmar Atividade", type="primary", use_container_width=True):
                    if atividades_escolhidas:
                        str_atividades = ", ".join(atividades_escolhidas)
                        status_final = f"Atividade: {str_atividades}"
                        if texto_extra: status_final += f" - {texto_extra}"
                        update_status(status_final) 
                        st.session_state.active_view = None; st.rerun()
                    else: st.warning("Selecione pelo menos uma atividade.")
            with col_confirm_2:
                if st.button("Cancelar", use_container_width=True, key='cancel_act'): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_projetos':
        with st.container(border=True):
            st.markdown("### Selecione o Projeto")
            projeto_escolhido = st.selectbox("Projeto:", OPCOES_PROJETOS)
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if st.button("Confirmar Projeto", type="primary", use_container_width=True):
                    status_final = f"Projeto: {projeto_escolhido}"
                    update_status(status_final) 
                    st.session_state.active_view = None; st.rerun()
            with col_p2:
                if st.button("Cancelar", use_container_width=True, key='cancel_proj'): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_reuniao':
        with st.container(border=True):
            st.markdown("### Detalhes da Reunião")
            reuniao_desc = st.text_input("Qual reunião?", placeholder="Ex: Alinhamento equipe, Daily...")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
                if st.button("Confirmar Reunião", type="primary", use_container_width=True):
                    if reuniao_desc:
                        status_final = f"Reunião: {reuniao_desc}"
                        update_status(status_final, force_exit_queue=True) 
                        st.session_state.active_view = None; st.rerun()
                    else: st.warning("Digite o nome da reunião.")
            with col_r2:
                if st.button("Cancelar", use_container_width=True, key='cancel_reuniao'): st.session_state.active_view = None; st.rerun()

    # [NOVO MENU] Menu Treinamento
    if st.session_state.active_view == 'menu_treinamento':
        with st.container(border=True):
            st.markdown("### Detalhes do Treinamento")
            st.info("?? Ao confirmar treinamento, você sairá da fila do bastão.")
            treinamento_desc = st.text_input("Qual Treinamento?", placeholder="Ex: Treinamento Eproc, Curso TJMG...")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                if st.button("Confirmar Treinamento", type="primary", use_container_width=True):
                    if treinamento_desc:
                        status_final = f"Treinamento: {treinamento_desc}"
                        # Force exit queue = True (Comportamento de bloqueio)
                        update_status(status_final, force_exit_queue=True) 
                        st.session_state.active_view = None; st.rerun()
                    else: st.warning("Digite o nome do treinamento.")
            with col_t2:
                if st.button("Cancelar", use_container_width=True, key='cancel_treinamento'): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_sessao':
        with st.container(border=True):
            st.markdown("### Detalhes da Sessão")
            sessao_desc = st.text_input("Qual Câmara/Sessão?", placeholder="Ex: 1ª Cível...")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                if st.button("Confirmar Sessão", type="primary", use_container_width=True):
                    if sessao_desc:
                        status_final = f"Sessão: {sessao_desc}"
                        update_status(status_final, force_exit_queue=True) # Sessão normalmente tira da fila
                        st.session_state.active_view = None; st.rerun()
                    else: st.warning("Digite o nome da sessão.")
            with col_s2:
                if st.button("Cancelar", use_container_width=True, key='cancel_sessao'): st.session_state.active_view = None; st.rerun()
    
    st.markdown("####")
    st.button('?? Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)
    st.markdown("---")
    
    c_tool1, c_tool2, c_tool3, c_tool4, c_tool5, c_tool6 = st.columns(6)
    c_tool1.button("?? Checklist", help="Gerador de Checklist Eproc", use_container_width=True, on_click=toggle_view, args=("checklist",))
    c_tool2.button("?? Chamados", help="Guia de Abertura de Chamados", use_container_width=True, on_click=toggle_view, args=("chamados",))
    c_tool3.button("?? Atendimento", help="Registrar Atendimento", use_container_width=True, on_click=toggle_view, args=("atendimentos",))
    c_tool4.button("? H. Extras", help="Registrar Horas Extras", use_container_width=True, on_click=toggle_view, args=("hextras",))
    c_tool5.button("?? Descanso", help="Jogo e Ranking", use_container_width=True, on_click=toggle_view, args=("descanso",))
    c_tool6.button("?? Erro/Novidade", help="Relatar Erro ou Novidade", use_container_width=True, on_click=toggle_view, args=("erro_novidade",))
        
    if st.session_state.active_view == "checklist":
        with st.container(border=True):
            st.header("Gerador de Checklist (Sessão Eproc)")
            if st.session_state.get('last_reg_status') == "success_sessao":
                st.success("Registro de Sessão enviado com sucesso!")
                if st.session_state.get('html_download_ready') and st.session_state.get('html_content_cache'):
                    filename = st.session_state.get('html_filename', 'Checklist_Sessao.html')
                    st.download_button(label=f"?? Baixar Formulário HTML ({filename})", data=st.session_state.html_content_cache, file_name=filename, mime="text/html")
            st.markdown("### Gerar HTML e Notificar")
            data_eproc = st.date_input("Data da Sessão:", value=get_brazil_time().date(), format="DD/MM/YYYY", key='sessao_data_input')
            camara_eproc = st.selectbox("Selecione a Câmara:", CAMARAS_OPCOES, index=None, key='sessao_camara_select')
            if st.button("Gerar e Enviar HTML", type="primary", use_container_width=True):
                consultor = st.session_state.consultor_selectbox
                if consultor and consultor != 'Selecione um nome': handle_sessao_submission(consultor, camara_eproc, data_eproc)
                else: st.warning("Selecione um consultor no menu acima primeiro.")

    elif st.session_state.active_view == "chamados":
        with st.container(border=True):
            st.header("Padrão abertura de chamados / jiras")
            guide_step = st.session_state.get('chamado_guide_step', 1)
            if guide_step == 1:
                st.subheader("?? Resumo e Passo 1: Testes Iniciais")
                st.markdown("O processo de abertura de chamados segue uma padronização.\n**PASSO 1: Testes Iniciais**\nAntes de abrir o chamado, o consultor(a) deve primeiro realizar os procedimentos de suporte e testes necessários.")
                st.button("Próximo (Passo 2) ??", on_click=set_chamado_step, args=(2,))
            elif guide_step == 2:
                st.subheader("PASSO 2: Checklist de Abertura")
                st.markdown("**1. Dados do Usuário**\n**2. Dados do Processo**\n**3. Descrição do Erro**\n**4. Prints/Vídeo**")
                st.button("Próximo (Passo 3) ??", on_click=set_chamado_step, args=(3,))
            elif guide_step == 3:
                st.subheader("PASSO 3: Registrar e Informar")
                st.markdown("Envie e-mail ao usuário informando o número do chamado.")
                st.button("Próximo (Observações) ??", on_click=set_chamado_step, args=(4,))
            elif guide_step == 4:
                st.subheader("Observações Gerais")
                st.markdown("* Comunicação via e-mail institucional.\n* Atualização no IN.")
                st.button("Entendi! Abrir campo ??", on_click=set_chamado_step, args=(5,))
            elif guide_step == 5:
                st.subheader("Campo de Digitação do Chamado")
                st.text_area("Rascunho do Chamado:", height=300, key="chamado_textarea", label_visibility="collapsed")
                if st.button("Enviar Rascunho", on_click=handle_chamado_submission, use_container_width=True, type="primary"): pass

    elif st.session_state.active_view == "atendimentos":
        with st.container(border=True):
            st.markdown("### Registro de Atendimento")
            at_data = st.date_input("Data:", value=get_brazil_time().date(), format="DD/MM/YYYY", key="at_data")
            at_usuario = st.selectbox("Usuário:", REG_USUARIO_OPCOES, index=None, placeholder="Selecione...", key="at_user")
            at_nome_setor = st.text_input("Nome usuário - Setor:", key="at_setor")
            at_sistema = st.selectbox("Sistema:", REG_SISTEMA_OPCOES, index=None, placeholder="Selecione...", key="at_sys")
            at_descricao = st.text_input("Descrição (até 7 palavras):", key="at_desc")
            at_canal = st.selectbox("Canal:", REG_CANAL_OPCOES, index=None, placeholder="Selecione...", key="at_channel")
            at_desfecho = st.selectbox("Desfecho:", REG_DESFECHO_OPCOES, index=None, placeholder="Selecione...", key="at_outcome")
            default_jira = st.session_state.get('last_jira_number', "")
            at_jira = st.text_input("Número do Jira:", value=default_jira, placeholder="Ex: 1234", key="at_jira_input")
            if st.button("Enviar Atendimento", type="primary", use_container_width=True):
                consultor = st.session_state.consultor_selectbox
                if not consultor or consultor == "Selecione um nome": st.error("Selecione um consultor.")
                else:
                    st.session_state['last_jira_number'] = at_jira
                    handle_atendimento_submission(consultor, at_data, at_usuario, at_nome_setor, at_sistema, at_descricao, at_canal, at_desfecho, at_jira)

    elif st.session_state.active_view == "hextras":
        with st.container(border=True):
            st.markdown("### Registro de Horas Extras")
            he_data = st.date_input("Data:", value=get_brazil_time().date(), format="DD/MM/YYYY")
            he_inicio = st.time_input("Horário de Início:", value=dt_time(18, 0))
            he_tempo = st.text_input("Tempo Total (ex: 2h30):")
            he_motivo = st.text_input("Motivo da Hora Extra:")
            if st.button("Enviar Registro HE", type="primary", use_container_width=True):
                consultor = st.session_state.consultor_selectbox
                if not consultor or consultor == "Selecione um nome": st.error("Selecione um consultor.")
                else: handle_horas_extras_submission(consultor, he_data, he_inicio, he_tempo, he_motivo)

    elif st.session_state.active_view == "descanso":
        with st.container(border=True): handle_simon_game()

    elif st.session_state.active_view == "erro_novidade":
        with st.container(border=True):
            st.markdown("### ?? Registro de Erro ou Novidade")
            with st.expander("?? Ver Exemplo de Preenchimento"):
                st.markdown("""**Título:** Melhoria na Gestão das Procuradorias
**Objetivo:** Permitir que os perfis de Procurador Chefe...
**Relato:** Foram realizados testes...
**Resultado:** O teste não foi bem-sucedido...""")
            en_titulo = st.text_input("Título:")
            en_objetivo = st.text_area("Objetivo:", height=100)
            en_relato = st.text_area("Relato:", height=200)
            en_resultado = st.text_area("Resultado:", height=150)
            if st.button("Enviar Relato", type="primary", use_container_width=True):
                consultor = st.session_state.consultor_selectbox
                if not consultor or consultor == "Selecione um nome": st.error("Selecione um consultor.")
                else:
                    if handle_erro_novidade_submission(consultor, en_titulo, en_objetivo, en_relato, en_resultado):
                        st.success("Relato enviado com sucesso!")
                        st.session_state.active_view = None
                        time.sleep(1.5)
                        st.rerun()
                    else: st.error("Erro no envio.")
    
    st.markdown("---")
    st.markdown("### ?? Links Úteis - Notebooks LM Cesupe")
    st.markdown("""
    * [Notebook Lm Eproc Gabinete](https://notebooklm.google.com/notebook/e2fcf868-1697-4a4c-a7db-fed5560e04ad)
    * [Eproc Cartório](https://notebooklm.google.com/notebook/8b7fd5e6-ee33-4d5e-945c-f763c443846f)
    * [Respostas Padrão e Atendimentos Cesupe](https://notebooklm.google.com/notebook/5504cfb6-174b-4cba-bbd4-ee22f45f60fe)
    """)

with col_disponibilidade:
    st.markdown("###")
    st.toggle("Auxílio HP/Emails/Whatsapp", key='auxilio_ativo', on_change=on_auxilio_change)
    if st.session_state.get('auxilio_ativo'): st.warning("HP/Emails/Whatsapp irão para bastão"); st.image(GIF_URL_NEDRY, width=300)
    st.markdown("---")
    st.header('Status dos(as) Consultores(as)')
    
    ui_lists = {
        'fila': [], 
        'almoco': [], 
        'saida': [], 
        'ausente': [], 
        'atividade_especifica': [], 
        'sessao_especifica': [], 
        'projeto_especifico': [], 
        'reuniao_especifica': [],
        'treinamento_especifico': [], # Nova lista
        'indisponivel': []
    } 

    for nome in CONSULTORES:
        if nome in st.session_state.bastao_queue:
            ui_lists['fila'].append(nome)
        
        status = st.session_state.status_texto.get(nome, 'Indisponível')
        
        if status == '' or status is None: pass
        elif status == 'Almoço': ui_lists['almoco'].append(nome)
        elif status == 'Ausente': ui_lists['ausente'].append(nome)
        elif status == 'Saída rápida': ui_lists['saida'].append(nome)
        elif status == 'Indisponível': 
            if nome not in st.session_state.bastao_queue: ui_lists['indisponivel'].append(nome)
        
        if 'Sessão:' in status:
            match = re.search(r'Sessão: (.*)', status)
            if match: ui_lists['sessao_especifica'].append((nome, match.group(1).split('|')[0].strip()))
        
        if 'Reunião:' in status:
            match = re.search(r'Reunião: (.*)', status)
            if match: ui_lists['reuniao_especifica'].append((nome, match.group(1).split('|')[0].strip()))
            
        if 'Projeto:' in status:
            match = re.search(r'Projeto: (.*)', status)
            if match: ui_lists['projeto_especifico'].append((nome, match.group(1).split('|')[0].strip()))
        
        # [DISPLAY] Captura status de Treinamento
        if 'Treinamento:' in status:
            match = re.search(r'Treinamento: (.*)', status)
            desc_treinamento = match.group(1).split('|')[0].strip() if match else "Geral"
            # Fallback se a descrição estiver vazia
            if not desc_treinamento: desc_treinamento = "Geral"
            ui_lists['treinamento_especifico'].append((nome, desc_treinamento))
            
        if 'Atividade:' in status or status == 'Atendimento':
            if status == 'Atendimento': 
                ui_lists['atividade_especifica'].append((nome, "Atendimento"))
            else:
                match = re.search(r'Atividade: (.*)', status)
                if match: ui_lists['atividade_especifica'].append((nome, match.group(1).split('|')[0].strip()))

    # --- RENDERIZAÇÃO FILA ---
    st.subheader(f'? Na Fila ({len(ui_lists["fila"])})')
    render_order = [c for c in queue if c in ui_lists["fila"]]
    if not render_order: st.markdown('_Ninguém na fila._')
    else:
        for nome in render_order:
            col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment="center")
            key = f'chk_fila_{nome}'
            is_checked = True 
            col_check.checkbox(' ', key=key, value=is_checked, on_change=toggle_queue, args=(nome,), label_visibility='collapsed')
            
            skip_flag = skips.get(nome, False)
            status_atual = st.session_state.status_texto.get(nome, '')
            extra_info = ""
            if "Atividade" in status_atual: extra_info += " ??"
            if "Projeto" in status_atual: extra_info += " ???"

            if nome == responsavel: display = f'<span style="background-color: #FFD700; color: #000; padding: 2px 6px; border-radius: 5px; font-weight: bold;">?? {nome}</span>'
            elif skip_flag: display = f'**{nome}**{extra_info} :orange-background[Pulando ??]'
            else: display = f'**{nome}**{extra_info} :blue-background[Aguardando]'
            col_nome.markdown(display, unsafe_allow_html=True)
    st.markdown('---')

    # --- FUNÇÃO ATUALIZADA: Renderização Segura com HTML ---
    def render_section_detalhada(title, icon, lista_tuplas, tag_color_name, keyword_removal):
        # Mapa de Cores Hexadecimal (Para HTML robusto)
        colors = {
            'orange': '#FFECB3', # Amber 100
            'blue': '#BBDEFB',   # Blue 100
            'teal': '#B2DFDB',   # Teal 100 (CORREÇÃO: Isso evita o erro visual)
            'violet': '#E1BEE7', # Purple 100
            'green': '#C8E6C9',  # Green 100
            'red': '#FFCDD2',    # Red 100
            'grey': '#F5F5F5'    # Grey 100
        }
        bg_hex = colors.get(tag_color_name, '#E0E0E0') # Fallback

        st.subheader(f'{icon} {title} ({len(lista_tuplas)})')
        if not lista_tuplas: st.markdown(f'_Ninguém em {title.lower()}._')
        else:
            for nome, desc in sorted(lista_tuplas, key=lambda x: x[0]):
                col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment="center")
                key_dummy = f'chk_status_{title}_{nome}' 
                col_check.checkbox(' ', key=key_dummy, value=True, on_change=leave_specific_status, args=(nome, keyword_removal), label_visibility='collapsed')
                
                # HTML direto para evitar que o código de markdown vaze
                html_badged = f"""
                <div style="font-size: 16px; margin: 2px 0;">
                    <strong>{nome}</strong>
                    <span style="background-color: {bg_hex}; color: #333; padding: 2px 8px; border-radius: 12px; font-size: 14px; margin-left: 8px; vertical-align: middle;">
                        {desc}
                    </span>
                </div>
                """
                col_nome.markdown(html_badged, unsafe_allow_html=True)
        st.markdown('---')

    def render_section_simples(title, icon, names, tag_color_name):
        colors = {
            'orange': '#FFECB3', 'blue': '#BBDEFB', 'teal': '#B2DFDB', 
            'violet': '#E1BEE7', 'green': '#C8E6C9', 'red': '#FFCDD2', 'grey': '#EEEEEE'
        }
        bg_hex = colors.get(tag_color_name, '#E0E0E0')

        st.subheader(f'{icon} {title} ({len(names)})')
        if not names: st.markdown(f'_Ninguém em {title.lower()}._')
        else:
            for nome in sorted(names):
                col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment="center")
                key_dummy = f'chk_simples_{title}_{nome}'
                if title == 'Indisponível':
                    col_check.checkbox(' ', key=key_dummy, value=False, on_change=enter_from_indisponivel, args=(nome,), label_visibility='collapsed')
                else:
                    col_check.checkbox(' ', key=key_dummy, value=True, on_change=leave_specific_status, args=(nome, title), label_visibility='collapsed')
                
                html_simple = f"""
                <div style="font-size: 16px; margin: 2px 0;">
                    <strong>{nome}</strong>
                    <span style="background-color: {bg_hex}; color: #444; padding: 2px 6px; border-radius: 6px; font-size: 12px; margin-left: 6px; vertical-align: middle; text-transform: uppercase;">
                        {title}
                    </span>
                </div>
                """
                col_nome.markdown(html_simple, unsafe_allow_html=True)
        st.markdown('---')

    render_section_detalhada('Em Demanda', '??', ui_lists['atividade_especifica'], 'orange', 'Atividade')
    render_section_detalhada('Projetos', '???', ui_lists['projeto_especifico'], 'blue', 'Projeto')
    render_section_detalhada('Treinamento', '??', ui_lists['treinamento_especifico'], 'teal', 'Treinamento') # Nova Seção Corrigida
    render_section_detalhada('Reuniões', '??', ui_lists['reuniao_especifica'], 'violet', 'Reunião')
    render_section_simples('Almoço', '???', ui_lists['almoco'], 'red')
    render_section_detalhada('Sessão', '???', ui_lists['sessao_especifica'], 'green', 'Sessão')
    render_section_simples('Saída rápida', '??', ui_lists['saida'], 'red')
    render_section_simples('Ausente', '??', ui_lists['ausente'], 'violet') 
    render_section_simples('Indisponível', '?', ui_lists['indisponivel'], 'grey')

now_utc = datetime.utcnow()
now_br = get_brazil_time()
last_run_date = st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()

if now_br.hour >= 20 and now_br.date() > last_run_date:
    print(f"TRIGGER: Enviando relatório diário. Agora (BRT): {now_br}, Última Execução: {st.session_state.report_last_run_date}")
    send_daily_report()
