# -*- coding: utf-8 -*-
import streamlit as st
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import re
import random

# --- IMPORTAÇÃO DOS MÓDULOS NOVOS ---
from utils import (
    CONSULTORES, get_brazil_time, send_to_chat, gerar_docx_certidao, 
    get_img_as_base64, get_secret
)
from repository import load_state_from_db, save_state_to_db

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

# --- GERENCIAMENTO DE ESTADO (MEMÓRIA + BANCO) ---
def init_session():
    # Carrega do Banco de Dados na inicialização
    if 'db_loaded' not in st.session_state:
        db_data = load_state_from_db()
        for key, value in db_data.items():
            st.session_state[key] = value
        st.session_state['db_loaded'] = True
        
    # Garante chaves padrão
    defaults = {
        'active_view': None, 'rotation_gif_start_time': None, 
        'lunch_warning_info': None, 'play_sound': False
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

    # Atualiza verificações de checkbox
    for nome in CONSULTORES:
        if f'check_{nome}' not in st.session_state:
            status = st.session_state.status_texto.get(nome, 'Indisponível')
            in_queue = nome in st.session_state.bastao_queue
            st.session_state[f'check_{nome}'] = in_queue or (status != 'Indisponível')

def persist():
    """Salva o session_state relevante no Banco"""
    keys_to_save = [
        'status_texto', 'bastao_queue', 'skip_flags', 'current_status_starts',
        'bastao_start_time', 'bastao_counts', 'priority_return_queue', 'daily_logs'
    ]
    data = {k: st.session_state[k] for k in keys_to_save if k in st.session_state}
    save_state_to_db(data)

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
        st.warning("Selecione o dono atual do bastão para passar.")
        return

    next_holder = find_next_holder(current_holder)
    if not next_holder:
        st.warning("Ninguém elegível na fila!")
        return

    # Atualiza Status
    now = get_brazil_time()
    
    # Remove do atual
    old_st = st.session_state.status_texto.get(current_holder, "")
    new_st_old = old_st.replace("Bastão | ", "").replace("Bastão", "").strip()
    st.session_state.status_texto[current_holder] = new_st_old
    st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
    
    # Adiciona no novo
    old_st_new = st.session_state.status_texto.get(next_holder, "")
    st.session_state.status_texto[next_holder] = f"Bastão | {old_st_new}" if old_st_new else "Bastão"
    
    # Reset Flags
    st.session_state.skip_flags[next_holder] = False
    st.session_state.bastao_start_time = now
    st.session_state.rotation_gif_start_time = now
    st.session_state.play_sound = True
    
    # Notifica
    send_to_chat("bastao", f"🎉 **BASTÃO GIRADO!**\nNovo Responsável: {next_holder}")
    
    persist()
    st.rerun()

def update_status_action(new_status, exit_queue=False):
    name = st.session_state.consultor_selectbox
    if not name or name == "Selecione um nome": return
    
    if exit_queue:
        if name in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(name)
        st.session_state[f'check_{name}'] = False
    
    # Lógica simples de atualização
    current = st.session_state.status_texto.get(name, "")
    if "Bastão" in current and not exit_queue:
        final = f"Bastão | {new_status}"
    else:
        final = new_status
        
    st.session_state.status_texto[name] = final
    st.session_state.current_status_starts[name] = get_brazil_time()
    
    persist()
    st.rerun()

def toggle_queue_action(name):
    if name in st.session_state.bastao_queue:
        st.session_state.bastao_queue.remove(name)
        st.session_state[f'check_{name}'] = False
    else:
        st.session_state.bastao_queue.append(name)
        st.session_state[f'check_{name}'] = True
        st.session_state.skip_flags[name] = False
        st.session_state.status_texto[name] = "" # Limpa indisponivel
    persist()

# --- INTERFACE ---
init_session()
st_autorefresh(interval=10000, key='refresher')

# Cabeçalho e Fogos
st.markdown("## Controle Bastão Cesupe 2026 🥂")
if st.session_state.rotation_gif_start_time:
    if (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 10:
        st.image("https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif", width=150)

if st.session_state.play_sound:
    st.components.v1.html(f'<audio autoplay="true"><source src="https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3" type="audio/mpeg"></audio>', height=0)
    st.session_state.play_sound = False

c1, c2 = st.columns([1.5, 1])

with c1:
    # Quem está com o bastão
    holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), "Ninguém")
    st.info(f"**COM O BASTÃO:** {holder}")
    
    # Próximos
    next_h = find_next_holder(holder)
    st.markdown(f"**Próximo:** {next_h if next_h else 'Ninguém elegível'}")
    
    st.markdown("---")
    
    # Controles
    st.session_state.consultor_selectbox = st.selectbox("Selecione seu nome:", ["Selecione um nome"] + CONSULTORES)
    
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    c_btn1.button("🎯 Passar Bastão", on_click=rotate_bastao, use_container_width=True)
    
    if st.button("📋 Atividade", use_container_width=True):
        st.session_state.active_view = 'atividade'
    if st.button("🍽️ Almoço", use_container_width=True):
        update_status_action("Almoço", exit_queue=True)

    # Views Expansíveis
    if st.session_state.active_view == 'atividade':
        with st.container(border=True):
            tipo = st.selectbox("Tipo:", ["HP", "E-mail", "WhatsApp", "Outros"])
            if st.button("Confirmar"):
                update_status_action(f"Atividade: {tipo}")
                st.session_state.active_view = None
                st.rerun()

    # Certidão
    with st.expander("🖨️ Gerar Certidão"):
        tipo_c = st.selectbox("Tipo", ["Geral", "Física"])
        motivo = st.text_area("Motivo")
        if st.button("Gerar DOCX"):
            buf = gerar_docx_certidao(tipo_c, "", "", "", motivo)
            st.download_button("Baixar", buf, "certidao.docx")
            send_to_chat("certidao", f"{st.session_state.consultor_selectbox} gerou certidão.")

with c2:
    st.markdown("### Fila e Status")
    
    # Renderiza lista
    for nome in CONSULTORES:
        c_n, c_chk = st.columns([0.8, 0.2])
        status = st.session_state.status_texto.get(nome, "")
        in_queue = nome in st.session_state.bastao_queue
        
        # Checkbox controla entrada/saida da fila
        c_chk.checkbox("", value=in_queue, key=f"chk_ui_{nome}", 
                       on_change=toggle_queue_action, args=(nome,))
        
        color = "black"
        if "Bastão" in status: color = "orange"
        elif "Almoço" in status: color = "red"
        elif not in_queue: color = "grey"
        
        c_n.markdown(f"<span style='color:{color}'>**{nome}**</span> <small>{status}</small>", unsafe_allow_html=True)

# Rodapé Debug (Opcional)
# st.write(st.session_state.bastao_queue)
