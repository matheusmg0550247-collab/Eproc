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
from repository import load_state_from_db, save_state_to_db

# --- IMPORTS DO UTILS (Helpers) ---
from utils import (
    get_brazil_time, get_secret, send_to_chat, gerar_docx_certidao, 
    get_img_as_base64
)

# --- CONSTANTES DE CONSULTORES ---
CONSULTORES = sorted([
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
    "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
    "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
])

# --- CONSTANTES GERAIS ---
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

# --- IMAGENS E ASSETS ---
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_LUNCH_WARNING = 'https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGZlbHN1azB3b2drdTI1eG10cDEzeWpmcmtwenZxNTV0bnc2OWgzZSYlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/bNlqpmBJRDMpxulfFB/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
PUG2026_FILENAME = "pug2026.png"

# Webhook Sheets
SHEETS_WEBHOOK_URL = get_secret("sheets", "url")

# ============================================
# 2. PERSISTÊNCIA E LOGS
# ============================================

def save_state():
    """Salva o estado atual no Supabase via repository.py"""
    try:
        # Monta o dicionário com tudo o que precisamos salvar
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
    
    if consultor not in st.session_state.current_status_starts:
        st.session_state.current_status_starts[consultor] = now_br
    st.session_state.current_status_starts[consultor] = now_br

# --- FUNCIONALIDADES DE WEBHOOK E CHAT ---
def send_chat_notification_internal(consultor, status):
    if status == 'Bastão':
        msg = f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {APP_URL_CLOUD}"
        send_to_chat("bastao", msg)
        return True
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    msg = f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n🕐 **Início:** {inicio.strftime('%H:%M')}\n⏱️ **Tempo Total:** {tempo}\n📝 **Motivo:** {motivo}"
    send_to_chat("extras", msg)
    return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    jira_str = f"\n🔢 **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n👥 **Usuário:** {usuario}\n🏢 **Nome/Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {descricao}\n📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{jira_str}"
    send_to_chat("registro", msg)
    return True

def handle_erro_novidade_submission(consultor, titulo, objetivo, relato, resultado):
    data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
    msg = f"🐛 **Novo Relato de Erro/Novidade**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n📌 **Título:** {titulo}\n\n🎯 **Objetivo:**\n{objetivo}\n\n🧪 **Relato:**\n{relato}\n\n🏁 **Resultado:**\n{resultado}"
    send_to_chat("erro", msg)
    return True

def send_sessao_to_chat_fn(consultor, texto_mensagem):
    if not consultor or consultor == 'Selecione um nome': return False
    send_to_chat("sessao", texto_mensagem)
    return True

def send_certidao_notification_to_chat(consultor, tipo):
    msg = f"Consultor {consultor} solicitou uma certidão ({tipo}) de indisponibilidade. Modelo em word encontra-se na pasta do servidor para envio."
    send_to_chat("certidao", msg)
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
    today_str = now_br.strftime("%d/%m/%Y")
    report_text = f"📊 **Relatório Diário - {today_str}** 📊\n\n"
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
    send_to_chat("backup", report_text)
    st.session_state['report_last_run_date'] = now_br
    st.session_state['daily_logs'] = []
    st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
    save_state()

# ============================================
# LÓGICA DO BASTÃO E FILA
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
        log_status_change(current_holder, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(current_holder, now))
        st.session_state.status_texto[current_holder] = 'Indisponível'
        changed = True

    if changed: save_state()
    return changed

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
def auto_manage_time():
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
    # 20h: Encerra expediente
    elif now.hour >= 20:
        active = any(s != 'Indisponível' for s in st.session_state.status_texto.values()) or len(st.session_state.bastao_queue) > 0
        if active:
            st.session_state.bastao_queue = []
            st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
            for n in CONSULTORES: st.session_state[f'check_{n}'] = False
            save_state()
            st.toast("🛑 Expediente encerrado (20h). Fila limpa.", icon="zzz")

