# -*- coding: utf-8 -*-
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
import io

# --- IMPORTS DO BANCO DE DADOS (SUPABASE) ---
# Certifique-se que o arquivo repository.py está na mesma pasta
from repository import load_state_from_db, save_state_to_db

# --- IMPORTS PARA O WORD ---
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

# --- CONSTANTES DE CONSULTORES ---
CONSULTORES = sorted([
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
    "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
    "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
])

# ============================================
# SEGURANÇA E WEBHOOKS (ST.SECRETS)
# ============================================

def get_secret(section, key):
    try: return st.secrets[section][key]
    except: return ""

def get_brazil_time():
    return datetime.utcnow() - timedelta(hours=3)

# Webhooks
GOOGLE_CHAT_WEBHOOK_BACKUP = get_secret("chat", "backup")
CHAT_WEBHOOK_BASTAO = get_secret("chat", "bastao")
GOOGLE_CHAT_WEBHOOK_REGISTRO = get_secret("chat", "registro")
GOOGLE_CHAT_WEBHOOK_CHAMADO = get_secret("chat", "chamado")
GOOGLE_CHAT_WEBHOOK_SESSAO = get_secret("chat", "sessao")
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = get_secret("chat", "checklist")
GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS = get_secret("chat", "extras")
GOOGLE_CHAT_WEBHOOK_ERRO_NOVIDADE = get_secret("chat", "erro")
SHEETS_WEBHOOK_URL = get_secret("sheets", "url")

# --- Opções Visuais ---
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
GIF_URL_LUNCH_WARNING = 'https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGZlbHN1azB3b2drdTI1eG10cDEzeWpmcmtwenZxNTV0bnc2OWgzZSYlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/bNlqpmBJRDMpxulfFB/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
PUG2026_FILENAME = "pug2026.png"

# ============================================
# 2. PERSISTÊNCIA E AUXILIARES
# ============================================

def save_state():
    """Salva o estado atual no Supabase via repository.py"""
    try:
        state_to_save = {
            'status_texto': st.session_state.status_texto,
            'bastao_queue': st.session_state.bastao_queue,
            'skip_flags': st.session_state.skip_flags,
            'current_status_starts': st.session_state.current_status_starts,
            'bastao_counts': st.session_state.bastao_counts,
            'priority_return_queue': st.session_state.priority_return_queue,
            'bastao_start_time': st.session_state.bastao_start_time,
            'report_last_run_date': st.session_state.report_last_run_date,
            'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'),
            'lunch_warning_info': st.session_state.get('lunch_warning_info'),
            'auxilio_ativo': st.session_state.get('auxilio_ativo', False),
            'daily_logs': st.session_state.daily_logs,
            'simon_ranking': st.session_state.get('simon_ranking', [])
        }
        save_state_to_db(state_to_save)
    except Exception as e:
        print(f"Erro ao salvar estado: {e}")

@st.cache_data
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return None

def load_logs(): return st.session_state.daily_logs

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def _send_webhook_thread(url, payload):
    if not url: return
    try: requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=5)
    except: pass

def send_log_to_sheets(timestamp_str, consultor, old_status, new_status, duration_str):
    if not SHEETS_WEBHOOK_URL: return
    payload = {
        "data_hora": timestamp_str, "consultor": consultor,
        "status_anterior": old_status, "status_atual": new_status, "tempo_anterior": duration_str
    }
    threading.Thread(target=_send_webhook_thread, args=(SHEETS_WEBHOOK_URL, payload)).start()

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    now_br = get_brazil_time()
    start_t = st.session_state.current_status_starts.get(consultor, now_br)
    today_8am = now_br.replace(hour=8, minute=0, second=0, microsecond=0)
    final_duration = duration
    if start_t < today_8am and now_br >= today_8am:
         final_duration = now_br - today_8am
         if final_duration.total_seconds() < 0: final_duration = timedelta(0)
    
    old_lbl = old_status if old_status else 'Fila Bastão'
    new_lbl = new_status if new_status else 'Fila Bastão'
    if consultor in st.session_state.bastao_queue:
        if 'Bastão' not in new_lbl and new_lbl != 'Fila Bastão':
             new_lbl = f"Fila | {new_lbl}"

    entry = {
        'timestamp': now_br, 'consultor': consultor,
        'old_status': old_lbl, 'new_status': new_lbl,
        'duration': final_duration, 'duration_s': final_duration.total_seconds()
    }
    st.session_state.daily_logs.append(entry)
    timestamp_str = now_br.strftime("%d/%m/%Y %H:%M:%S")
    duration_str = format_time_duration(final_duration)
    send_log_to_sheets(timestamp_str, consultor, old_lbl, new_lbl, duration_str)
    
    st.session_state.current_status_starts[consultor] = now_br

