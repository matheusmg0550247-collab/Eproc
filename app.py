# -*- coding: utf-8 -*-
import streamlit as st
from dashboard import render_dashboard

st.set_page_config(page_title="Central Bastão TJMG", page_icon="🧭", layout="wide")

st.sidebar.title("Central Bastão")
equipe = st.sidebar.radio("Equipe", ["⚖️ Eproc", "🏛️ Legados"], index=0)

TEAM_MAP = {
    "🏛️ Legados": (1, "Legados"),
    "⚖️ Eproc": (2, "Eproc"),
}

team_id, team_name = TEAM_MAP[equipe]
other_team_id = 1 if team_id == 2 else 2
other_team_name = "Legados" if team_name == "Eproc" else "Eproc"

# Renderiza apenas a equipe selecionada (evita misturar filas/estado entre equipes)
render_dashboard(team_id=team_id, team_name=team_name, other_team_id=other_team_id, other_team_name=other_team_name)
# -*- coding: utf-8 -*-
import streamlit as st
from dashboard import render_dashboard

st.set_page_config(page_title="Central Unificada do Bastão", page_icon="🧭", layout="wide")

EQUIPES = {
    "Equipe Legados": {
        "team_id": 1,
        "team_name": "Equipe Legados",
        "consultores_list": [
            "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva",
            "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor",
            "Luiz Henrique", "Marcelo Dos Santos", "Marina Marques", "Marina Amaral", "Vanessa Ligiane"
        ],
        "webhook_key": "bastao_eq1",
        "app_url": "http://138.197.212.187:8501",
        "other_team_id": 2,
        "other_team_name": "Equipe EPROC",
    },
    "Equipe EPROC": {
        "team_id": 2,
        "team_name": "Equipe EPROC",
        "consultores_list": [
            "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres",
            "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra",
            "Michael Douglas", "Morôni", "Pablo Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
        ],
        "webhook_key": "bastao_eq2",
        "app_url": "http://138.197.212.187:8501",
        "other_team_id": 1,
        "other_team_name": "Equipe Legados",
    }
}

TEAM_SLUG = {"Equipe Legados": "legados", "Equipe EPROC": "eproc"}
SLUG_TEAM = {v: k for k, v in TEAM_SLUG.items()}

def _get_team_from_query():
    try:
        qp = st.query_params
        raw = (qp.get("team") or qp.get("equipe") or "").strip().lower()
        return SLUG_TEAM.get(raw)
    except Exception:
        return None

def _set_team_query(team_name: str):
    try:
        st.query_params["team"] = TEAM_SLUG.get(team_name, "")
    except Exception:
        pass

st.session_state.setdefault("consultor_logado", None)
st.session_state.setdefault("time_selecionado", None)

team_from_q = _get_team_from_query()
if team_from_q and not st.session_state.get("consultor_logado"):
    st.session_state.time_selecionado = team_from_q

if not st.session_state.get("time_selecionado"):
    st.session_state.time_selecionado = "Equipe EPROC"
_set_team_query(st.session_state.time_selecionado)

# Header
c1, c2 = st.columns([1, 1])
with c1:
    st.title("🧭 Central Unificada do Bastão")
    st.caption("Selecione o time e clique no seu nome para entrar.")
with c2:
    st.markdown(
        f"""<div style="text-align:right;margin-top:8px;">
        <a href="{EQUIPES[st.session_state.time_selecionado]['app_url']}" target="_blank"
           style="text-decoration:none;padding:8px 12px;border-radius:10px;border:1px solid #ddd;color:#111;background:#fff;display:inline-block;">
           🌐 Abrir em nova guia
        </a>
        </div>""", unsafe_allow_html=True
    )

st.divider()

# Voltar
if st.session_state.consultor_logado:
    colA, colB = st.columns([1, 3])
    with colA:
        if st.button("↩️ Voltar (trocar consultor)", use_container_width=True):
            st.session_state.consultor_logado = None
            st.rerun()
    with colB:
        st.info(f"Logado como **{st.session_state.consultor_logado}** em **{st.session_state.time_selecionado}**.")

# Seleção de time (somente se não estiver logado)
if not st.session_state.consultor_logado:
    team_options = list(EQUIPES.keys())
    idx = team_options.index(st.session_state.time_selecionado) if st.session_state.time_selecionado in team_options else 0
    team_choice = st.radio("Escolha a equipe", team_options, index=idx, horizontal=True, key="team_radio_selector")
    if team_choice != st.session_state.time_selecionado:
        st.session_state.time_selecionado = team_choice
        _set_team_query(team_choice)
        st.rerun()

# Login (nomes)
if not st.session_state.consultor_logado:
    equipe = EQUIPES[st.session_state.time_selecionado]
    st.subheader(f"👥 {equipe['team_name']}")
    cols = st.columns(4)
    for i, nome in enumerate(equipe["consultores_list"]):
        with cols[i % 4]:
            if st.button(f"👤 {nome}", key=f"btn_{TEAM_SLUG[equipe['team_name']]}_{nome}", use_container_width=True):
                st.session_state.consultor_logado = nome
                st.session_state.time_selecionado = equipe["team_name"]
                _set_team_query(equipe["team_name"])
                st.rerun()

# Dashboard
else:
    equipe = EQUIPES[st.session_state.time_selecionado]
    render_dashboard(
        team_id=equipe["team_id"],
        team_name=equipe["team_name"],
        consultores_list=equipe["consultores_list"],
        webhook_key=equipe["webhook_key"],
        app_url=equipe["app_url"],
        other_team_id=equipe["other_team_id"],
        other_team_name=equipe["other_team_name"],
        usuario_logado=st.session_state.consultor_logado
    )