def toggle_queue(consultor):
    # Regra 20h
    if get_brazil_time().hour >= 20:
        st.toast("🚫 Expediente encerrado! Não é possível entrar na fila.", icon="🌙")
        st.session_state[f'check_{consultor}'] = False
        return

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

    nxt_idx = find_next_holder_index(curr_idx, q, skips)
    if nxt_idx != -1:
        nxt = q[nxt_idx]
        now = get_brazil_time()
        
        old_s = st.session_state.status_texto[curr]
        new_s_old = old_s.replace('Bastão | ', '').replace('Bastão', '').strip()
        log_status_change(curr, old_s, new_s_old, now - (st.session_state.bastao_start_time or now))
        st.session_state.status_texto[curr] = new_s_old
        
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

# [FUNÇÕES QUE FALTAVAM]
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

def leave_specific_status(consultor, status_type_to_remove):
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
    if status_type_to_remove == 'Almoço' or status_type_to_remove == 'Treinamento':
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True
        st.session_state.skip_flags[consultor] = False
    check_and_assume_baton()
    save_state()

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state()
auto_manage_time()
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
            st.markdown("### Selecione a Atividade")
            c_a1, c_a2 = st.columns([1, 1], vertical_alignment="bottom")
            with c_a1: atividades_escolhidas = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS)
            with c_a2: texto_extra = st.text_input("Detalhe (se necessário):", placeholder="Ex: Assunto específico...")
            col_confirm_1, col_confirm_2 = st.columns(2)
            with col_confirm_1:
                if st.button("Confirmar Atividade", type="primary", use_container_width=True):
                    if atividades_escolhidas:
                        str_atividades = ", ".join(atividades_escolhidas)
                        status_final = f"Atividade: {str_atividades}"
                        if texto_extra: status_final += f" - {texto_extra}"
                        update_status(status_final); st.session_state.active_view = None; st.rerun()
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
                    update_status(status_final); st.session_state.active_view = None; st.rerun()
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
                        update_status(status_final, force_exit_queue=True); st.session_state.active_view = None; st.rerun()
                    else: st.warning("Digite o nome da reunião.")
            with col_r2:
                if st.button("Cancelar", use_container_width=True, key='cancel_reuniao'): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_treinamento':
        with st.container(border=True):
            st.markdown("### Detalhes do Treinamento")
            st.info("ℹ️ Ao confirmar treinamento, você sairá da fila do bastão.")
            treinamento_desc = st.text_input("Qual Treinamento?", placeholder="Ex: Treinamento Eproc, Curso TJMG...")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                if st.button("Confirmar Treinamento", type="primary", use_container_width=True):
                    if treinamento_desc:
                        status_final = f"Treinamento: {treinamento_desc}"
                        update_status(status_final, force_exit_queue=True); st.session_state.active_view = None; st.rerun()
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
                        update_status(status_final, force_exit_queue=True); st.session_state.active_view = None; st.rerun()
                    else: st.warning("Digite o nome da sessão.")
            with col_s2:
                if st.button("Cancelar", use_container_width=True, key='cancel_sessao'): st.session_state.active_view = None; st.rerun()
    
    st.markdown("####")
    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)
    st.markdown("---")
    
    c_tool1, c_tool2, c_tool3, c_tool4, c_tool5, c_tool6, c_tool7 = st.columns(7)
    
    c_tool1.button("📑 Checklist", help="Gerador de Checklist Eproc", use_container_width=True, on_click=toggle_view, args=("checklist",))
    c_tool2.button("🆘 Chamados", help="Guia de Abertura de Chamados", use_container_width=True, on_click=toggle_view, args=("chamados",))
    c_tool3.button("📝 Atendimento", help="Registrar Atendimento", use_container_width=True, on_click=toggle_view, args=("atendimentos",))
    c_tool4.button("⏰ H. Extras", help="Registrar Horas Extras", use_container_width=True, on_click=toggle_view, args=("hextras",))
    c_tool5.button("🧠 Descanso", help="Jogo e Ranking", use_container_width=True, on_click=toggle_view, args=("descanso",))
    c_tool6.button("🐛 Erro/Novidade", help="Relatar Erro ou Novidade", use_container_width=True, on_click=toggle_view, args=("erro_novidade",))
    c_tool7.button("🖨️ Certidão", help="Gerar Certidão de Indisponibilidade", use_container_width=True, on_click=toggle_view, args=("certidao",))
        
    if st.session_state.active_view == "checklist":
        with st.container(border=True):
            st.header("Gerador de Checklist (Sessão Eproc)")
            if st.session_state.get('last_reg_status') == "success_sessao":
                st.success("Registro de Sessão enviado com sucesso!")
                if st.session_state.get('html_download_ready') and st.session_state.get('html_content_cache'):
                    filename = st.session_state.get('html_filename', 'Checklist_Sessao.html')
                    st.download_button(label=f"⬇️ Baixar Formulário HTML ({filename})", data=st.session_state.html_content_cache, file_name=filename, mime="text/html")
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
                st.subheader("📄 Resumo e Passo 1: Testes Iniciais")
                st.markdown("O processo de abertura de chamados segue uma padronização.\n**PASSO 1: Testes Iniciais**\nAntes de abrir o chamado, o consultor(a) deve primeiro realizar os procedimentos de suporte e testes necessários.")
                st.button("Próximo (Passo 2) ➡️", on_click=set_chamado_step, args=(2,))
            elif guide_step == 2:
                st.subheader("PASSO 2: Checklist de Abertura")
                st.markdown("**1. Dados do Usuário**\n**2. Dados do Processo**\n**3. Descrição do Erro**\n**4. Prints/Vídeo**")
                st.button("Próximo (Passo 3) ➡️", on_click=set_chamado_step, args=(3,))
            elif guide_step == 3:
                st.subheader("PASSO 3: Registrar e Informar")
                st.markdown("Envie e-mail ao usuário informando o número do chamado.")
                st.button("Próximo (Observações) ➡️", on_click=set_chamado_step, args=(4,))
            elif guide_step == 4:
                st.subheader("Observações Gerais")
                st.markdown("* Comunicação via e-mail institucional.\n* Atualização no IN.")
                st.button("Entendi! Abrir campo ➡️", on_click=set_chamado_step, args=(5,))
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
            st.markdown("### 🐛 Registro de Erro ou Novidade")
            with st.expander("📝 Ver Exemplo de Preenchimento"):
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
    
    # [VIEW CERTIDÃO ATUALIZADA]
    elif st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.header("🖨️ Gerador de Certidão de Indisponibilidade")
            
            # Inputs
            tipo_cert = st.selectbox("Tipo de Certidão:", ["Geral", "Eletrônica", "Física"])
            
            # Condicional para input de Data
            dt_indis = []
            
            if tipo_cert == "Geral":
                # Certidão Geral pede Data (Dia Único ou Período)
                # OBS: Removido o campo "Horário de Início" pois você pediu para voltar à versão anterior
                tipo_periodo = st.radio("Período:", ["Dia Único", "Intervalo de Dias"], horizontal=True)
                if tipo_periodo == "Dia Único":
                    dt_input_raw = st.date_input("Data da Indisponibilidade:", value=get_brazil_time().date(), format="DD/MM/YYYY")
                    dt_indis = [dt_input_raw]
                else:
                    dt_indis_raw = st.date_input("Selecione o Intervalo:", value=[], format="DD/MM/YYYY")
                    if isinstance(dt_indis_raw, list): dt_indis = dt_indis_raw
                    else: dt_indis = [dt_indis_raw] # Fallback

                st.info("ℹ️ Certidão Geral não requer número de processo ou chamado.")
                num_proc = ""
                chamado = ""
                
            else:
                # Certidões Físicas/Eletrônicas
                tipo_periodo = st.radio("Período:", ["Dia Único", "Intervalo de Dias"], horizontal=True)
                if tipo_periodo == "Dia Único":
                    dt_input_raw = st.date_input("Data da Indisponibilidade:", value=get_brazil_time().date(), format="DD/MM/YYYY")
                    dt_indis = [dt_input_raw]
                else:
                    dt_indis = st.date_input("Selecione o Intervalo:", value=[], format="DD/MM/YYYY")
                    if isinstance(dt_indis_raw, list): dt_indis = dt_indis_raw
                    else: dt_indis = [dt_indis_raw]

                num_proc = st.text_input("Número do Processo:", placeholder="1.0000...")
                chamado = st.text_input("Número do Chamado (ServiceNow/Jira):")
                
            motivo_pedido = st.text_area("Motivo do Pedido / Descrição da Ocorrência:", placeholder="Descreva brevemente a causa da indisponibilidade...")
            consultor_logado = st.session_state.consultor_selectbox
            
            if st.button("Gerar Documento Word", type="primary"):
                erro = False
                if not consultor_logado or consultor_logado == "Selecione um nome": st.error("Selecione um consultor no menu principal."); erro = True
                if not motivo_pedido: st.error("Por favor, informe o motivo do pedido."); erro = True
                if tipo_cert != "Geral":
                    if not num_proc or not chamado: st.error("Preencha Processo e Chamado."); erro = True
                if isinstance(dt_indis, list) and not dt_indis: st.error("Selecione uma data válida."); erro = True
                
                if not erro:
                    # Gera o arquivo
                    arquivo_buffer = gerar_docx_certidao(tipo_cert, num_proc, dt_indis, chamado, motivo_pedido)
                    
                    nome_arq = f"Certidao_{tipo_cert}.docx"
                    if num_proc: nome_arq = f"Certidao_{tipo_cert}_{num_proc.replace('/','-')}.docx"
                    
                    st.session_state['ultimo_docx'] = arquivo_buffer
                    st.session_state['ultimo_nome_docx'] = nome_arq
                    
                    # Notifica Chat
                    send_certidao_notification_to_chat(consultor_logado, tipo_cert)
                    
                    # NÃO envia para o Sheets nesta versão
                    
                    st.success("Certidão gerada com sucesso! Clique abaixo para baixar.")

            if 'ultimo_docx' in st.session_state and st.session_state['ultimo_docx'] is not None:
                st.download_button(
                    label="⬇️ Baixar Certidão (.docx)",
                    data=st.session_state['ultimo_docx'],
                    file_name=st.session_state['ultimo_nome_docx'],
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
    
    st.markdown("---")
    st.markdown("### 📚 Links Úteis - Notebooks LM Cesupe")
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
        'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade_especifica': [], 
        'sessao_especifica': [], 'projeto_especifico': [], 'reuniao_especifica': [],
        'treinamento_especifico': [], 'indisponivel': []
    }

    for nome in CONSULTORES:
        if nome in st.session_state.bastao_queue: ui_lists['fila'].append(nome)
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
        if 'Treinamento:' in status:
            match = re.search(r'Treinamento: (.*)', status)
            desc_treinamento = match.group(1).split('|')[0].strip() if match else "Geral"
            if not desc_treinamento: desc_treinamento = "Geral"
            ui_lists['treinamento_especifico'].append((nome, desc_treinamento))
        if 'Atividade:' in status or status == 'Atendimento':
            if status == 'Atendimento': ui_lists['atividade_especifica'].append((nome, "Atendimento"))
            else:
                match = re.search(r'Atividade: (.*)', status)
                if match: ui_lists['atividade_especifica'].append((nome, match.group(1).split('|')[0].strip()))

    st.subheader(f'✅ Na Fila ({len(ui_lists["fila"])})')
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
            if "Atividade" in status_atual: extra_info += " 📋"
            if "Projeto" in status_atual: extra_info += " 🏗️"
            if nome == responsavel: display = f'<span style="background-color: #FFD700; color: #000; padding: 2px 6px; border-radius: 5px; font-weight: bold;">🥂 {nome}</span>'
            elif skip_flag: display = f'**{nome}**{extra_info} :orange-background[Pulando ⏭️]'
            else: display = f'**{nome}**{extra_info} :blue-background[Aguardando]'
            col_nome.markdown(display, unsafe_allow_html=True)
    st.markdown('---')

    def render_section_detalhada(title, icon, lista_tuplas, tag_color_name, keyword_removal):
        colors = {'orange': '#FFECB3', 'blue': '#BBDEFB', 'teal': '#B2DFDB', 'violet': '#E1BEE7', 'green': '#C8E6C9', 'red': '#FFCDD2', 'grey': '#F5F5F5'}
        bg_hex = colors.get(tag_color_name, '#E0E0E0') 
        st.subheader(f'{icon} {title} ({len(lista_tuplas)})')
        if not lista_tuplas: st.markdown(f'_Ninguém em {title.lower()}._')
        else:
            for nome, desc in sorted(lista_tuplas, key=lambda x: x[0]):
                col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment="center")
                key_dummy = f'chk_status_{title}_{nome}' 
                col_check.checkbox(' ', key=key_dummy, value=True, on_change=leave_specific_status, args=(nome, keyword_removal), label_visibility='collapsed')
                html_badged = f"""<div style="font-size: 16px; margin: 2px 0;"><strong>{nome}</strong><span style="background-color: {bg_hex}; color: #333; padding: 2px 8px; border-radius: 12px; font-size: 14px; margin-left: 8px; vertical-align: middle;">{desc}</span></div>"""
                col_nome.markdown(html_badged, unsafe_allow_html=True)
        st.markdown('---')

    def render_section_simples(title, icon, names, tag_color_name):
        colors = {'orange': '#FFECB3', 'blue': '#BBDEFB', 'teal': '#B2DFDB', 'violet': '#E1BEE7', 'green': '#C8E6C9', 'red': '#FFCDD2', 'grey': '#EEEEEE'}
        bg_hex = colors.get(tag_color_name, '#E0E0E0')
        st.subheader(f'{icon} {title} ({len(names)})')
        if not names: st.markdown(f'_Ninguém em {title.lower()}._')
        else:
            for nome in sorted(names):
                col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment="center")
                key_dummy = f'chk_simples_{title}_{nome}'
                if title == 'Indisponível': col_check.checkbox(' ', key=key_dummy, value=False, on_change=enter_from_indisponivel, args=(nome,), label_visibility='collapsed')
                else: col_check.checkbox(' ', key=key_dummy, value=True, on_change=leave_specific_status, args=(nome, title), label_visibility='collapsed')
                html_simple = f"""<div style="font-size: 16px; margin: 2px 0;"><strong>{nome}</strong><span style="background-color: {bg_hex}; color: #444; padding: 2px 6px; border-radius: 6px; font-size: 12px; margin-left: 6px; vertical-align: middle; text-transform: uppercase;">{title}</span></div>"""
                col_nome.markdown(html_simple, unsafe_allow_html=True)
        st.markdown('---')

    render_section_detalhada('Em Demanda', '📋', ui_lists['atividade_especifica'], 'orange', 'Atividade')
    render_section_detalhada('Projetos', '🏗️', ui_lists['projeto_especifico'], 'blue', 'Projeto')
    render_section_detalhada('Treinamento', '🎓', ui_lists['treinamento_especifico'], 'teal', 'Treinamento') 
    render_section_detalhada('Reuniões', '📅', ui_lists['reuniao_especifica'], 'violet', 'Reunião')
    render_section_simples('Almoço', '🍽️', ui_lists['almoco'], 'red')
    render_section_detalhada('Sessão', '🎙️', ui_lists['sessao_especifica'], 'green', 'Sessão')
    render_section_simples('Saída rápida', '🚶', ui_lists['saida'], 'red')
    render_section_simples('Ausente', '👤', ui_lists['ausente'], 'violet') 
    render_section_simples('Indisponível', '❌', ui_lists['indisponivel'], 'grey')

now_utc = datetime.utcnow()
now_br = get_brazil_time()
last_run_date = st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()

if now_br.hour >= 20 and now_br.date() > last_run_date:
    print(f"TRIGGER: Enviando relatório diário. Agora (BRT): {now_br}, Última Execução: {st.session_state.report_last_run_date}")
    send_daily_report()
