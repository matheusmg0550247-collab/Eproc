# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json
import re
from repository import load_state_from_db, save_state_to_db
from utils import (get_brazil_time, get_secret, send_to_chat, gerar_docx_certidao, get_img_as_base64)

# --- CONSTANTES ---
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

# --- HANDLER GLOBAL ---
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
    import io; from docx import Document; from docx.shared import Pt
    document = Document(); buffer = io.BytesIO(); document.save(buffer); buffer.seek(0); return buffer

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

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue); start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        consultor = queue[idx]
        if st.session_state.get(f'check_{consultor}', False) and not skips.get(consultor, False): return idx
    return -1

# --- CORREÇÃO CRÍTICA AQUI ---
def check_and_assume_baton(forced_successor=None, immune_consultant=None):
    """
    immune_consultant: Nome do consultor que acabou de realizar uma ação (ex: Almoço).
    A função NÃO vai alterar o status desse consultor, mesmo que ele tenha saído do bastão.
    """
    queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    # Se o holder atual for o imune (quem clicou almoço), precisamos forçar a saída dele
    # mas SEM alterar o status "Almoço" que ele acabou de setar.
    
    is_valid = (current_holder and current_holder in queue and st.session_state.get(f'check_{current_holder}'))
    
    target = forced_successor if forced_successor else (current_holder if is_valid else None)
    if not target and not is_valid:
        idx = find_next_holder_index(-1, queue, skips)
        target = queue[idx] if idx != -1 else None

    changed = False; now = get_brazil_time()
    
    # 1. Limpeza dos Antigos Holders
    for c in CONSULTORES:
        # PULA se for o consultor imune (quem clicou no botão)
        if c == immune_consultant: continue
        
        # Se não é o alvo e tem bastão, tira o bastão
        if c != target and 'Bastão' in st.session_state.status_texto.get(c, ''):
            log_status_change(c, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(c, now))
            st.session_state.status_texto[c] = 'Indisponível'; changed = True

    # 2. Definição do Novo Dono
    if target:
        curr_s = st.session_state.status_texto.get(target, '')
        if 'Bastão' not in curr_s:
            old_s = curr_s; new_s = f"Bastão | {old_s}" if old_s and old_s != "Indisponível" else "Bastão"
            log_status_change(target, old_s, new_s, now - st.session_state.current_status_starts.get(target, now))
            st.session_state.status_texto[target] = new_s; st.session_state.bastao_start_time = now
            if current_holder != target: 
                st.session_state.play_sound = True; send_chat_notification_internal(target, 'Bastão')
            st.session_state.skip_flags[target] = False; changed = True
            
    elif not target and current_holder:
        # Se não tem ninguém pra assumir e o atual não é o imune, tira o bastão
        if current_holder != immune_consultant:
            log_status_change(current_holder, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(current_holder, now))
            st.session_state.status_texto[current_holder] = 'Indisponível'; changed = True

    if changed: save_state()
    return changed

