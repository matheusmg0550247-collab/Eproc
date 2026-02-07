import streamlit as st
from dashboard import render_dashboard

# ============================================
# CONFIGURAÇÃO DAS EQUIPES
# ============================================
EQUIPES = {
    "Equipe 1": {
        "id": 1,
        "nome_exibicao": "Equipe 1",
        "webhook_key": "bastao_eq1", # Nome da chave que colocaremos no secrets.toml
        "url_app": "https://controle-bastao-equipe1.streamlit.app", # Apenas referência
        "consultores": [
            "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
            "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
            "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
        ]
    },
    "Equipe 2 (Cesupe)": {
        "id": 2,
        "nome_exibicao": "Equipe 2 - Cesupe",
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

# Estado de sessão para persistir a escolha
if "time_selecionado" not in st.session_state:
    st.session_state["time_selecionado"] = None

# SE NENHUM TIME FOI SELECIONADO, MOSTRA O MENU
if st.session_state["time_selecionado"] is None:
    st.markdown("<h1 style='text-align: center; color: #FF8C00;'>🔐 Central Unificada de Bastão</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Selecione sua equipe para acessar o painel de controle.</p>", unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        for nome_chave, dados in EQUIPES.items():
            # Botão grande para cada equipe
            if st.button(f"🚀 Acessar {dados['nome_exibicao']}", use_container_width=True, type="secondary"):
                st.session_state["time_selecionado"] = nome_chave
                st.rerun()
                
    st.markdown("<br><br><p style='text-align: center; color: grey; font-size: 0.8rem;'>Sistema Unificado - 2026</p>", unsafe_allow_html=True)

# SE UM TIME JÁ FOI SELECIONADO, CARREGA O DASHBOARD
else:
    chave = st.session_state["time_selecionado"]
    dados_time = EQUIPES[chave]
    
    # Barra lateral para trocar de equipe
    with st.sidebar:
        st.caption(f"Logado em: **{dados_time['nome_exibicao']}**")
        if st.button("🔙 Trocar Equipe", use_container_width=True):
            st.session_state["time_selecionado"] = None
            st.cache_data.clear() # Limpa cache visual ao trocar
            st.rerun()
        st.divider()

    # CHAMA O MOTOR (dashboard.py)
    render_dashboard(
        team_id=dados_time["id"],
        team_name=dados_time["nome_exibicao"],
        consultores_list=dados_time["consultores"],
        webhook_key=dados_time["webhook_key"],
        app_url=dados_time["url_app"]
    )
