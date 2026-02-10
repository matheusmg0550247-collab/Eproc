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

# --- Se o dashboard pedir volta ao menu, garante que estamos no login ---
if st.session_state.get("_force_back_to_names"):
    st.session_state["time_selecionado"] = None
    st.session_state["consultor_logado"] = None
    st.session_state["_force_back_to_names"] = False

# ============================================================
# LISTAS (por equipe)
# ============================================================

CONSULTORES_EPROC = [
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
]

# Legados (Equipe 1) – mantendo nomes “canônicos” (curtos) usados no dashboard
CONSULTORES_LEGADOS = [
    "Alex Paulo",
    "Dirceu Gonçalves",
    "Douglas De Souza",
    "Hugo Leonardo",
    "Farley Leonardo",
    "Gleis Da Silva",
    "Jerry Marcos",
    "Jonatas Gomes",
    "Leandro Victor",
    "Luiz Henrique",
    "Marcelo Dos Santos",
    "Marina Silva",
    "Marina Torres",
    "Vanessa Ligiane",
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
        "other_team_name": "Legados",
    },
    "Legados": {
        "team_id": 1,
        "team_name": "Legados",
        "consultores": CONSULTORES_LEGADOS,
        "webhook_key": "legados",
        "app_url": "https://controle-bastao-cesupe.streamlit.app",
        "other_team_id": 2,
        "other_team_name": "Eproc",
    },
}

# ============================================================
# CSS (cards, cores por equipe, hover e espaçamentos)
# ============================================================

st.markdown(
    """
<style>
/* ---------- Layout geral ---------- */
.main .block-container{
  padding-top: 1.2rem;
  padding-bottom: 2rem;
}

/* reduz gaps entre colunas/linhas */
div[data-testid="stHorizontalBlock"]{ gap: .6rem; }
div[data-testid="stVerticalBlock"] > div{ gap: .55rem; }
div[data-testid="stButton"]{ margin: 0; }

/* ---------- Hero ---------- */
.login-wrap{
  max-width: 1200px;
  margin: 0 auto;
}
.hero{
  border: 1px solid rgba(0,0,0,.06);
  border-radius: 18px;
  padding: 18px 18px 14px 18px;
  background: linear-gradient(180deg, rgba(255,140,0,.09), rgba(255,255,255,0));
}
.hero h1{
  margin: 0;
  font-size: 1.55rem;
}
.hero p{
  margin: 6px 0 0 0;
  color: rgba(0,0,0,.65);
}

/* ---------- Banners por equipe (cor de fundo como no Excel) ---------- */
.team-banner{
  border-radius: 14px;
  padding: 10px 12px;
  margin: .35rem 0 .65rem 0;
  border: 1px solid rgba(0,0,0,.06);
}
.team-banner .t-title{
  font-weight: 800;
  margin: 0;
}
.team-banner .t-sub{
  margin: 2px 0 0 0;
  opacity: .85;
  font-size: .92rem;
}
.team-eproc-banner{
  background: linear-gradient(135deg, rgba(33,150,243,.18), rgba(33,150,243,.06));
}
.team-legados-banner{
  background: linear-gradient(135deg, rgba(141,110,99,.22), rgba(141,110,99,.06));
}

/* ---------- Cards (botões) ---------- */
.card-grid [data-testid="stButton"] > button{
  height: 54px;
  border-radius: 16px;
  border: 1px solid rgba(0,0,0,.08);
  font-weight: 800;
  letter-spacing: .2px;
  transition: transform .10s ease, box-shadow .10s ease, filter .10s ease;
}

/* Eproc (azul) */
.team-eproc .card-grid [data-testid="stButton"] > button{
  color: #ffffff;
  border: 0;
  background: linear-gradient(135deg, #1E88E5 0%, #64B5F6 100%);
  box-shadow: 0 2px 10px rgba(30,136,229,.18);
}

/* Legados (marrom) */
.team-legados .card-grid [data-testid="stButton"] > button{
  color: #ffffff;
  border: 0;
  background: linear-gradient(135deg, #6D4C41 0%, #A1887F 100%);
  box-shadow: 0 2px 10px rgba(109,76,65,.18);
}

/* Hover / Active */
.card-grid [data-testid="stButton"] > button:hover{
  transform: translateY(-2px);
  filter: brightness(1.05);
  box-shadow: 0 10px 22px rgba(0,0,0,.14);
}
.card-grid [data-testid="stButton"] > button:active{
  transform: translateY(0px) scale(.995);
  filter: brightness(.98);
}

/* Nota pequena */
.small-note{
  color: rgba(0,0,0,.55);
  font-size: .92rem;
  margin-top: -2px;
}
</style>
""",
    unsafe_allow_html=True,
)

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

    def render_cards(lista, equipe_nome: str, wrap_class: str):
        # gap="small" deixa os botões mais “colados”
        try:
            cols = st.columns(4, gap="small")
        except TypeError:
            cols = st.columns(4)
        for i, nome in enumerate(lista):
            with cols[i % 4]:
                st.markdown(f'<div class="{wrap_class}"><div class="card-grid">', unsafe_allow_html=True)
                if st.button(nome, use_container_width=True, key=f"login_{equipe_nome}_{nome}"):
                    st.session_state["time_selecionado"] = equipe_nome
                    st.session_state["consultor_logado"] = nome
                    st.rerun()
                st.markdown("</div></div>", unsafe_allow_html=True)

    with tab_eproc:
        st.markdown(
            """
<div class="team-banner team-eproc-banner">
  <div class="t-title">Equipe Eproc (2ª Instância)</div>
  <div class="t-sub">Clique no seu nome para entrar no painel.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="team-eproc">', unsafe_allow_html=True)
        render_cards(CONSULTORES_EPROC, "Eproc", "team-eproc")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab_legados:
        st.markdown(
            """
<div class="team-banner team-legados-banner">
  <div class="t-title">Equipe Legados (Themis/JPe/SIAP etc.)</div>
  <div class="t-sub">Clique no seu nome para entrar no painel.</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="team-legados">', unsafe_allow_html=True)
        render_cards(CONSULTORES_LEGADOS, "Legados", "team-legados")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

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