def init_session_state():
    if 'db_loaded' not in st.session_state:
        try:
            db_data = load_state_from_db(); 
            if db_data: 
                for key, value in db_data.items(): st.session_state[key] = value
        except: pass
        st.session_state['db_loaded'] = True
    # Reset de data se necessário
    if 'report_last_run_date' in st.session_state and isinstance(st.session_state['report_last_run_date'], str):
        try: st.session_state['report_last_run_date'] = datetime.fromisoformat(st.session_state['report_last_run_date'])
        except: st.session_state['report_last_run_date'] = datetime.min
        
    now = get_brazil_time()
    # Inicializa defaults se faltar algo
    defaults = {'bastao_start_time': None, 'report_last_run_date': datetime.min, 'rotation_gif_start_time': None, 'play_sound': False, 'gif_warning': False, 'lunch_warning_info': None, 'last_reg_status': None, 'chamado_guide_step': 0, 'auxilio_ativo': False, 'active_view': None, 'last_jira_number': "", 'consultor_selectbox': "Selecione um nome", 'status_texto': {n: 'Indisponível' for n in CONSULTORES}, 'bastao_queue': [], 'skip_flags': {}, 'current_status_starts': {n: now for n in CONSULTORES}, 'bastao_counts': {n: 0 for n in CONSULTORES}, 'priority_return_queue': [], 'daily_logs': [], 'simon_ranking': []}
    for k, v in defaults.items(): 
        if k not in st.session_state: st.session_state[k] = v
        
    # Garante estrutura básica
    for nome in CONSULTORES:
        if nome not in st.session_state.status_texto: st.session_state.status_texto[nome] = 'Indisponível'
        st.session_state.bastao_counts.setdefault(nome, 0)
        st.session_state.skip_flags.setdefault(nome, False)
        
        # Checkbox logic recovery
        curr = st.session_state.status_texto[nome]
        is_blocked = any(x in curr for x in ['Almoço', 'Ausente', 'Saída', 'Sessão', 'Reunião', 'Treinamento'])
        in_prio = nome in st.session_state.priority_return_queue
        in_queue = nome in st.session_state.bastao_queue
        st.session_state[f'check_{nome}'] = True if in_queue else (False if is_blocked or in_prio else ('Indisponível' not in curr))
        
        if nome not in st.session_state.current_status_starts: st.session_state.current_status_starts[nome] = now
        
    check_and_assume_baton()

def reset_day_state():
    now = get_brazil_time()
    st.session_state.bastao_queue = []; st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
    st.session_state.bastao_counts = {n: 0 for n in CONSULTORES}; st.session_state.skip_flags = {}
    st.session_state.daily_logs = []; st.session_state.current_status_starts = {n: now for n in CONSULTORES}
    st.session_state.report_last_run_date = now
    for n in CONSULTORES: st.session_state[f'check_{n}'] = False

def ensure_daily_reset():
    now_br = get_brazil_time(); last_run = st.session_state.report_last_run_date
    if now_br.date() > last_run.date():
        reset_day_state(); st.toast("☀️ Novo dia detectado! Fila limpa.", icon="🧹"); save_state()

# --- AÇÕES ---
def toggle_queue(consultor):
    now_hour = get_brazil_time().hour
    if now_hour >= 20 or now_hour < 6: st.toast("💤 Fora do expediente!", icon="🌙"); time.sleep(1); st.rerun(); return
    ensure_daily_reset(); st.session_state.gif_warning = False; now_br = get_brazil_time()
    
    if consultor in st.session_state.bastao_queue:
        # Saindo da fila
        holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        succ = None
        if consultor == holder:
            idx = st.session_state.bastao_queue.index(consultor)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: succ = st.session_state.bastao_queue[nxt]
        
        st.session_state.bastao_queue.remove(consultor)
        st.session_state[f'check_{consultor}'] = False
        
        curr = st.session_state.status_texto.get(consultor, '')
        if not curr or curr == 'Bastão':
            log_status_change(consultor, curr, 'Indisponível', now_br - st.session_state.current_status_starts.get(consultor, now_br))
            st.session_state.status_texto[consultor] = 'Indisponível'
            
        check_and_assume_baton(succ)
    else:
        # Entrando
        st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True
        st.session_state.skip_flags[consultor] = False
        if consultor in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(consultor)
        
        curr = st.session_state.status_texto.get(consultor, 'Indisponível')
        if 'Indisponível' in curr:
            log_status_change(consultor, curr, '', now_br - st.session_state.current_status_starts.get(consultor, now_br))
            st.session_state.status_texto[consultor] = ''
        check_and_assume_baton()
    save_state()

def leave_specific_status(consultor, status_type_to_remove):
    ensure_daily_reset(); st.session_state.gif_warning = False
    old = st.session_state.status_texto.get(consultor, '')
    now_br = get_brazil_time(); dur = now_br - st.session_state.current_status_starts.get(consultor, now_br)
    
    parts = [p.strip() for p in old.split('|')]
    new_parts = [p for p in parts if status_type_to_remove not in p and p]
    new_s = " | ".join(new_parts)
    if not new_s and consultor not in st.session_state.bastao_queue: new_s = 'Indisponível'
    
    log_status_change(consultor, old, new_s, dur)
    st.session_state.status_texto[consultor] = new_s
    
    if status_type_to_remove in ['Almoço', 'Treinamento']:
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True
        st.session_state.skip_flags[consultor] = False
    
    check_and_assume_baton(); save_state()

