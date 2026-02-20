# -*- coding: utf-8 -*-
import streamlit as st

# ============================================
# APP (EPROC) - ENTRA DIRETO NO DASHBOARD
# ============================================

st.set_page_config(
    page_title="Fila EPROC",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

TEAM_ID_EPROC = 2  # Supabase app_state.id

EQUIPE_EPROC = [
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves",
    "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno",
    "Marcelo Pena Guerra", "Michael Douglas", "Morôni", "Pablo Mol", "Ranyer Segal",
    "Sarah Leal", "Victoria Lisboa",
]


def main():
    # Import lazy (melhor RAM / tempo de start)
    from dashboard import render_dashboard

    render_dashboard(
        team_id=TEAM_ID_EPROC,
        team_name="EPROC",
        consultores_list=EQUIPE_EPROC,
        webhook_key=st.secrets.get("n8n", {}).get("bastao_giro", ""),
        app_url=st.secrets.get("app", {}).get("url_cloud", ""),
        other_team_id=None,          # não exibe outra equipe
        other_team_name="",
        usuario_logado="",           # sem tela de login
    )


if __name__ == "__main__":
    main()
