import streamlit as st
from dashboard import render_dashboard

# Configuração da Página (Título e Ícone)
st.set_page_config(
    page_title="Controle de Bastão",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =================================================
# CONFIGURAÇÕES DA EQUIPE
# =================================================
# Ajuste estes valores conforme a sua necessidade real

# 1. Identificação da Equipe Principal
TEAM_ID = 2
TEAM_NAME = "Equipe EPROC"

# 2. Lista de Consultores (Pode copiar a mesma do dashboard ou personalizar)
CONSULTORES = sorted([
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", 
    "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", 
    "Michael Douglas", "Morôni", "Pablo Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
])

# 3. Configurações de Integração (Webhooks e URLs)
# Se estiver usando st.secrets, pode trocar por: st.secrets["n8n"]["webhook_key"]
WEBHOOK_KEY = "sua_chave_aqui_se_houver" 
APP_URL = "https://controle-bastao-cesupe.streamlit.app"

# 4. Configuração da "Outra Equipe" (Para visão cruzada no painel lateral)
# Se não houver, pode deixar None ou 0
OTHER_TEAM_ID = 1
OTHER_TEAM_NAME = "Equipe Legados"

# =================================================
# EXECUÇÃO DO DASHBOARD
# =================================================

# Tenta pegar o usuário logado (simulação simples ou vazio)
usuario_logado = st.session_state.get('consultor_selectbox', 'Selecione um nome')

# Chama a função principal do arquivo dashboard.py
render_dashboard(
    team_id=TEAM_ID,
    team_name=TEAM_NAME,
    consultores_list=CONSULTORES,
    webhook_key=WEBHOOK_KEY,
    app_url=APP_URL,
    other_team_id=OTHER_TEAM_ID,
    other_team_name=OTHER_TEAM_NAME,
    usuario_logado=usuario_logado
)