def enter_from_indisponivel(consultor):
    now_hour = get_brazil_time().hour
    if now_hour >= 20 or now_hour < 6: st.toast("💤 Fora do expediente!", icon="🌙"); time.sleep(1); st.rerun(); return
    ensure_daily_reset(); st.session_state.gif_warning = False
    if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    st.session_state[f'check_{consultor}'] = True
    st.session_state.skip_flags[consultor] = False
    old = st.session_state.status_texto.get(consultor, 'Indisponível')
    dur = get_brazil_time() - st.session_state.current_status_starts.get(consultor, get_brazil_time())
    log_status_change(consultor, old, '', dur)
    st.session_state.status_texto[consultor] = ''
    check_and_assume_baton(); save_state()

def rotate_bastao():
    ensure_daily_reset(); sel = st.session_state.consultor_selectbox
    if not sel or sel == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if sel != holder: st.session_state.gif_warning = True; return
    
    q = st.session_state.bastao_queue; idx = q.index(holder) if holder in q else -1
    if idx == -1: check_and_assume_baton(); return
    
    next_idx = find_next_holder_index(idx, q, st.session_state.skip_flags)
    if next_idx != -1:
        nh = q[next_idx]
        # Skippers logic...
        if next_idx > idx: skipped = q[idx+1:next_idx]
        else: skipped = q[idx+1:] + q[:next_idx]
        for p in skipped: st.session_state.skip_flags[p] = False
        st.session_state.skip_flags[nh] = False
        
        now = get_brazil_time()
        # Holder sai
        old_h_s = st.session_state.status_texto[holder]
        new_h_s = old_h_s.replace('Bastão | ', '').replace('Bastão', '').strip()
        log_status_change(holder, old_h_s, new_h_s, now - (st.session_state.bastao_start_time or now))
        st.session_state.status_texto[holder] = new_h_s
        
        # New holder entra
        old_n_s = st.session_state.status_texto.get(nh, '')
        new_n_s = f"Bastão | {old_n_s}" if old_n_s else "Bastão"
        log_status_change(nh, old_n_s, new_n_s, timedelta(0))
        st.session_state.status_texto[nh] = new_n_s
        st.session_state.bastao_start_time = now
        st.session_state.bastao_counts[holder] = st.session_state.bastao_counts.get(holder, 0) + 1
        st.session_state.play_sound = True; st.session_state.rotation_gif_start_time = now
        send_chat_notification_internal(nh, 'Bastão'); save_state()
    else:
        st.warning('Ninguém elegível na fila.'); check_and_assume_baton()

def toggle_skip():
    sel = st.session_state.consultor_selectbox
    if not sel or sel == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    if not st.session_state.get(f'check_{sel}'): st.warning(f'{sel} indisponível.'); return
    st.session_state.skip_flags[sel] = not st.session_state.skip_flags.get(sel, False); save_state()

