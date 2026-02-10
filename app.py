import streamlit as st
from dashboard import render_dashboard

# ============================================================
# Central Unificada de Bastão - Tela de Entrada (Login)
# ============================================================

st.set_page_config(
    page_title="Central Unificada de Bastão",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CSS (Cards / Botões) ---
st.markdown(
    """
<style>
/* Centraliza e dá cara de "card" */
.login-wrap{
  max-width: 1100px;
  margin: 0 auto;
}
.hero{
  border: 1px solid rgba(0,0,0,.06);
  border-radius: 18px;
  padding: 18px 18px 14px 18px;
  background: linear-gradient(180deg, rgba(255,140,0,.10), rgba(255,255,255,0));
}
.hero h1{
  margin: 0;
  font-size: 1.55rem;
}
.hero p{
  margin: 6px 0 0 0;
  color: rgba(0,0,0,.65);
}
.card-grid [data-testid="stButton"] > button{
  height: 56px;
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,.08);
  font-weight: 700;
  transition: transform .06s ease, box-shadow .06s ease;
}
.card-grid [data-testid="stButton"] > button:hover{
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(0,0,0,.08);
}
.small-note{
  color: rgba(0,0,0,.55);
  font-size: .9rem;
}
</style>
""",
    unsafe_allow_html=True,
)

# --- Se o dashboard pedir volta ao menu, garante que estamos no login ---
if st.session_state.get("_force_back_to_names"):
    st.session_state["time_selecionado"] = None
    st.session_state["consultor_logado"] = None
    st.session_state["_force_back_to_names"] = False

CONSULTORES_EPROC = [
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves",
    "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães",
    "Leonardo Damaceno", "Marcelo PenaGuerra", "Michael Douglas", "Morôni",
    "Pablo Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
]

CONSULTORES_LEGADOS = [
    "Alex Paulo", "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Dirceu Gonçalves",
    "Douglas De Souza", "Farley", "Fábio Alves", "Gilberto", "Glayce Torres",
    "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno",
    "Marcelo PenaGuerra", "Matheus", "Michael Douglas", "Morôni", "Pablo Mol",
    "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
]

# Configurações por equipe
EQUIPES = {
    "Eproc": {
        "team_id": 2,
        "team_name": "Eproc",
        "consultores": CONSULTORES_EPROC,
        "webhook_key": "eproc",
        "app_url": "https://controle-bastao-cesupe.streamlit.app",
        "other_team_id": 1,
        "other_team_name": "Legados"
    },
    "Legados": {
        "team_id": 1,
        "team_name": "Legados",
        "consultores": CONSULTORES_LEGADOS,
        "webhook_key": "legados",
        "app_url": "https://controle-bastao-cesupe.streamlit.app",
        "other_team_id": 2,
        "other_team_name": "Eproc"
    }
}

# ============================================================
# LOGIN / ROTEAMENTO
# ============================================================

cfg = None
if st.session_state.get("time_selecionado") in ("Eproc", "Legados"):
    cfg = EQUIPES[st.session_state["time_selecionado"]]

if cfg is None:
    # Tela inicial
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)

    st.markdown(
        """
<div class="hero">
  <h1>🔐 Central Unificada de Bastão</h1>
  <p>Escolha sua equipe e depois seu nome para entrar no painel.</p>
</div>
""",
        unsafe_allow_html=True,
    )

    st.write("")

    tab_eproc, tab_legados = st.tabs(["⚖️ Eproc", "🏛️ Legados"])

    def render_cards(lista, equipe_nome):
        cols = st.columns(4)
        for i, nome in enumerate(lista):
            with cols[i % 4]:
                with st.container():
                    st.markdown('<div class="card-grid">', unsafe_allow_html=True)
                    if st.button(nome, use_container_width=True, key=f"login_{equipe_nome}_{nome}"):
                        st.session_state["time_selecionado"] = equipe_nome
                        st.session_state["consultor_logado"] = nome
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    with tab_eproc:
        st.markdown("<div class='small-note'>Equipe focada no Eproc (2ª Instância).</div>", unsafe_allow_html=True)
        st.write(" ")
        render_cards(CONSULTORES_EPROC, "Eproc")

    with tab_legados:
        st.markdown("<div class='small-note'>Equipe focada em sistemas legados (Themis/JPe/SIAP etc.).</div>", unsafe_allow_html=True)
        st.write(" ")
        render_cards(CONSULTORES_LEGADOS, "Legados")

    st.markdown('</div>', unsafe_allow_html=True)

else:
    # Entrou no Dashboard
    render_dashboard(
        team_id=cfg["team_id"],
        team_name=cfg["team_name"],
        consultores_list=cfg["consultores"],
        webhook_key=cfg["webhook_key"],
        app_url=cfg["app_url"],
        other_team_id=cfg["other_team_id"],
        other_team_name=cfg["other_team_name"],
        usuario_logado=st.session_state.get("consultor_logado"),
    )
