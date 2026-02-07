import streamlit as st
from dashboard import render_dashboard

# ============================================
# CONFIGURAÇÃO DAS EQUIPES (NOVOS NOMES)
# ============================================
EQUIPES = {
    "Equipe Legados": {
        "id": 1,
        "nome_exibicao": "Equipe Legados",
        "webhook_key": "bastao_eq1",
        "url_app": "https://controle-bastao-equipe1.streamlit.app",
        "consultores": [
            "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
            "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
            "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
        ]
    },
    "Equipe Eproc": {
        "id": 2,
        "nome_exibicao": "Equipe Eproc",
        "webhook_key": "bastao_eq2",
        "url_app": "https://controle-bastao-cesupe.streamlit.app",
        "consultores": [
            "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", 
            "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", 
            "Michael Douglas", "Morôni", "Pablo Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
        ]
    }
}

# ============================================
# INTERFACE DE ENTRADA
# ============================================
st.set_page_config(page_title="Central Bastão TJMG", layout="wide", page_icon="⚖️")

# CSS para esconder elementos padrão e deixar mais limpo
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
    .stDeployButton {display: none;}
</style>
""", unsafe_allow_html=True)

if "time_selecionado" not in st.session_state:
    st.session_state["time_selecionado"] = None

# TELA DE LOGIN (SELEÇÃO)
if st.session_state["time_selecionado"] is None:
    st.markdown("<h1 style='text-align: center; color: #FF8C00;'>🔐 Central Unificada de Bastão</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Selecione sua equipe para acessar o painel.</p>", unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        for nome_chave, dados in EQUIPES.items():
            if st.button(f"🚀 Acessar {dados['nome_exibicao']}", use_container_width=True, type="secondary"):
                st.session_state["time_selecionado"] = nome_chave
                st.rerun()

# DASHBOARD CARREGADO
else:
    chave = st.session_state["time_selecionado"]
    dados_time = EQUIPES[chave]
    
    # Define o ID da "Outra Equipe" para a função de espiar
    outro_id = 2 if dados_time["id"] == 1 else 1
    nome_outra_equipe = "Equipe Eproc" if dados_time["id"] == 1 else "Equipe Legados"
    
    # CHAMA O MOTOR (dashboard.py)
    render_dashboard(
        team_id=dados_time["id"],
        team_name=dados_time["nome_exibicao"],
        consultores_list=dados_time["consultores"],
        webhook_key=dados_time["webhook_key"],
        app_url=dados_time["url_app"],
        other_team_id=outro_id,
        other_team_name=nome_outra_equipe
    )