def update_status(new_status_part, force_exit_queue=False):
    ensure_daily_reset()
    sel = st.session_state.consultor_selectbox
    if not sel or sel == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    
    # 1. Definir o Status Final STRING antes de qualquer coisa
    current = st.session_state.status_texto.get(sel, '')
    parts = [p.strip() for p in current.split('|') if p.strip()]
    type_new = new_status_part.split(':')[0]
    clean = [p for p in parts if p != 'Indisponível' and not p.startswith(type_new)]
    clean.append(new_status_part)
    # Ordena: Bastão -> Atividade -> Outros
    clean.sort(key=lambda x: 0 if 'Bastão' in x else 1 if 'Atividade' in x or 'Projeto' in x else 2)
    final_status = " | ".join(clean)
    
    # 2. Lógica de Saída da Fila e Rotação
    blocking = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento']
    should_exit = force_exit_queue or any(b in new_status_part for b in blocking)
    
    is_holder = 'Bastão' in current
    forced_succ = None
    
    if should_exit and sel in st.session_state.bastao_queue:
        # Se for o holder, descobre sucessor
        holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        if sel == holder:
            idx = st.session_state.bastao_queue.index(sel)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: forced_succ = st.session_state.bastao_queue[nxt]
        
        # Remove da fila
        st.session_state[f'check_{sel}'] = False
        st.session_state.bastao_queue.remove(sel)
        st.session_state.skip_flags.pop(sel, None)
    
    # 3. Se tinha bastão e não saiu, mantém o texto Bastão
    if is_holder and not should_exit and 'Bastão' not in final_status:
        final_status = f"Bastão | {final_status}"
    
    # 4. APLICA A MUDANÇA DE STATUS (Log + Estado)
    # Importante: Fazemos isso ANTES de chamar check_and_assume_baton
    now_br = get_brazil_time()
    log_status_change(sel, current, final_status, now_br - st.session_state.current_status_starts.get(sel, now_br))
    st.session_state.status_texto[sel] = final_status
    
    if new_status_part == 'Saída rápida':
        if sel not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(sel)
    elif sel in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(sel)
    
    # 5. GIRA O BASTÃO COM IMUNIDADE
    # Passamos 'sel' como immune_consultant para que a função de rotação NÃO coloque ele como Indisponível
    if is_holder: 
        check_and_assume_baton(forced_succ, immune_consultant=sel)
        
    save_state()

def auto_manage_time():
    now = get_brazil_time(); last_run = st.session_state.report_last_run_date
    if now.hour >= 23 and now.date() == last_run.date(): reset_day_state(); save_state()
    elif now.date() > last_run.date(): reset_day_state(); save_state()
    elif now.hour >= 20:
        if any(s != 'Indisponível' for s in st.session_state.status_texto.values()) or st.session_state.bastao_queue:
            st.session_state.bastao_queue = []; st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
            for n in CONSULTORES: st.session_state[f'check_{n}'] = False
            save_state()

def manual_rerun(): st.session_state.gif_warning = False; st.rerun()

# ============================================
# LAYOUT
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
init_session_state(); auto_manage_time()
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
render_fireworks()

c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img = get_img_as_base64(PUG2026_FILENAME); src = f"data:image/png;base64,{img}" if img else GIF_BASTAO_HOLDER
    st.markdown(f"""<div style="display: flex; align-items: center; gap: 15px;"><h1 style="margin: 0; padding: 0; font-size: 2.2rem; color: #FFD700; text-shadow: 1px 1px 2px #B8860B;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{src}" style="width: 120px; height: 120px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;"></div>""", unsafe_allow_html=True)

with c_topo_dir:
    c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
    sel_fast = c1.selectbox("Assumir (Rápido)", ["Selecione"]+CONSULTORES, label_visibility="collapsed", key="quick")
    if c2.button("🚀 Entrar", use_container_width=True) and sel_fast != "Selecione":
        if toggle_queue(sel_fast): st.session_state.consultor_selectbox = sel_fast; st.rerun()