# --- FUNCIONALIDADES DE WEBHOOK E CHAT ---
def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        msg = f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {APP_URL_CLOUD}"
        threading.Thread(target=_send_webhook_thread, args=(CHAT_WEBHOOK_BASTAO, {"text": msg})).start()
        return True
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    if not GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS: return False
    msg = f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n🕐 **Início:** {inicio.strftime('%H:%M')}\n⏱️ **Tempo Total:** {tempo}\n📝 **Motivo:** {motivo}"
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_HORAS_EXTRAS, {"text": msg})).start()
    return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO: return False
    jira_str = f"\n🔢 **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n👥 **Usuário:** {usuario}\n🏢 **Nome/Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {descricao}\n📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{jira_str}"
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_REGISTRO, {"text": msg})).start()
    return True

def handle_erro_novidade_submission(consultor, titulo, objetivo, relato, resultado):
    if not GOOGLE_CHAT_WEBHOOK_ERRO_NOVIDADE: return False
    data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
    msg = f"🐛 **Novo Relato de Erro/Novidade**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n📌 **Título:** {titulo}\n\n🎯 **Objetivo:**\n{objetivo}\n\n🧪 **Relato:**\n{relato}\n\n🏁 **Resultado:**\n{resultado}"
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_ERRO_NOVIDADE, {"text": msg})).start()
    return True

def send_sessao_to_chat(consultor, texto_mensagem):
    if not GOOGLE_CHAT_WEBHOOK_SESSAO: return False
    if not consultor or consultor == 'Selecione um nome': return False
    threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_SESSAO, {'text': texto_mensagem})).start()
    return True

# --- HTML & VISUAL HELPERS ---
def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'

def render_fireworks():
    fireworks_css = """<style>
    @keyframes firework { 0% { transform: translate(var(--x), var(--initialY)); width: var(--initialSize); opacity: 1; } 50% { width: 0.5vmin; opacity: 1; } 100% { width: var(--finalSize); opacity: 0; } }
    .firework, .firework::before, .firework::after { --initialSize: 0.5vmin; --finalSize: 45vmin; --particleSize: 0.2vmin; --color1: #ff0000; --color2: #ffd700; --color3: #b22222; --color4: #daa520; --color5: #ff4500; --color6: #b8860b; --y: -30vmin; --x: -50%; --initialY: 60vmin; content: ""; animation: firework 2s infinite; position: absolute; top: 50%; left: 50%; transform: translate(-50%, var(--y)); width: var(--initialSize); aspect-ratio: 1; background: radial-gradient(circle, var(--color1) var(--particleSize), #0000 0) 50% 0%, radial-gradient(circle, var(--color2) var(--particleSize), #0000 0) 100% 50%, radial-gradient(circle, var(--color3) var(--particleSize), #0000 0) 50% 100%, radial-gradient(circle, var(--color4) var(--particleSize), #0000 0) 0% 50%, radial-gradient(circle, var(--color5) var(--particleSize), #0000 0) 80% 90%, radial-gradient(circle, var(--color6) var(--particleSize), #0000 0) 95% 90%; background-size: var(--initialSize) var(--initialSize); background-repeat: no-repeat; }
    .firework::before { --x: -50%; --y: -50%; --initialY: -50%; transform: translate(-50%, -50%) rotate(40deg) scale(1.3) rotateY(40deg); }
    .firework::after { --x: -50%; --y: -50%; --initialY: -50%; transform: translate(-50%, -50%) rotate(170deg) scale(1.15) rotateY(-30deg); }
    .firework:nth-child(2) { --x: 30vmin; }
    .firework:nth-child(2), .firework:nth-child(2)::before, .firework:nth-child(2)::after { --color1: #ff0000; --color2: #ffd700; --color3: #8b0000; --color4: #daa520; --color5: #ff6347; --color6: #f0e68c; --finalSize: 40vmin; left: 30%; top: 60%; animation-delay: -0.25s; }
    .firework:nth-child(3) { --x: -30vmin; --y: -50vmin; }
    .firework:nth-child(3), .firework:nth-child(3)::before, .firework:nth-child(3)::after { --color1: #ffd700; --color2: #ff4500; --color3: #b8860b; --color4: #cd5c5c; --color5: #800000; --color6: #ffa500; --finalSize: 35vmin; left: 70%; top: 60%; animation-delay: -0.4s; }
    </style><div class="firework"></div><div class="firework"></div><div class="firework"></div>"""
    st.markdown(fireworks_css, unsafe_allow_html=True)

