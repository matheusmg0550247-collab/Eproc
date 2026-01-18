# -*- coding: utf-8 -*-
import streamlit as st
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import re
import random

# --- IMPORTAÇÃO DOS MÓDULOS ---
from utils import (
    CONSULTORES, get_brazil_time, send_to_chat, gerar_docx_certidao, 
    get_img_as_base64, get_secret
)
from repository import load_state_from_db, save_state_to_db

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

# --- GERENCIAMENTO DE ESTADO (MEMÓRIA + BANCO) ---
def init_session():
    """Inicializa as variáveis de estado, carregando do banco ou criando padrões."""
    
    # 1. Tenta carregar do Banco de Dados na primeira execução
    if 'db_loaded' not in st.session_state:
        try:
            db_data = load_state_from_db()
            if db_data:
                for key, value in db_data.items():
                    st.session_state[key] = value
        except Exception as e:
            print(f"Erro ao carregar estado inicial (usando padrões): {e}")
        st.session_state['db_loaded'] = True
        
    # 2. Garante chaves padrão (Safety Net)
    now_br = get_brazil_time()
    
    defaults = {
        'active_view': None, 
        'rotation_gif_start_time': None, 
        'lunch_warning_info': None, 
        'play_sound': False,
        'consultor_selectbox': "Selecione um nome",
        # Variáveis críticas
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'current_status_starts': {nome: now_br for nome in CONSULTORES},
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'daily_logs': [],
        'simon_ranking': []
    }
    
    for key, default in defaults.items():
        if key not in st.session_state: st.session_state[k] = default

    # 3. Garante checkboxes
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0)
        st.session_state.skip_flags.setdefault(nome, False)
        
        current = st.session_state.status_texto.get(nome, 'Indisponível')
        if current is None: current = 'Indisponível'
        st.session_state.status_texto[nome] = current
        
        blocking = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento']
        is_blocked = any(kw in current for kw in blocking)
        
        if is_blocked: is_avail = False
        elif nome in st.session_state.priority_return_queue: is_avail = False
        elif nome in st.session_state.bastao_queue: is_avail = True
        else: is_avail = 'Indisponível' not in current
        
        st.session_state[f'check_{nome}'] = is_avail
        if nome not in st.session_state.current_status_starts: st.session_state.current_status_starts[nome] = now_br

def persist():
    """Salva o session_state relevante no Banco Supabase"""
    keys_to_save = [
        'status_texto', 'bastao_queue', 'skip_flags', 'current_status_starts',
        'bastao_start_time', 'bastao_counts', 'priority_return_queue', 'daily_logs', 'simon_ranking'
    ]
    data = {k: st.session_state[k] for k in keys_to_save if k in st.session_state}
    save_state_to_db(data)

# --- FUNÇÃO DE AUTOMATIZAÇÃO DE HORÁRIO ---
def auto_manage_time():
    """Aplica as regras de horário (20h e 23h) automaticamente ao carregar."""
    now = get_brazil_time()
    
    # REGRA 1: LIMPEZA TOTAL ÀS 23:00 (Reseta para o dia seguinte)
    if now.hour >= 23:
        # Verifica se o banco está "sujo" (tem alguém na fila ou contadores > 0)
        has_queue = len(st.session_state.bastao_queue) > 0
        has_counts = any(v > 0 for v in st.session_state.bastao_counts.values())
        
        if has_queue or has_counts:
            st.session_state.bastao_queue = []
            st.session_state.status_texto = {nome: 'Indisponível' for nome in CONSULTORES}
            st.session_state.bastao_counts = {nome: 0 for nome in CONSULTORES} # Zera contadores
            st.session_state.skip_flags = {}
            st.session_state.daily_logs = []
            st.session_state.current_status_starts = {nome: now for nome in CONSULTORES}
            
            # Atualiza checkboxes visuais
            for nome in CONSULTORES: st.session_state[f'check_{nome}'] = False
                
            persist()
            # Mostra aviso discreto
            st.toast("🧹 Limpeza Diária (23h) realizada. Banco resetado para amanhã!", icon="🌙")

    # REGRA 2: INDISPONIBILIDADE APÓS AS 20:00 (Encerramento do expediente)
    elif now.hour >= 20:
        # Se ainda não limpou a fila ou alguém não está 'Indisponível'
        active_status = any(s != 'Indisponível' for s in st.session_state.status_texto.values())
        queue_active = len(st.session_state.bastao_queue) > 0
        
        if active_status or queue_active:
            st.session_state.bastao_queue = []
            st.session_state.status_texto = {nome: 'Indisponível' for nome in CONSULTORES}
            # NOTA: Aqui NÃO zeramos os contadores (bastao_counts), mantemos o histórico do dia
            
            # Atualiza checkboxes visuais
            for nome in CONSULTORES: st.session_state[f'check_{nome}'] = False
            
            persist()
            st.toast("🛑 Horário de Encerramento (20h). Todos definidos como Indisponível.", icon="zzz")

