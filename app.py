# -*- coding: utf-8 -*-
import streamlit as st
from urllib.parse import quote
from typing import List, Tuple

# ============================================
# CONFIG
# ============================================
st.set_page_config(
    page_title="Central Unificada de Bastão",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TEAM_ID_EPROC = 2     # App State: Eproc = ID 02 (Supabase)
TEAM_ID_LEGADOS = 1   # App State: Legados = ID 01 (Supabase)

EQUIPE_EPROC = [
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves",
    "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno",
    "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Mol", "Ranyer Segal",
    "Sarah Leal", "Victoria Lisboa",
]

EQUIPE_LEGADOS = [
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley", "Gleis", "Hugo Leonardo",
    "Jerry Marcos", "Jonatas", "Leandro", "Luiz Henrique", "Marcelo dos Santos Dutra",
    "Marina", "Mariana Silva", "Marina Torres", "Vanessa Ligiane",
]

JUSTICE_EMOJIS = ["⚖️", "🧑‍⚖️", "🏛️", "📜", "🔎", "🗂️", "🔏", "🪪"]

def _emoji_for(name: str) -> str:
    try:
        idx = sum(ord(c) for c in name) % len(JUSTICE_EMOJIS)
        return JUSTICE_EMOJIS[idx]
    except Exception:
        return "⚖️"

def _inject_css():
    st.markdown(
        """
<style>
/* layout geral */
.block-container { padding-top: 1.2rem !important; max-width: 1500px; }
footer, header { visibility: hidden; height: 0; }

/* cabeçalho */
.hero {
  background: linear-gradient(135deg, rgba(255,140,0,0.10), rgba(255,255,255,0.7));
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 18px;
  padding: 18px 18px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  margin-bottom: 12px;
}
.hero h1 { margin: 0; font-size: 1.55rem; }
.hero p { margin: 6px 0 0 0; color: rgba(0,0,0,0.62); }

/* tabs mais limpas */
div[data-baseweb="tab-list"] { gap: 8px; }
button[data-baseweb="tab"] { padding: 10px 14px !important; }

/* cards (links) */
.grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; }
@media (max-width: 1200px){ .grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 850px){ .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }

.card {
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none !important;
  height: 52px;
  border-radius: 14px;
  font-weight: 800;
  letter-spacing: .2px;
  border: 0;
  background-size: 220% 220%;
  background-position: 0% 50%;
  transition: transform .12s ease, box-shadow .12s ease, filter .12s ease, background-position .22s ease;
  box-shadow: 0 10px 24px rgba(0,0,0,0.08);
  user-select: none;
}

.card:hover{
  transform: translateY(-1px);
  background-position: 100% 50%;
  box-shadow: 0 0 0 2px rgba(255,255,255,0.35) inset, 0 14px 34px rgba(0,0,0,0.12);
  filter: brightness(1.06);
}

.card-eproc{
  color: #fff !important;
  background-image: linear-gradient(135deg, rgba(30,136,229,.95), rgba(144,202,249,.90));
}

.card-legados{
  color: #fff !important;
  background-image: linear-gradient(135deg, rgba(121,85,72,.95), rgba(215,204,200,.92));
}

/* banners de equipe */
.banner {
  border:1px solid rgba(0,0,0,0.06);
  border-radius: 14px;
  padding: 12px 14px;
  margin-bottom: 10px;
  color: rgba(0,0,0,0.78);
}
.banner small{ color: rgba(0,0,0,0.62); }

</style>
        """,
        unsafe_allow_html=True,
    )

def _read_query_params() -> Tuple[str, str]:
    # Compatível com versões diferentes do Streamlit
    team = None
    user = None
    try:
        qp = st.query_params
        team = qp.get("team")
        user = qp.get("user")
    except Exception:
        qp = st.experimental_get_query_params()
        team = (qp.get("team") or [None])[0]
        user = (qp.get("user") or [None])[0]
    if isinstance(team, list): team = team[0] if team else None
    if isinstance(user, list): user = user[0] if user else None
    return (team, user)

def _clear_query_params():
    try:
        st.query_params.clear()
    except Exception:
        st.experimental_set_query_params()

def _enter_dashboard(team_name: str, user_name: str):
    st.session_state["time_selecionado"] = team_name
    st.session_state["consultor_logado"] = user_name
    st.session_state["_force_enter_dashboard"] = True
    _clear_query_params()
    st.rerun()

def _render_card_grid(team_name: str, nomes: List[str], css_class: str):
    cards = []
    for nome in nomes:
        emoji = _emoji_for(nome)
        href = f"?team={quote(team_name)}&user={quote(nome)}"
        cards.append(f'<a class="card {css_class}" href="{href}">{emoji} {nome}</a>')
    st.markdown('<div class="grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

def main():
    _inject_css()

    # --- captura clique via query params (mais leve que st.button) ---
    q_team, q_user = _read_query_params()
    if q_team and q_user:
        if q_team == "Eproc" and q_user in EQUIPE_EPROC:
            _enter_dashboard("Eproc", q_user)
        if q_team == "Legados" and q_user in EQUIPE_LEGADOS:
            _enter_dashboard("Legados", q_user)

    # Se já logado, vai direto pro dashboard
    if st.session_state.get("_force_enter_dashboard") and st.session_state.get("consultor_logado"):
        # Import lazy (evita lentidão/ram na tela de login)
        from dashboard import render_dashboard

        nome = st.session_state.get("consultor_logado")
        time_sel = st.session_state.get("time_selecionado")

        if time_sel == "Eproc":
            render_dashboard(
                team_id=TEAM_ID_EPROC,
                team_name="Eproc",
                consultores_list=EQUIPE_EPROC,
                webhook_key=st.secrets.get("n8n", {}).get("bastao_giro", ""),
                app_url=st.secrets.get("app", {}).get("url_cloud", ""),
                other_team_id=TEAM_ID_LEGADOS,
                other_team_name="Legados",
                usuario_logado=nome,
            )
        else:
            render_dashboard(
                team_id=TEAM_ID_LEGADOS,
                team_name="Legados",
                consultores_list=EQUIPE_LEGADOS,
                webhook_key=st.secrets.get("n8n", {}).get("bastao_giro", ""),
                app_url=st.secrets.get("app", {}).get("url_cloud", ""),
                other_team_id=TEAM_ID_EPROC,
                other_team_name="Eproc",
                usuario_logado=nome,
            )
        return

    # --- LOGIN ---
    st.markdown(
        """
<div class="hero">
  <h1>🔐 Central Unificada de Bastão</h1>
  <p>Escolha a equipe e clique no seu nome para entrar no painel.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    tab_eproc, tab_legados = st.tabs(["Eproc", "Legados"])

    with tab_eproc:
        st.markdown(
            """<div class="banner" style="background: linear-gradient(135deg, rgba(30,136,229,0.14), rgba(255,255,255,0.65));">
                  <b>Equipe Eproc</b> <small>(2ª Instância)</small><br/>
                  <small>Passe o mouse para ver o efeito de luz.</small>
                </div>""",
            unsafe_allow_html=True,
        )
        _render_card_grid("Eproc", EQUIPE_EPROC, "card-eproc")

    with tab_legados:
        st.markdown(
            """<div class="banner" style="background: linear-gradient(135deg, rgba(121,85,72,0.16), rgba(255,255,255,0.70));">
                  <b>Equipe Legados</b><br/>
                  <small>Passe o mouse para ver o efeito de luz.</small>
                </div>""",
            unsafe_allow_html=True,
        )
        _render_card_grid("Legados", EQUIPE_LEGADOS, "card-legados")

if __name__ == "__main__":
    main()