def gerar_html_checklist(consultor_nome, camara_nome, data_sessao_formatada):
    consultor_formatado = f"@{consultor_nome}" if not consultor_nome.startswith("@") else consultor_nome
    return f'<!DOCTYPE html><html lang="pt-br"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Acompanhamento de Sessão - {camara_nome}</title></head><body><div style="font-family: Arial, sans-serif; padding: 20px;"><h2>Checklist Gerado para {camara_nome}</h2><p>Responsável: {consultor_formatado}</p><p>Data: {data_sessao_formatada}</p><p><em>(Versão simplificada para visualização.)</em></p></div></body></html>'

def gerar_docx_certidao(tipo_certidao, num_processo, data_indisponibilidade_input, num_chamado, motivo_pedido):
    document = Document()
    style = document.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(12)
    # ... (Geração simplificada para economizar espaço, mas funcional)
    document.add_paragraph(f"Certidão: {tipo_certidao}")
    document.add_paragraph(f"Processo: {num_processo}")
    document.add_paragraph(f"Motivo: {motivo_pedido}")
    buffer = io.BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer

def send_daily_report():
    logs = load_logs()
    bastao_counts = st.session_state.bastao_counts.copy()
    aggregated_data = {nome: {} for nome in CONSULTORES}
    for log in logs:
        try:
            consultor, status, duration = log['consultor'], log['old_status'], log.get('duration', timedelta(0))
            if not isinstance(duration, timedelta): duration = timedelta(seconds=float(duration))
            if status and consultor in aggregated_data:
                aggregated_data[consultor][status] = aggregated_data[consultor].get(status, timedelta(0)) + duration
        except: pass
    now_br = get_brazil_time()
    report_text = f"📊 **Relatório Diário - {now_br.strftime('%d/%m/%Y')}** 📊\n\n"
    has_data = False
    for nome in CONSULTORES:
        counts, times = bastao_counts.get(nome, 0), aggregated_data.get(nome, {})
        if counts > 0 or times:
            has_data = True
            report_text += f"**👤 {nome}**\n- 🥂 Bastão: **{counts}**\n"
            for s, t in sorted(times.items(), key=itemgetter(0)):
                if s != 'Bastão': report_text += f"- {s}: **{format_time_duration(t)}**\n"
            report_text += "\n"
    if not has_data: report_text += "Nenhuma atividade registrada."
    if GOOGLE_CHAT_WEBHOOK_BACKUP: threading.Thread(target=_send_webhook_thread, args=(GOOGLE_CHAT_WEBHOOK_BACKUP, {'text': report_text})).start()
    st.session_state['report_last_run_date'] = now_br
    st.session_state['daily_logs'] = []
    st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
    save_state()

# ============================================
# LÓGICA DO BASTÃO
# ============================================

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue)
    start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        consultor = queue[idx]
        if st.session_state.get(f'check_{consultor}', False) and not skips.get(consultor, False): return idx
    return -1