# --- LÓGICA DO BASTÃO ---
def find_next_holder(current_holder):
    queue = st.session_state.bastao_queue
    if not queue: return None
    
    start_idx = 0
    if current_holder in queue:
        start_idx = (queue.index(current_holder) + 1) % len(queue)
    
    for i in range(len(queue)):
        idx = (start_idx + i) % len(queue)
        candidate = queue[idx]
        is_avail = st.session_state.get(f'check_{candidate}', False)
        is_skipping = st.session_state.skip_flags.get(candidate, False)
        if is_avail and not is_skipping:
            return candidate
    return None

def rotate_bastao():
    selected = st.session_state.consultor_selectbox
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    if selected != current_holder:
        st.warning(f"Ação inválida! O bastão está com {current_holder}. Apenas ele(a) pode passar.")
        return

    next_holder = find_next_holder(current_holder)
    if not next_holder:
        st.warning("Ninguém elegível na fila para receber o bastão!")
        return

    now = get_brazil_time()
    
    # Tira do atual
    old_st = st.session_state.status_texto.get(current_holder, "")
    new_st_old = old_st.replace("Bastão | ", "").replace("Bastão", "").strip()
    if not new_st_old: new_st_old = "Indisponível"
    
    st.session_state.status_texto[current_holder] = new_st_old
    st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
    
    # Passa para novo
    old_st_new = st.session_state.status_texto.get(next_holder, "")
    if old_st_new and old_st_new != "Indisponível":
        st.session_state.status_texto[next_holder] = f"Bastão | {old_st_new}"
    else:
        st.session_state.status_texto[next_holder] = "Bastão"
    
    st.session_state.skip_flags[next_holder] = False
    st.session_state.bastao_start_time = now
    st.session_state.rotation_gif_start_time = now
    st.session_state.play_sound = True
    
    send_to_chat("bastao", f"🎉 **BASTÃO GIRADO!**\nNovo Responsável: {next_holder}")
    persist()
    st.rerun()

def update_status_action(new_status, exit_queue=False):
    name = st.session_state.consultor_selectbox
    if not name or name == "Selecione um nome": 
        st.warning("Selecione seu nome primeiro.")
        return
    
    if exit_queue:
        if name in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(name)
        st.session_state[f'check_{name}'] = False
        if name in st.session_state.skip_flags:
            del st.session_state.skip_flags[name]
    
    current = st.session_state.status_texto.get(name, "")
    is_holder = "Bastão" in current
    
    if is_holder and not exit_queue:
        final = f"Bastão | {new_status}"
    else:
        final = new_status
        
    st.session_state.status_texto[name] = final
    st.session_state.current_status_starts[name] = get_brazil_time()
    persist()
    st.rerun()

def toggle_queue_action(name):
    # Verifica horário antes de permitir entrar na fila
    now = get_brazil_time()
    if now.hour >= 20:
        st.toast("🚫 Expediente encerrado! Não é possível entrar na fila após as 20h.", icon="🌙")
        # Força o checkbox a ficar desmarcado (visualmente precisa do rerun)
        st.session_state[f'check_{name}'] = False
        return

    if name in st.session_state.bastao_queue:
        st.session_state.bastao_queue.remove(name)
        st.session_state[f'check_{name}'] = False
        st.session_state.status_texto[name] = "Indisponível"
    else:
        st.session_state.bastao_queue.append(name)
        st.session_state[f'check_{name}'] = True
        st.session_state.skip_flags[name] = False
        if st.session_state.status_texto.get(name) == "Indisponível":
            st.session_state.status_texto[name] = "" 
            
    persist()

# --- INICIALIZAÇÃO ---
init_session()
auto_manage_time() # <--- AQUI ESTÁ A MÁGICA (Executa as regras de horário)
st_autorefresh(interval=10000, key='refresher')

# --- INTERFACE VISUAL ---
st.markdown("## Controle Bastão Cesupe 2026 🥂")