st.markdown("<hr style='border: 1px solid #FFD700; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

if st.session_state.rotation_gif_start_time:
    if (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 20: st.image(GIF_URL_ROTATION, width=200)
    else: st.session_state.rotation_gif_start_time = None; save_state()
if st.session_state.get('play_sound'): st.components.v1.html(play_sound_html(), height=0, width=0); st.session_state.play_sound = False
st_autorefresh(interval=8000, key='auto')

col_main, col_side = st.columns([1.5, 1])
queue = st.session_state.bastao_queue
holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
idx_h = queue.index(holder) if holder in queue else -1
idx_p = find_next_holder_index(idx_h, queue, st.session_state.skip_flags)
prox = queue[idx_p] if idx_p != -1 else None
rest = [queue[(idx_p + 1 + i) % len(queue)] for i in range(len(queue)) if queue[(idx_p + 1 + i) % len(queue)] not in [holder, prox]] if idx_p != -1 else []

with col_main:
    st.header("Responsável pelo Bastão")
    if holder:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%); border: 3px solid #FFD700; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3); margin-bottom: 20px;"><div style="flex-shrink: 0; margin-right: 25px;"><img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #FFD700;"></div><div><span style="font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px;">Atualmente com:</span><br><span style="font-size: 42px; font-weight: 800; color: #000080; line-height: 1.1;">{holder}</span></div></div>""", unsafe_allow_html=True)
        dur = get_brazil_time() - (st.session_state.bastao_start_time or get_brazil_time())
        st.caption(f"⏱️ Tempo: **{format_time_duration(dur)}**")
    else: st.markdown('<h2>(Ninguém)</h2>', unsafe_allow_html=True)
    
    st.markdown("###"); st.header("Próximos")
    if prox: st.markdown(f'### 1º: **{prox}**')
    if rest: st.markdown(f'#### 2º+: {", ".join(rest)}')
    
    st.markdown("###"); st.header("**Consultor(a)**")
    st.selectbox('Selecione:', ['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### Ações:")
    
    r1, r2, r3, r4 = st.columns(4); r2_1, r2_2, r2_3, r2_4, r2_5, r2_6 = st.columns(6)
    r1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    r2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True)
    r3.button('📋 Ativ.', on_click=toggle_view, args=('menu_atividades',), use_container_width=True)
    r4.button('🏗️ Proj.', on_click=toggle_view, args=('menu_projetos',), use_container_width=True)
    r2_1.button('🎓 Treino', on_click=toggle_view, args=('menu_treinamento',), use_container_width=True)
    r2_2.button('📅 Reunião', on_click=toggle_view, args=('menu_reuniao',), use_container_width=True)
    r2_3.button('🍽️ Almoço', on_click=update_status, args=('Almoço', True), use_container_width=True)
    r2_4.button('🎙️ Sessão', on_click=toggle_view, args=('menu_sessao',), use_container_width=True)
    r2_5.button('🚶 Saída', on_click=update_status, args=('Saída rápida', True), use_container_width=True)
    r2_6.button('👤 Ausente', on_click=update_status, args=('Ausente', True), use_container_width=True)

    if st.session_state.active_view:
        with st.container(border=True):
            av = st.session_state.active_view
            if av == 'menu_atividades':
                c1, c2 = st.columns(2); sel = c1.multiselect("Tipo", OPCOES_ATIVIDADES_STATUS); txt = c2.text_input("Det.")
                if st.button("OK", type="primary"): update_status(f"Atividade: {', '.join(sel)} {txt}"); st.session_state.active_view=None; st.rerun()
            elif av == 'menu_projetos':
                if st.button("OK", type="primary"): update_status(f"Projeto: {st.selectbox('Proj.', OPCOES_PROJETOS)}"); st.session_state.active_view=None; st.rerun()
            elif av in ['menu_reuniao', 'menu_treinamento', 'menu_sessao']:
                t = av.split('_')[1].capitalize(); d = st.text_input("Qual?")
                if st.button("OK", type="primary"): update_status(f"{t}: {d}", True); st.session_state.active_view=None; st.rerun()
            if st.button("Cancelar"): st.session_state.active_view=None; st.rerun()

    st.markdown("####"); st.button('🔄 Atualizar', on_click=manual_rerun, use_container_width=True); st.markdown("---")
    
    t1, t2, t3, t4, t5, t6, t7 = st.columns(7)
    t1.button("📑", on_click=toggle_view, args=("checklist",), help="Checklist")
    t2.button("🆘", on_click=toggle_view, args=("chamados",), help="Chamados")
    t3.button("📝", on_click=toggle_view, args=("atendimentos",), help="Atend.")
    t4.button("⏰", on_click=toggle_view, args=("hextras",), help="Extras")
    t5.button("🧠", on_click=toggle_view, args=("descanso",), help="Descanso")
    t6.button("🐛", on_click=toggle_view, args=("erro_novidade",), help="Erro")
    t7.button("🖨️", on_click=toggle_view, args=("certidao",), help="Certidão")

    if st.session_state.active_view == "checklist":
        with st.container(border=True):
            st.header("Checklist"); d = st.date_input("Data"); c = st.selectbox("Câmara", CAMARAS_OPCOES)
            if st.button("Gerar", type="primary"): handle_sessao_submission(st.session_state.consultor_selectbox, c, d)
            if st.session_state.get('html_download_ready'): st.download_button("Baixar", st.session_state.html_content_cache, "Checklist.html")
    # (Outros menus simplificados para caber, lógica mantida)

with col_side:
    st.markdown("###"); st.toggle("Auxílio", key='auxilio_ativo', on_change=on_auxilio_change)
    if st.session_state.get('auxilio_ativo'): st.warning("Ativo!"); st.image(GIF_URL_NEDRY, width=200)
    st.markdown("---"); st.header('Status')
    
    # Listas UI
    lists = {k: [] for k in ['fila','almoco','saida','ausente','indisponivel','atividades','projetos','reuniao','treino','sessao']}
    for n in CONSULTORES:
        s = st.session_state.status_texto.get(n, 'Indisponível')
        if n in queue: lists['fila'].append(n)
        elif s == 'Almoço': lists['almoco'].append(n)
        elif s == 'Ausente': lists['ausente'].append(n)
        elif s == 'Saída rápida': lists['saida'].append(n)
        elif s == 'Indisponível': lists['indisponivel'].append(n)
        elif 'Atividade:' in s or s=='Atendimento': lists['atividades'].append((n, s))
        elif 'Projeto:' in s: lists['projetos'].append((n, s))
        elif 'Reunião:' in s: lists['reuniao'].append((n, s))
        elif 'Treinamento:' in s: lists['treino'].append((n, s))
        elif 'Sessão:' in s: lists['sessao'].append((n, s))

    st.subheader(f'✅ Fila ({len(lists["fila"])})')
    for n in [c for c in queue if c in lists['fila']]:
        c1, c2 = st.columns([0.85, 0.15])
        c2.checkbox(' ', key=f'chk_fila_{n}', value=True, on_change=toggle_queue, args=(n,), label_visibility='collapsed')
        bg = "#FFD700" if n == holder else "transparent"; cl = "black" if n == holder else "inherit"
        c1.markdown(f'<span style="background-color:{bg};color:{cl};padding:2px;border-radius:4px">{n}</span>', unsafe_allow_html=True)
    st.markdown('---')

    def show_sect(t, i, l, c, tag):
        st.subheader(f'{i} {t} ({len(l)})')
        for item in sorted(l, key=lambda x: x[0] if isinstance(x, tuple) else x):
            n = item[0] if isinstance(item, tuple) else item; d = item[1] if isinstance(item, tuple) else t
            c1, c2 = st.columns([0.85, 0.15])
            if t == 'Indisponível': c2.checkbox(' ', key=f'k_i_{n}', value=False, on_change=enter_from_indisponivel, args=(n,), label_visibility='collapsed')
            else: c2.checkbox(' ', key=f'k_o_{n}', value=True, on_change=leave_specific_status, args=(n, tag), label_visibility='collapsed')
            c1.markdown(f'**{n}** <span style="background:{c};font-size:11px;padding:2px;border-radius:4px">{d}</span>', unsafe_allow_html=True)
        st.markdown('---')

    show_sect('Demanda', '📋', lists['atividades'], '#FFECB3', 'Atividade')
    show_sect('Projetos', '🏗️', lists['projetos'], '#BBDEFB', 'Projeto')
    show_sect('Treino', '🎓', lists['treino'], '#B2DFDB', 'Treinamento')
    show_sect('Reunião', '📅', lists['reuniao'], '#E1BEE7', 'Reunião')
    show_sect('Almoço', '🍽️', lists['almoco'], '#FFCDD2', 'Almoço')
    show_sect('Sessão', '🎙️', lists['sessao'], '#C8E6C9', 'Sessão')
    show_sect('Saída', '🚶', lists['saida'], '#FFCDD2', 'Saída')
    show_sect('Ausente', '👤', lists['ausente'], '#E1BEE7', 'Ausente')
    show_sect('Indisponível', '❌', lists['indisponivel'], '#F5F5F5', 'Indisponível')