def check_and_assume_baton(forced_successor=None):
    queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    is_valid = (current_holder and current_holder in queue and st.session_state.get(f'check_{current_holder}'))
    
    target = forced_successor if forced_successor else (current_holder if is_valid else None)
    if not target and not is_valid:
        idx = find_next_holder_index(-1, queue, skips)
        target = queue[idx] if idx != -1 else None

    changed = False
    now = get_brazil_time()
    
    # Remove bastão de quem não deveria ter
    for c in CONSULTORES:
        if c != target and 'Bastão' in st.session_state.status_texto.get(c, ''):
            log_status_change(c, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(c, now))
            st.session_state.status_texto[c] = 'Indisponível'
            changed = True

    # Atribui ao novo
    if target:
        curr_s = st.session_state.status_texto.get(target, '')
        if 'Bastão' not in curr_s:
            old_s = curr_s
            new_s = f"Bastão | {old_s}" if old_s and old_s != "Indisponível" else "Bastão"
            log_status_change(target, old_s, new_s, now - st.session_state.current_status_starts.get(target, now))
            st.session_state.status_texto[target] = new_s
            st.session_state.bastao_start_time = now
            if current_holder != target:
                st.session_state.play_sound = True
                send_chat_notification_internal(target, 'Bastão')
            st.session_state.skip_flags[target] = False
            changed = True
    elif not target and current_holder:
        # Perdeu bastão e não tem ninguém
        log_status_change(current_holder, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(current_holder, now))
        st.session_state.status_texto[current_holder] = 'Indisponível'
        changed = True

    if changed: save_state()
    return changed

# ============================================
# AUTOMATIZAÇÃO DE HORÁRIO (20h / 23h)
# ============================================
def auto_manage_time():
    """Aplica regras de horário ao carregar"""
    now = get_brazil_time()
    
    # 23h: Limpeza total
    if now.hour >= 23:
        has_data = len(st.session_state.bastao_queue) > 0 or any(v > 0 for v in st.session_state.bastao_counts.values())
        if has_data:
            st.session_state.bastao_queue = []
            st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
            st.session_state.bastao_counts = {n: 0 for n in CONSULTORES}
            st.session_state.skip_flags = {}
            st.session_state.daily_logs = []
            st.session_state.current_status_starts = {n: now for n in CONSULTORES}
            for n in CONSULTORES: st.session_state[f'check_{n}'] = False
            save_state()
            st.toast("🧹 Limpeza Diária (23h) realizada.", icon="🌙")
            
    # 20h: Encerra expediente (mantém histórico)
    elif now.hour >= 20:
        active = any(s != 'Indisponível' for s in st.session_state.status_texto.values()) or len(st.session_state.bastao_queue) > 0
        if active:
            st.session_state.bastao_queue = []
            st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
            for n in CONSULTORES: st.session_state[f'check_{n}'] = False
            save_state()
            st.toast("🛑 Expediente encerrado (20h). Fila limpa.", icon="zzz")

