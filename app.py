# -- coding: utf-8 --
import streamlit as st
from urllib.parse import quote
from typing import List, Tuple
from dashboard import render_dashboard

# ============================================
# CONFIG
# ============================================
st.set_page_config(
    page_title="Central Unificada de Bastão",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TEAM_ID_EPROC = 2
TEAM_ID_LEGADOS = 1

EQUIPE_EPROC = [
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves",
    "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno",
    "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Mol", "Ranyer Segal",
    "Sarah Leal", "Victoria Lisboa"
]

EQUIPE_LEGADOS = [
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley", "Gleis", "Hugo Leonardo",
    "Jerry Marcos", "Jonatas", "Leandro", "Luiz Henrique", "Marcelo dos Santos Dutra",
    "Marina", "Mariana Silva", "Marina Torres", "Vanessa Ligiane"
]

def _inject_css():
    st.markdown("""
    <style>
    .block-container { padding-top: 1.2rem !important; max-width: 1500px; }
    .hero {
      background: linear-gradient(135deg, rgba(255,140,0,0.10), rgba(255,255,255,0.7));
      border: 1px solid rgba(0,0,0,0.06);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.05);
      margin-bottom: 12px;
    }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
    .card {
      display: flex; align-items: center; justify-content: center;
      text-decoration: none !important; height: 52px; border-radius: 14px;
      font-weight: 800; color: #fff !important; box-shadow: 0 10px 24px rgba(0,0,0,0.08);
      transition: transform 0.12s ease;
    }
    .card:hover { transform: translateY(-2px); filter: brightness(1.1); }
    .card-eproc { background: linear-gradient(135deg, #1e88e5, #90caf9); }
    .card-legados { background: linear-gradient(135deg, #795548, #d7ccc8); }
    </style>
    """, unsafe_allow_html=True)

def main():
    _inject_css()
    
    # Captura via query params
    q_team = st.query_params.get("team")
    q_user = st.query_params.get("user")

    if q_team and q_user:
        st.session_state["time_selecionado"] = q_team
        st.session_state["consultor_logado"] = q_user
        st.session_state["_force_enter_dashboard"] = True

    if st.session_state.get("_force_enter_dashboard"):
        nome = st.session_state.get("consultor_logado")
        time_sel = st.session_state.get("time_selecionado")

        if time_sel == "Eproc":
            render_dashboard(TEAM_ID_EPROC, "Eproc", EQUIPE_EPROC, 
                             st.secrets.get("n8n", {}).get("bastao_giro", ""),
                             st.secrets.get("app", {}).get("url_cloud", ""),
                             TEAM_ID_LEGADOS, "Legados", nome)
        else:
            render_dashboard(TEAM_ID_LEGADOS, "Legados", EQUIPE_LEGADOS,
                             st.secrets.get("n8n", {}).get("bastao_giro", ""),
                             st.secrets.get("app", {}).get("url_cloud", ""),
                             TEAM_ID_EPROC, "Eproc", nome)
        return

    st.markdown('<div class="hero"><h1>🔐 Central Unificada de Bastão</h1><p>Escolha sua equipe e clique no seu nome.</p></div>', unsafe_allow_html=True)
    
    t1, t2 = st.tabs(["Eproc", "Legados"])
    with t1:
        cols = st.columns(1)
        for nome in EQUIPE_EPROC:
            if st.button(nome, key=f"btn_eproc_{nome}", use_container_width=True):
                st.session_state["time_selecionado"] = "Eproc"
                st.session_state["consultor_logado"] = nome
                st.session_state["_force_enter_dashboard"] = True
                st.rerun()
    with t2:
        for nome in EQUIPE_LEGADOS:
            if st.button(nome, key=f"btn_leg_{nome}", use_container_width=True):
                st.session_state["time_selecionado"] = "Legados"
                st.session_state["consultor_logado"] = nome
                st.session_state["_force_enter_dashboard"] = True
                st.rerun()

if __name__ == "__main__":
    main()
