import os
import streamlit as st

# ============================================
# CONFIGURAÇÃO DAS EQUIPES E MEMBROS
# ============================================
EQUIPES = {
    "Equipe Legados": {
        "id": 1,
        "cor": "#FF8C00",  # Laranja
        "icone": "🏛️",
        "consultores": [
            "Alex Paulo",
            "Dirceu Gonçalves",
            "Douglas De Souza",
            "Farley Leandro",
            "Gleis Da Silva",
            "Hugo Leonardo",
            "Igor Dayrell",
            "Jerry Marcos",
            "Jonatas Gomes",
            "Leandro Victor",
            "Luiz Henrique",
            "Marcelo Dos Santos",
            "Marina Silva",
            "Marina Torres",
            "Vanessa Ligiane",
        ],
    },
    "Equipe Eproc": {
        "id": 2,
        "cor": "#1E88E5",  # Azul
        "icone": "⚖️",
        "consultores": [
            "Barbara Mara",
            "Bruno Glaicon",
            "Claudia Luiza",
            "Douglas Paiva",
            "Fábio Alves",
            "Glayce Torres",
            "Isabela Dias",
            "Isac Candido",
            "Ivana Guimarães",
            "Leonardo Damaceno",
            "Marcelo PenaGuerra",
            "Michael Douglas",
            "Morôni",
            "Pablo Mol",
            "Ranyer Segal",
            "Sarah Leal",
            "Victoria Lisboa",
        ],
    },
}

# ============================================
# CONFIGURAÇÃO DO APP
# ============================================
st.set_page_config(page_title="Central Bastão TJMG", layout="wide", page_icon="⚖️")

from dashboard import render_dashboard

# URL base do app (para montar links no dashboard)
# - 1ª opção: st.secrets["app"]["url"]
# - 2ª opção: variável de ambiente APP_URL
# - fallback: IP atual informado por você
APP_URL = (
    st.secrets.get("app", {}).get("url")
    or os.getenv("APP_URL")
    or "http://157.230.167.24:8501"
)

# CSS: Cards, limpeza visual e remoção de menu padrão
st.markdown(
    """
<style>
    [data-testid="stSidebarNav"] {display: none;}
    .stDeployButton {display: none;}

    /* Estilo dos Botões da Home para parecerem Cards */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        height: auto;
        min-height: 60px;
        padding: 15px 10px;
        border: 1px solid #ddd;
        background-color: #f8f9fa;
        color: #333;
        transition: all 0.3s;
        text-align: left;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 10px;
        white-space: nowrap;
    }
    div.stButton > button:hover {
        border-color: #111;
        background-color: #f2f2f2;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    div.stButton > button p {
        font-size: 16px;
        font-weight: 600;
        margin: 0;
        white-space: nowrap;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Inicialização de Estado de Login
if "time_selecionado" not in st.session_state:
    st.session_state["time_selecionado"] = None
if "consultor_logado" not in st.session_state:
    st.session_state["consultor_logado"] = None

# ============================================
# TELA DE SELEÇÃO (LOGIN)
# ============================================
if st.session_state["time_selecionado"] is None:
    st.markdown(
        "<h1 style='text-align: center; color: #111;'>🔐 Central Unificada de Bastão</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #444;'>Selecione seu nome para entrar no sistema:</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # Prepara lista unificada de todos os consultores
    todos_consultores = []
    for nome_eq, dados in EQUIPES.items():
        for c in dados["consultores"]:
            todos_consultores.append({"nome": c, "equipe": nome_eq, "dados": dados})

    # Ordena alfabeticamente
    todos_consultores.sort(key=lambda x: x["nome"])

    # Renderiza Grade (5 colunas)
    cols = st.columns(5)
    for i, user in enumerate(todos_consultores):
        col = cols[i % 5]
        with col:
            label = f"{user['dados']['icone']} {user['nome']}"
            if st.button(label, key=f"btn_{user['nome']}", use_container_width=True):
                st.session_state["time_selecionado"] = user["equipe"]
                st.session_state["consultor_logado"] = user["nome"]
                st.rerun()

# ============================================
# DASHBOARD (LOGADO)
# ============================================
else:
    chave = st.session_state["time_selecionado"]
    dados_time = EQUIPES[chave]

    # Outra equipe (apenas para visualização cruzada)
    outro_id = 2 if dados_time["id"] == 1 else 1
    nome_outra_equipe = "Equipe Eproc" if dados_time["id"] == 1 else "Equipe Legados"

    render_dashboard(
        team_id=dados_time["id"],
        team_name=dados_time.get("nome_exibicao", chave),
        consultores_list=dados_time["consultores"],
        webhook_key="bastao_eq1" if dados_time["id"] == 1 else "bastao_eq2",
        app_url=APP_URL,
        other_team_id=outro_id,
        other_team_name=nome_outra_equipe,
        usuario_logado=st.session_state["consultor_logado"],
    )
