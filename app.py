# -*- coding: utf-8 -*-
import streamlit as st
from urllib.parse import quote
from typing import List, Tuple

# ============================================
# CONFIG
# ============================================
st.set_page_config(
    page_title="Central Bastão - Legados",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TEAM_ID = 1
TEAM_NAME = "Legados"

CONSULTORES: List[str] = [
    "Alex Paulo da Silva",
    "Dirceu Gonçalves Siqueira Neto",
    "Douglas de Souza Gonçalves",
    "Hugo Leonardo Murta",
    "Farley Leandro de Oliveira Juliano",
    "Gleis da Silva Rodrigues",
    "Igor Dayrell Gonçalves Correa",
    "Jerry Marcos dos Santos Neto",
    "Jonatas Gomes Saraiva",
    "Leandro Victor Catharino",
    "Luiz Henrique Barros Oliveira",
    "Marcelo dos Santos Dutra",
    "Marina Silva Marques",
    "Marina Torres do Amaral",
    "Vanessa Ligiane Pimenta Santos"
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
.block-container { padding-top: 1.2rem !important; max-width: 1500px; }
footer, header { visibility: hidden; height: 0; }

.hero {
  background: linear-gradient(135deg, rgba(121,85,72,0.16), rgba(255,255,255,0.70));
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 18px;
  padding: 18px 18px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
  margin-bottom: 12px;
}
.hero h1 { margin: 0; font-size: 1.55rem; }
.hero p { margin: 6px 0 0 0; color: rgba(0,0,0,0.62); }

.grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
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
  color: #fff !important;
  background-image: linear-gradient(135deg, rgba(121,85,72,.95), rgba(215,204,200,.92));
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

def _enter_dashboard(user_name: str):
    st.session_state["time_selecionado"] = TEAM_NAME
    st.session_state["team_id"] = TEAM_ID
    st.session_state["team_name"] = TEAM_NAME
    st.session_state["consultor_logado"] = user_name
    st.session_state["_force_enter_dashboard"] = True
    _clear_query_params()
    st.rerun()

def _render_card_grid(nomes: List[str]):
    cards = []
    for nome in nomes:
        emoji = _emoji_for(nome)
        href = f"?team={quote(TEAM_NAME)}&user={quote(nome)}"
        cards.append(f'<a class="card" href="{href}">{emoji} {nome}</a>')
    st.markdown('<div class="grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

def main():
    _inject_css()

    # Clique por query params (mais leve que st.button)
    q_team, q_user = _read_query_params()
    if q_user and (q_team in [None, TEAM_NAME]) and (q_user in CONSULTORES):
        _enter_dashboard(q_user)

    # Se já logado, vai direto pro dashboard
    if st.session_state.get("_force_enter_dashboard") and st.session_state.get("consultor_logado"):
        from dashboard import render_dashboard  # lazy import

        show_other = bool(st.secrets.get("features", {}).get("show_other_team_queue", False))
        other_team_id = 2 if show_other else 0
        other_team_name = "Eproc" if show_other else ""

        render_dashboard(
            team_id=TEAM_ID,
            team_name=TEAM_NAME,
            consultores_list=CONSULTORES,
            webhook_key=st.secrets.get("n8n", {}).get("bastao_giro", ""),
            app_url=st.secrets.get("app", {}).get("url_cloud", ""),
            other_team_id=other_team_id,
            other_team_name=other_team_name,
            usuario_logado=st.session_state.get("consultor_logado"),
        )
        return

    # --- LOGIN ---
    st.markdown(
        f"""
<div class="hero">
  <h1>🔐 Central de Bastão — {TEAM_NAME}</h1>
  <p>Clique no seu nome para entrar no painel.</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """<div class="banner">
              <b>Equipe Legados</b><br/>
              <small>Lista padronizada conforme planilha oficial.</small>
            </div>""",
        unsafe_allow_html=True,
    )
    _render_card_grid(CONSULTORES)

if __name__ == "__main__":
    main()
