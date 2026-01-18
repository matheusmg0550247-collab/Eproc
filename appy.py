# -*- coding: utf-8 -*-
import streamlit as st
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import re
import random

# --- IMPORTAÇÃO DOS MÓDULOS (Certifique-se que utils.py e repository.py estão na pasta) ---
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
            print("Tentando carregar do Supabase...")
            db_data = load_state_from_db()
            if db_data:
                for key, value in db_data.items():
                    st.session_state[key] = value
                print("Estado carregado do banco com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar estado inicial (usando padrões): {e}")
        st.session_state['db_loaded'] = True
        
    # 2. Garante chaves padrão (Salva o app se o banco estiver vazio ou falhar)
    now_br = get_brazil_time()
    
    # Lista completa de todas as variáveis que seu app precisa para não quebrar
    defaults = {
        'active_view': None, 
        'rotation_gif_start_time': None, 
        'lunch_warning_info': None, 
        'play_sound': False,
        'consultor_selectbox': "Selecione um nome",
        # Variáveis Críticas de Lógica
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'current_status_starts': {nome: now_br for nome in CONSULTORES},
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'daily_logs': []
    }
    
    # Aplica os padrões se a chave não existir
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 3. Atualiza verificações de checkbox (Agora é seguro pois 'status_texto' existe)
    for nome in CONSULTORES:
        if f'check_{nome}' not in st.session_state:
            # .get() previne erro, mas o passo 2 já garantiu a existência
            status = st.session_state.status_texto.get(nome, 'Indisponível')
            in_queue = nome in st.session_state.bastao_queue
            # Marca como True se estiver na fila OU se não estiver Indisponível
            st.session_state[f'check_{nome}'] = in_queue or (status != 'Indisponível')

def persist():
    """Salva o session_state relevante no Banco Supabase"""
    keys_to_save = [
        'status_texto', 'bastao_queue', 'skip_flags', 'current_status_starts',
        'bastao_start_time', 'bastao_counts', 'priority_return_queue', 'daily_logs'
    ]
    # Cria um dicionário apenas com o que importa salvar
    data = {k: st.session_state[k] for k in keys_to_save if k in st.session_state}
    
    # Envia para o repository.py salvar
    save_state_to_db(data)

# --- LÓGICA DO BASTÃO ---
def find_next_holder(current_holder):
    queue = st.session_state.bastao_queue
    if not queue: return None
    
    start_idx = 0
    if current_holder in queue:
        start_idx = (queue.index(current_holder) + 1) % len(queue)
    
    # Procura circularmente
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
    # Descobre quem tem o bastão agora
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    if selected != current_holder:
        st.warning(f"Ação inválida! O bastão está com {current_holder}. Apenas ele(a) pode passar.")
        return

    next_holder = find_next_holder(current_holder)
    if not next_holder:
        st.warning("Ninguém elegível na fila para receber o bastão!")
        return

    # Atualiza Status
    now = get_brazil_time()
    
    # 1. Tira do atual
    old_st = st.session_state.status_texto.get(current_holder, "")
    # Remove a string "Bastão" e limpa espaços
    new_st_old = old_st.replace("Bastão | ", "").replace("Bastão", "").strip()
    # Se ficou vazio, vira Indisponível (ou mantém vazio se preferir lógica de fila pura)
    if not new_st_old: new_st_old = "Indisponível"
    
    st.session_state.status_texto[current_holder] = new_st_old
    st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
    
    # 2. Passa para o novo
    old_st_new = st.session_state.status_texto.get(next_holder, "")
    # Se ele já tinha status (ex: Projeto), vira "Bastão | Projeto"
    if old_st_new and old_st_new != "Indisponível":
        st.session_state.status_texto[next_holder] = f"Bastão | {old_st_new}"
    else:
        st.session_state.status_texto[next_holder] = "Bastão"
    
    # 3. Reset Flags e Sinais
    st.session_state.skip_flags[next_holder] = False
    st.session_state.bastao_start_time = now
    st.session_state.rotation_gif_start_time = now
    st.session_state.play_sound = True
    
    # 4. Notifica Chat
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
        # Remove flags de pular
        if name in st.session_state.skip_flags:
            del st.session_state.skip_flags[name]
    
    # Lógica de atualização de texto
    current = st.session_state.status_texto.get(name, "")
    
    # Se a pessoa tem o bastão, não queremos apagar o "Bastão" a menos que ela saia da fila totalmente
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
    """Função chamada ao clicar no checkbox da lista"""
    # Inverte o estado lógico baseado no checkbox
    # O Streamlit já atualizou o st.session_state[key], então lemos de lá ou verificamos a lista
    
    # Verifica se já estava na fila
    if name in st.session_state.bastao_queue:
        # Se estava, remove (pois o usuário desmarcou ou queremos tirar)
        st.session_state.bastao_queue.remove(name)
        st.session_state[f'check_{name}'] = False
        st.session_state.status_texto[name] = "Indisponível"
    else:
        # Se não estava, adiciona
        st.session_state.bastao_queue.append(name)
        st.session_state[f'check_{name}'] = True
        st.session_state.skip_flags[name] = False
        # Se estava como indisponível, limpa
        if st.session_state.status_texto.get(name) == "Indisponível":
            st.session_state.status_texto[name] = "" 
            
    persist()