if st.session_state.rotation_gif_start_time:
    if (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 10:
        st.image("https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif", width=150)

if st.session_state.play_sound:
    st.components.v1.html(f'<audio autoplay="true"><source src="https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3" type="audio/mpeg"></audio>', height=0)
    st.session_state.play_sound = False

c1, c2 = st.columns([1.5, 1])

with c1:
    holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), "Ninguém")
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #FFD700;">
        <h3 style="margin:0; color: #000;">COM O BASTÃO:</h3>
        <h1 style="margin:0; color: #000080;">{holder}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    next_h = find_next_holder(holder)
    st.caption(f"⏭️ **Próximo da fila:** {next_h if next_h else 'Ninguém elegível'}")
    
    st.markdown("---")
    
    st.session_state.consultor_selectbox = st.selectbox("Quem é você?", ["Selecione um nome"] + CONSULTORES, index=0)
    
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    c_btn1.button("🎯 Passar Bastão", on_click=rotate_bastao, use_container_width=True)
    
    if c_btn2.button("📋 Atividade", use_container_width=True):
        st.session_state.active_view = 'atividade'
    if c_btn3.button("🍽️ Almoço", use_container_width=True):
        update_status_action("Almoço", exit_queue=True)

    if st.session_state.active_view == 'atividade':
        with st.container(border=True):
            st.markdown("##### Registrar Atividade")
            tipo = st.selectbox("Tipo:", ["HP", "E-mail", "WhatsApp", "Outros"])
            c_ok, c_cancel = st.columns(2)
            if c_ok.button("Confirmar Status", type="primary"):
                update_status_action(f"Atividade: {tipo}")
                st.session_state.active_view = None
                st.rerun()
            if c_cancel.button("Cancelar"):
                st.session_state.active_view = None
                st.rerun()

    with st.expander("🖨️ Gerar Certidão de Indisponibilidade"):
        tipo_c = st.selectbox("Tipo", ["Geral", "Física", "Eletrônica"])
        c_proc = st.text_input("Processo (se houver):")
        c_chamado = st.text_input("Chamado (se houver):")
        c_motivo = st.text_area("Motivo / Descrição:")
        
        if st.button("Gerar DOCX"):
            if not st.session_state.consultor_selectbox or st.session_state.consultor_selectbox == "Selecione um nome":
                st.error("Selecione seu nome primeiro.")
            elif not c_motivo:
                st.error("Preencha o motivo.")
            else:
                buf = gerar_docx_certidao(tipo_c, c_proc, datetime.now(), c_chamado, c_motivo)
                st.download_button("Baixar", buf, "certidao_gerada.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                send_to_chat("certidao", f"📄 **Certidão Gerada** por {st.session_state.consultor_selectbox} (Tipo: {tipo_c})")

with c2:
    st.markdown("### 🚦 Fila e Status")
    with st.container(height=600):
        def sort_priority(name):
            status = st.session_state.status_texto.get(name, "")
            if "Bastão" in status: return 0
            if name in st.session_state.bastao_queue: return 1
            return 2
            
        sorted_consultores = sorted(CONSULTORES, key=sort_priority)

        for nome in sorted_consultores:
            c_row, c_chk = st.columns([0.85, 0.15])
            status = st.session_state.status_texto.get(nome, "")
            in_queue = nome in st.session_state.bastao_queue
            is_skipped = st.session_state.skip_flags.get(nome, False)
            
            c_chk.checkbox(" ", value=in_queue, key=f"chk_ui_{nome}", on_change=toggle_queue_action, args=(nome,), label_visibility="collapsed")
            
            icon = ""
            color = "#333"
            bg_color = "transparent"
            border = "none"
            
            if "Bastão" in status:
                icon = "🥂"
                color = "#000080"
                bg_color = "#FFF8DC"
                border = "1px solid #FFD700"
            elif is_skipped:
                icon = "⏭️"
                color = "orange"
            elif in_queue:
                icon = "✅"
                color = "green"
            elif "Almoço" in status:
                icon = "🍽️"
                color = "red"
            elif status == "Indisponível":
                icon = "❌"
                color = "#999"
            
            html_card = f"""
            <div style="padding: 5px 10px; margin-bottom: 5px; background-color: {bg_color}; border: {border}; border-radius: 5px; display: flex; justify-content: space-between; align-items: center;">
                <span style="color: {color}; font-weight: 500;">{icon} {nome}</span>
                <span style="font-size: 0.8em; color: #666;">{status}</span>
            </div>
            """
            c_row.markdown(html_card, unsafe_allow_html=True)

st.divider()
st.caption("Sistema Cesupe 2026 | Powered by Streamlit & Supabase")