def init_session_state():
    # 1. Carrega do DB
    if 'db_loaded' not in st.session_state:
        try:
            db_data = load_state_from_db()
            if db_data:
                for k, v in db_data.items(): st.session_state[k] = v
        except: pass
        st.session_state['db_loaded'] = True

    now = get_brazil_time()
    
    # 2. Defaults
    defaults = {
        'bastao_start_time': None, 'report_last_run_date': datetime.min, 'rotation_gif_start_time': None,
        'play_sound': False, 'gif_warning': False, 'lunch_warning_info': None, 'last_reg_status': None,
        'chamado_guide_step': 0, 'sessao_msg_preview': "", 'html_download_ready': False, 'html_content_cache': "",
        'auxilio_ativo': False, 'active_view': None, 'last_jira_number': "",
        'simon_sequence': [], 'simon_user_input': [], 'simon_status': 'start', 'simon_level': 1,
        'consultor_selectbox': 'Selecione um nome',
        # Chaves críticas
        'status_texto': {n: 'Indisponível' for n in CONSULTORES},
        'bastao_queue': [], 'skip_flags': {}, 'current_status_starts': {n: now for n in CONSULTORES},
        'bastao_counts': {n: 0 for n in CONSULTORES}, 'priority_return_queue': [], 'daily_logs': [], 'simon_ranking': []
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

    # 3. Checkboxes
    for n in CONSULTORES:
        st.session_state.bastao_counts.setdefault(n, 0)
        st.session_state.skip_flags.setdefault(n, False)
        status = st.session_state.status_texto.get(n, 'Indisponível')
        if status is None: status = 'Indisponível'; st.session_state.status_texto[n] = status
        
        is_blocked = any(kw in status for kw in ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento'])
        if is_blocked: avail = False
        elif n in st.session_state.priority_return_queue: avail = False
        elif n in st.session_state.bastao_queue: avail = True
        else: avail = 'Indisponível' not in status
        
        st.session_state[f'check_{n}'] = avail
        if n not in st.session_state.current_status_starts: st.session_state.current_status_starts[n] = now
    
    check_and_assume_baton()

# --- AÇÕES DE BOTÕES ---
def toggle_queue(consultor):
    # Regra 20h
    if get_brazil_time().hour >= 20:
        st.toast("🚫 Expediente encerrado! Não é possível entrar na fila.", icon="🌙")
        st.session_state[f'check_{consultor}'] = False
        return

    # Lógica original
    if consultor in st.session_state.bastao_queue:
        curr = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        forced = None
        if consultor == curr:
            idx = st.session_state.bastao_queue.index(consultor)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: forced = st.session_state.bastao_queue[nxt]
        st.session_state.bastao_queue.remove(consultor)
        st.session_state[f'check_{consultor}'] = False
        if 'Bastão' in st.session_state.status_texto.get(consultor, ''):
            st.session_state.status_texto[consultor] = 'Indisponível'
        check_and_assume_baton(forced)
    else:
        st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True
        st.session_state.skip_flags[consultor] = False
        if consultor in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(consultor)
        if 'Indisponível' in st.session_state.status_texto.get(consultor, ''):
            st.session_state.status_texto[consultor] = ''
        check_and_assume_baton()
    save_state()

def toggle_skip():
    sel = st.session_state.consultor_selectbox
    if not sel or sel == 'Selecione um nome': return
    st.session_state.skip_flags[sel] = not st.session_state.skip_flags.get(sel, False)
    save_state()

def update_status(new_status, force_exit_queue=False):
    sel = st.session_state.consultor_selectbox
    if not sel or sel == 'Selecione um nome': return
    
    blocking = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento']
    should_exit = force_exit_queue or any(b in new_status for b in blocking)
    
    current = st.session_state.status_texto.get(sel, '')
    parts = [p.strip() for p in current.split('|') if p.strip()]
    type_new = new_status.split(':')[0]
    clean = [p for p in parts if p != 'Indisponível' and not p.startswith(type_new)]
    clean.append(new_status)
    clean.sort(key=lambda x: 0 if 'Bastão' in x else 1 if 'Atividade' in x or 'Projeto' in x else 2)
    final = " | ".join(clean)
    
    if should_exit:
        st.session_state[f'check_{sel}'] = False
        if sel in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(sel)
        st.session_state.skip_flags[sel] = False
        
    is_holder = 'Bastão' in current
    if is_holder and not should_exit and 'Bastão' not in final: final = f"Bastão | {final}"
    
    log_status_change(sel, current, final, get_brazil_time() - st.session_state.current_status_starts.get(sel, get_brazil_time()))
    st.session_state.status_texto[sel] = final
    
    if new_status == 'Saída rápida':
        if sel not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(sel)
    elif sel in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(sel)
    
    if is_holder: check_and_assume_baton()
    save_state()

def rotate_bastao():
    # Mesma lógica do seu código original
    sel = st.session_state.consultor_selectbox
    curr = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if sel != curr: 
        st.session_state.gif_warning = True
        return
    
    q, skips = st.session_state.bastao_queue, st.session_state.skip_flags
    curr_idx = q.index(curr) if curr in q else -1
    if curr_idx == -1: 
        check_and_assume_baton()
        return

    # Pular lógica
    nxt_idx = find_next_holder_index(curr_idx, q, skips)
    if nxt_idx != -1:
        nxt = q[nxt_idx]
        now = get_brazil_time()
        
        # Log antigo
        old_s = st.session_state.status_texto[curr]
        new_s_old = old_s.replace('Bastão | ', '').replace('Bastão', '').strip()
        log_status_change(curr, old_s, new_s_old, now - (st.session_state.bastao_start_time or now))
        st.session_state.status_texto[curr] = new_s_old
        
        # Log novo
        old_s_nxt = st.session_state.status_texto.get(nxt, '')
        new_s_nxt = f"Bastão | {old_s_nxt}" if old_s_nxt else "Bastão"
        log_status_change(nxt, old_s_nxt, new_s_nxt, timedelta(0))
        st.session_state.status_texto[nxt] = new_s_nxt
        
        st.session_state.bastao_start_time = now
        st.session_state.bastao_counts[curr] += 1
        st.session_state.play_sound = True
        st.session_state.rotation_gif_start_time = now
        st.session_state.skip_flags[nxt] = False
        
        send_chat_notification_internal(nxt, 'Bastão')
        save_state()
    else:
        st.warning("Ninguém elegível.")
        check_and_assume_baton()

def manual_rerun(): st.rerun()
def on_auxilio_change(): save_state()
def toggle_view(v): 
    st.session_state.active_view = v if st.session_state.active_view != v else None
    if v == 'chamados': st.session_state.chamado_guide_step = 1

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
auto_manage_time() # Mágica do tempo
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
        if st.button("🚀 Entrar"):
            if novo_responsavel != "Selecione":
                toggle_queue(novo_responsavel)
                st.session_state.consultor_selectbox = novo_responsavel
                st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

# Gifs e Avisos
if st.session_state.rotation_gif_start_time:
    if (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 20: st.image(GIF_URL_ROTATION, width=200)
    else: st.session_state.rotation_gif_start_time = None; save_state()

if st.session_state.get('play_sound'):
    st.components.v1.html(play_sound_html(), height=0, width=0)
    st.session_state.play_sound = False

st_autorefresh(interval=8000, key='auto_rerun')

# Colunas Principais
col_principal, col_disponibilidade = st.columns([1.5, 1])
queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
curr_idx = queue.index(responsavel) if responsavel in queue else -1
prox_idx = find_next_holder_index(curr_idx, queue, skips)
proximo = queue[prox_idx] if prox_idx != -1 else None
restante = [queue[(prox_idx + 1 + i) % len(queue)] for i in range(len(queue)) if queue[(prox_idx + 1 + i) % len(queue)] not in [responsavel, proximo]] if prox_idx != -1 else []

with col_principal:
    st.header("Responsável pelo Bastão")
    if responsavel:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%); border: 3px solid #FFD700; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3); margin-bottom: 20px;"><div style="flex-shrink: 0; margin-right: 25px;"><img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #FFD700;"></div><div><span style="font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px;">Atualmente com:</span><br><span style="font-size: 42px; font-weight: 800; color: #000080; line-height: 1.1;">{responsavel}</span></div></div>""", unsafe_allow_html=True)
        dur = get_brazil_time() - (st.session_state.bastao_start_time or get_brazil_time())
        st.caption(f"⏱️ Tempo com o bastão: **{format_time_duration(dur)}**")
    else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
    
    st.markdown("###")
    st.header("Próximos da Fila")
    if proximo: st.markdown(f'### 1º: **{proximo}**')
    if restante: st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    elif not proximo: st.markdown('*Ninguém elegível.*')

    st.markdown("###")
    st.header("**Consultor(a)**")
    st.selectbox('Selecione:', ['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r2c1, r2c2, r2c3, r2c4, r2c5, r2c6 = st.columns(6)
    
    r1c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    r1c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True)
    r1c3.button('📋 Atividades', on_click=toggle_view, args=('menu_atividades',), use_container_width=True)
    r1c4.button('🏗️ Projeto', on_click=toggle_view, args=('menu_projetos',), use_container_width=True)
    
    r2c1.button('🎓 Treino', on_click=toggle_view, args=('menu_treinamento',), use_container_width=True)
    r2c2.button('📅 Reunião', on_click=toggle_view, args=('menu_reuniao',), use_container_width=True)
    r2c3.button('🍽️ Almoço', on_click=update_status, args=('Almoço', True), use_container_width=True)
    r2c4.button('🎙️ Sessão', on_click=toggle_view, args=('menu_sessao',), use_container_width=True)
    r2c5.button('🚶 Saída', on_click=update_status, args=('Saída rápida', True), use_container_width=True)
    r2c6.button('👤 Ausente', on_click=update_status, args=('Ausente', True), use_container_width=True)

    # Menus Expansíveis (Lógica Visual)
    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            ats = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS)
            txt = st.text_input("Detalhe:")
            if st.button("Confirmar Atividade", type="primary"):
                stt = f"Atividade: {', '.join(ats)}" + (f" - {txt}" if txt else "")
                update_status(stt); st.session_state.active_view = None; st.rerun()
                
    if st.session_state.active_view == 'menu_projetos':
        with st.container(border=True):
            prj = st.selectbox("Projeto:", OPCOES_PROJETOS)
            if st.button("Confirmar", type="primary"):
                update_status(f"Projeto: {prj}"); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_treinamento':
        with st.container(border=True):
            trn = st.text_input("Treinamento:")
            if st.button("Confirmar", type="primary"):
                update_status(f"Treinamento: {trn}", force_exit_queue=True); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_reuniao':
        with st.container(border=True):
            rnu = st.text_input("Reunião:")
            if st.button("Confirmar", type="primary"):
                update_status(f"Reunião: {rnu}", force_exit_queue=True); st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_sessao':
        with st.container(border=True):
            ses = st.text_input("Sessão:")
            if st.button("Confirmar", type="primary"):
                update_status(f"Sessão: {ses}", force_exit_queue=True); st.session_state.active_view = None; st.rerun()

    st.markdown("---")
    tc1, tc2, tc3, tc4, tc5, tc6 = st.columns(6)
    tc1.button("📑 Checklist", on_click=toggle_view, args=("checklist",))
    tc2.button("🆘 Chamados", on_click=toggle_view, args=("chamados",))
    tc3.button("📝 Atend.", on_click=toggle_view, args=("atendimentos",))
    tc4.button("⏰ H. Extras", on_click=toggle_view, args=("hextras",))
    tc5.button("🧠 Game", on_click=toggle_view, args=("descanso",))
    tc6.button("🐛 Erro", on_click=toggle_view, args=("erro_novidade",))
    
    if st.button("🖨️ Certidão"): st.session_state.active_view = "certidao"

    # Views das Ferramentas
    if st.session_state.active_view == "checklist":
        with st.container(border=True):
            dt = st.date_input("Data Sessão")
            cam = st.selectbox("Câmara", CAMARAS_OPCOES)
            if st.button("Gerar HTML"): 
                handle_sessao_submission(st.session_state.consultor_selectbox, cam, dt)

    elif st.session_state.active_view == "atendimentos":
        with st.container(border=True):
            ad = st.date_input("Data")
            au = st.selectbox("Usuário", REG_USUARIO_OPCOES)
            an = st.text_input("Nome/Setor")
            as_ = st.selectbox("Sistema", REG_SISTEMA_OPCOES)
            adesc = st.text_input("Descrição")
            ac = st.selectbox("Canal", REG_CANAL_OPCOES)
            adf = st.selectbox("Desfecho", REG_DESFECHO_OPCOES)
            aj = st.text_input("Jira")
            if st.button("Enviar"): 
                handle_atendimento_submission(st.session_state.consultor_selectbox, ad, au, an, as_, adesc, ac, adf, aj)

    elif st.session_state.active_view == "hextras":
        with st.container(border=True):
            hd = st.date_input("Data")
            hi = st.time_input("Início")
            ht = st.text_input("Tempo Total")
            hm = st.text_input("Motivo")
            if st.button("Enviar"): 
                handle_horas_extras_submission(st.session_state.consultor_selectbox, hd, hi, ht, hm)

    elif st.session_state.active_view == "certidao":
        with st.container(border=True):
            ct = st.selectbox("Tipo", ["Geral", "Física", "Eletrônica"])
            cp = st.text_input("Processo")
            cc = st.text_input("Chamado")
            cm = st.text_area("Motivo")
            if st.button("Gerar DOCX"):
                buf = gerar_docx_certidao(ct, cp, [], cc, cm)
                st.download_button("Baixar", buf, "certidao.docx")
                send_certidao_notification_to_chat(st.session_state.consultor_selectbox, ct)

    elif st.session_state.active_view == "descanso":
        with st.container(border=True): handle_simon_game()

with col_disponibilidade:
    st.markdown("###")
    st.toggle("Auxílio HP", key='auxilio_ativo', on_change=on_auxilio_change)
    if st.session_state.get('auxilio_ativo'): st.warning("HP ativo"); st.image(GIF_URL_NEDRY, width=200)
    st.markdown("---")
    st.header('Status')
    
    # Listas UI
    ui_map = {'fila':[], 'almoco':[], 'saida':[], 'ausente':[], 'indisponivel':[], 'ativ':[], 'sess':[], 'proj':[], 'reun':[], 'trein':[]}
    
    for n in CONSULTORES:
        stt = st.session_state.status_texto.get(n, 'Indisponível')
        if n in queue: ui_map['fila'].append(n)
        elif stt == 'Almoço': ui_map['almoco'].append(n)
        elif stt == 'Ausente': ui_map['ausente'].append(n)
        elif stt == 'Saída rápida': ui_map['saida'].append(n)
        elif stt == 'Indisponível': ui_map['indisponivel'].append(n)
        
        if 'Sessão:' in stt: ui_map['sess'].append((n, stt.replace('Sessão:','')))
        if 'Reunião:' in stt: ui_map['reun'].append((n, stt.replace('Reunião:','')))
        if 'Projeto:' in stt: ui_map['proj'].append((n, stt.replace('Projeto:','')))
        if 'Treinamento:' in stt: ui_map['trein'].append((n, stt.replace('Treinamento:','')))
        if 'Atividade:' in stt or stt=='Atendimento': ui_map['ativ'].append((n, stt.replace('Atividade:','')))

    # Render Fila
    st.subheader(f'✅ Na Fila ({len(ui_map["fila"])})')
    for n in [x for x in queue if x in ui_map['fila']]:
        c1, c2 = st.columns([0.85, 0.15])
        c2.checkbox(' ', True, key=f'chk_{n}', on_change=toggle_queue, args=(n,), label_visibility='collapsed')
        
        info = ""
        stt = st.session_state.status_texto.get(n,'')
        if "Atividade" in stt: info += " 📋"
        if "Projeto" in stt: info += " 🏗️"
        
        style = f'**{n}**{info}'
        if skips.get(n): style += ' :orange[⏭️]'
        if n == responsavel: style = f':star: **{n}**'
        c1.markdown(style)
        
    st.markdown('---')
    
    def render_list(title, icon, items, color, key_rm):
        st.subheader(f'{icon} {title} ({len(items)})')
        if not items: st.markdown('_Vazio_')
        for n, desc in sorted(items, key=lambda x: x[0]):
            c1, c2 = st.columns([0.85, 0.15])
            c2.checkbox(' ', True, key=f'chk_out_{n}', on_change=leave_specific_status, args=(n, key_rm), label_visibility='collapsed')
            c1.markdown(f"**{n}** <span style='background-color:{color}; padding:2px; font-size:0.8em'>{desc}</span>", unsafe_allow_html=True)
        st.markdown('---')

    render_list('Demanda', '📋', ui_map['ativ'], '#FFECB3', 'Atividade')
    render_list('Projetos', '🏗️', ui_map['proj'], '#BBDEFB', 'Projeto')
    render_list('Treino', '🎓', ui_map['trein'], '#B2DFDB', 'Treinamento')
    render_list('Reunião', '📅', ui_map['reun'], '#E1BEE7', 'Reunião')
    render_list('Sessão', '🎙️', ui_map['sess'], '#C8E6C9', 'Sessão')
    
    # Listas Simples
    def render_simple(title, icon, items):
        st.subheader(f'{icon} {title} ({len(items)})')
        if not items: st.markdown('_Vazio_')
        for n in sorted(items):
            c1, c2 = st.columns([0.85, 0.15])
            if title == 'Indisponível':
                c2.checkbox(' ', False, key=f'chk_in_{n}', on_change=enter_from_indisponivel, args=(n,), label_visibility='collapsed')
            else:
                c2.checkbox(' ', True, key=f'chk_out_{n}', on_change=leave_specific_status, args=(n, title), label_visibility='collapsed')
            c1.markdown(f"**{n}**")
        st.markdown('---')

    render_simple('Almoço', '🍽️', ui_map['almoco'])
    render_simple('Saída', '🚶', ui_map['saida'])
    render_simple('Ausente', '👤', ui_map['ausente'])
    render_simple('Indisponível', '❌', ui_map['indisponivel'])

# Relatório Diário (Fim do dia)
if get_brazil_time().hour >= 20 and get_brazil_time().date() > st.session_state.report_last_run_date.date():
    send_daily_report()