# --- INICIALIZAÇÃO ---
init_session()
st_autorefresh(interval=10000, key='refresher')

# --- INTERFACE VISUAL ---

# 1. Cabeçalho
st.markdown("## Controle Bastão Cesupe 2026 🥂")

# Gif de Rotação (Dura 10 segundos após a troca)
if st.session_state.rotation_gif_start_time:
    if (datetime.now() - st.session_state.rotation_gif_start_time).total_seconds() < 10:
        st.image("https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif", width=150)

# Áudio (Toca uma vez)
if st.session_state.play_sound:
    st.components.v1.html(f'<audio autoplay="true"><source src="https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3" type="audio/mpeg"></audio>', height=0)
    st.session_state.play_sound = False

# Layout Principal
c1, c2 = st.columns([1.5, 1])

with c1:
    # --- ÁREA DE CONTROLE ---
    
    # Quem está com o bastão
    holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), "Ninguém")
    
    # Estilo do Card
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #FFD700;">
        <h3 style="margin:0; color: #000;">COM O BASTÃO:</h3>
        <h1 style="margin:0; color: #000080;">{holder}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Mostra o Próximo
    next_h = find_next_holder(holder)
    st.caption(f"⏭️ **Próximo da fila:** {next_h if next_h else 'Ninguém elegível'}")
    
    st.markdown("---")
    
    # Seletor de Usuário
    st.session_state.consultor_selectbox = st.selectbox(
        "Quem é você?", 
        ["Selecione um nome"] + CONSULTORES,
        index=0
    )
    
    # Botões de Ação Rápida
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    
    # Botão Passar (Só funciona se for o dono ou admin, mas aqui deixamos aberto com aviso)
    c_btn1.button("🎯 Passar Bastão", on_click=rotate_bastao, use_container_width=True)
    
    # Botão Atividade (Abre submenu)
    if c_btn2.button("📋 Atividade", use_container_width=True):
        st.session_state.active_view = 'atividade'
    
    # Botão Almoço (Sai da fila)
    if c_btn3.button("🍽️ Almoço", use_container_width=True):
        update_status_action("Almoço", exit_queue=True)

    st.markdown("###") # Espaço

    # --- SUBMENUS (VIEWS) ---
    
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

    # --- EXPANDER CERTIDÃO ---
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
                # Gera em memória
                buf = gerar_docx_certidao(tipo_c, c_proc, datetime.now(), c_chamado, c_motivo)
                st.download_button(
                    label="⬇️ Baixar Arquivo",
                    data=buf,
                    file_name="certidao_gerada.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                # Notifica
                send_to_chat("certidao", f"📄 **Certidão Gerada** por {st.session_state.consultor_selectbox} (Tipo: {tipo_c})")

with c2:
    st.markdown("### 🚦 Fila e Status")
    
    # Container para lista com scroll se ficar muito grande
    with st.container(height=600):
        # Renderiza lista de Consultores
        # Ordenamos: Primeiro quem tem Bastão, depois quem tá na Fila, depois o resto
        
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
            
            # Checkbox controla entrada/saida da fila diretamente
            # Usamos on_change para disparar a ação de banco
            c_chk.checkbox(
                " ", 
                value=in_queue, 
                key=f"chk_ui_{nome}", 
                on_change=toggle_queue_action, 
                args=(nome,),
                label_visibility="collapsed"
            )
            
            # Definição de Cores e Ícones
            icon = ""
            color = "#333" # Preto padrão
            bg_color = "transparent"
            border = "none"
            
            if "Bastão" in status:
                icon = "🥂"
                color = "#000080" # Azul escuro
                bg_color = "#FFF8DC" # Dourado claro
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
            
            # Renderiza o "Card" do consultor na lista
            html_card = f"""
            <div style="
                padding: 5px 10px; 
                margin-bottom: 5px; 
                background-color: {bg_color}; 
                border: {border}; 
                border-radius: 5px;
                display: flex; justify-content: space-between; align-items: center;
            ">
                <span style="color: {color}; font-weight: 500;">{icon} {nome}</span>
                <span style="font-size: 0.8em; color: #666;">{status}</span>
            </div>
            """
            c_row.markdown(html_card, unsafe_allow_html=True)

# Rodapé simples
st.divider()
st.caption("Sistema Cesupe 2026 | Powered by Streamlit & Supabase")
