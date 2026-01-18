import streamlit as st
import pandas as pd
from datetime import datetime
import time
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import pytz
from supabase import create_client

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Gestão Cesupe 2026", layout="wide", page_icon="🛡️")

# 2. ESTILIZAÇÃO CSS
st.markdown("""
    <style>
    div[data-testid="column"] { padding: 0px 2px !important; }
    .title-card { padding: 4px; border-radius: 4px; color: white; font-weight: 700; text-align: center; width: 100%; margin-bottom: 6px; text-transform: uppercase; font-size: 10px; box-shadow: 0 1px 2px rgba(0,0,0,0.1); letter-spacing: 0.5px; }
    .bg-bastao { background-color: #D4AF37; } .bg-fila { background-color: #20c997; } .bg-atividade { background-color: #0056b3; }
    .bg-reuniao { background-color: #fd7e14; } .bg-projeto { background-color: #8b5cf6; } .bg-treinamento { background-color: #17a2b8; }
    .bg-sessao { background-color: #6f42c1; } .bg-almoco { background-color: #d9534f; } .bg-ausente { background-color: #6c757d; }
    .stPopover { display: flex; justify-content: center; margin-bottom: 4px; }
    div[data-testid="stPopover"] > button { width: 100% !important; font-size: 10px !important; font-weight: 600 !important; background-color: #f0f2f6 !important; border: 1px solid #e0e0e0 !important; border-radius: 12px !important; text-align: left !important; padding: 2px 8px !important; color: #31333F !important; min-height: 28px !important; line-height: 1.2 !important; }
    .header-eproc { background-color: #e7f1ff; border-left: 4px solid #0056b3; padding: 8px; border-radius: 4px; color: #0056b3; font-weight: bold; margin-bottom: 8px; }
    .header-legado { background-color: #f3f3f3; border-left: 4px solid #555; padding: 8px; border-radius: 4px; color: #333; font-weight: bold; margin-bottom: 8px; }
    .block-container { padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1KFt_JH5HPTPC9c0_1oJZJHGfKyUqZB1AMXwaDLrvQwk/edit?usp=sharing"
REFRESH_INT = 60; FUSO_BR = pytz.timezone('America/Sao_Paulo')

LISTA_LEGADOS = ["Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"]
LISTA_EPROC = ["Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"]
TODOS_CONSULTORES = sorted(LISTA_LEGADOS + LISTA_EPROC)

def identificar_sistema(n): return "Eproc" if n in LISTA_EPROC else "Legados"
def encurtar_nome(n): p = n.split(); return n if len(p) <= 2 else (f"{p[0]} {p[-1]}" if len(n) > 20 else n)
def formatar_negrito(t): return f"{t.split('|')[0].strip()} | **{t.split('|')[1].strip()}**" if "|" in str(t) else str(t).replace("Disponível", "Bastão")

@st.cache_resource
def get_supabase_client():
    try: return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except: return None

@st.cache_data(ttl=REFRESH_INT)
def carregar_dados_do_banco():
    sb = get_supabase_client()
    if not sb: return pd.DataFrame()
    try:
        resp = sb.table("app_state").select("data").eq("id", 1).execute()
        if not resp.data: return pd.DataFrame()
        raw = resp.data[0]['data'].get('daily_logs', [])
        if not raw: return pd.DataFrame()
        df = pd.DataFrame(raw)
        if 'timestamp' in df.columns: df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert(FUSO_BR).dt.tz_localize(None)
        df = df.rename(columns={'consultor': 'Consultor', 'new_status': 'Status Atual', 'timestamp': 'Data e Horário'})
        df = df.sort_values('Data e Horário', ascending=True).groupby('Consultor').last().reset_index()
        df['Sistema'] = df['Consultor'].apply(identificar_sistema)
        return df
    except: return pd.DataFrame()

if 'last_ref' not in st.session_state: st.session_state.last_ref = time.time()
if 'show_eproc' not in st.session_state: st.session_state.show_eproc = True
if 'show_legado' not in st.session_state: st.session_state.show_legado = True
st_autorefresh(interval=1000, key="timer_main")
if max(0, REFRESH_INT - int(time.time() - st.session_state.last_ref)) == 0:
    st.session_state.last_ref = time.time(); st.cache_data.clear(); st.rerun()

df_status = carregar_dados_do_banco()
todos_df = pd.DataFrame({'Consultor': TODOS_CONSULTORES})
if not df_status.empty: df_status = pd.merge(todos_df, df_status, on='Consultor', how='left')
else: df_status = todos_df; df_status['Status Atual'] = "Indisponível"; df_status['Data e Horário'] = None
df_status['Sistema'] = df_status['Consultor'].apply(identificar_sistema)
df_status['Status Atual'] = df_status['Status Atual'].fillna("Indisponível")

dono_bastao_real = None
if not df_status.empty:
    cand = df_status[df_status['Status Atual'] == "Bastão"].copy()
    if not cand.empty: cand = cand.sort_values('Data e Horário', ascending=False); dono_bastao_real = cand.iloc[0]['Consultor']
    
    def classificar(row):
        s, n = str(row['Status Atual']), row['Consultor']
        if n == dono_bastao_real: return "Bastão"
        if "Fila Bastão" in s: return "Fila Bastão"
        for k in ["Almoço", "Reunião", "Sessão", "Ausente", "Projeto", "Treinamento"]:
            if k in s: return k
        if "Atividade" in s: return "Atividade"
        return "Ausente"
    df_status['Categoria Visual'] = df_status.apply(classificar, axis=1)

col_h, col_p = st.columns([2, 1])
with col_h: 
    c1, c2 = st.columns([0.1, 0.9]); c1.write("# 🛡️"); c2.title("Gestão Cesupe 2026")
    b1, b2 = st.columns([1, 4]); 
    if b1.button("🔄 Atualizar", use_container_width=True): st.session_state.last_ref = time.time(); st.cache_data.clear(); st.rerun()
    b2.link_button("📂 Planilha", SHEET_URL)

with col_p:
    t1, t2 = st.tabs(["📊", "🏆"])
    with t1:
        if not df_status.empty:
            c = df_status['Categoria Visual'].value_counts().reset_index(); c.columns=['S','Q']
            colors = {'Bastão':'#D4AF37','Fila Bastão':'#20c997','Ausente':'#6c757d','Almoço':'#d9534f'}
            fig = px.pie(c, values='Q', names='S', hole=.5); fig.update_traces(marker=dict(colors=[colors.get(x,'#999') for x in c['S']])); fig.update_layout(height=150, margin=dict(t=0,b=0,l=0,r=0)); st.plotly_chart(fig, use_container_width=True)
    with t2: st.info("Ranking indisponível.")

st.divider()

def render_grid(df, cats):
    cols = st.columns(9)
    for i, (n, css) in enumerate(cats):
        with cols[i]:
            st.markdown(f'<div class="title-card {css}">{n}</div>', unsafe_allow_html=True)
            if df.empty: continue
            filt = df[df['Categoria Visual'] == n]
            
            # ORDENAÇÃO TEMPORAL
            if n == "Bastão": filt = filt.sort_values('Data e Horário', ascending=False)
            elif n == "Fila Bastão": filt = filt.sort_values('Data e Horário', ascending=True) # Antiguidade
            else: filt = filt.sort_values('Consultor')

            if filt.empty: st.markdown(f"<div style='text-align:center;color:#ccc'>-</div>", unsafe_allow_html=True)
            else:
                for j, (ix, r) in enumerate(filt.iterrows()):
                    lbl = f"⏩ {encurtar_nome(r['Consultor'])} (PRÓXIMO)" if n == "Fila Bastão" and j==0 else f"{'🔵' if r['Sistema']=='Eproc' else '⚫'} {encurtar_nome(r['Consultor'])}"
                    with st.popover(lbl, use_container_width=True):
                        st.write(f"**{r['Consultor']}**\n{formatar_negrito(r['Status Atual'])}")
                        if pd.notna(r['Data e Horário']):
                            d = (datetime.now(FUSO_BR).replace(tzinfo=None) - r['Data e Horário'].replace(tzinfo=None)).total_seconds()
                            st.caption(f"Tempo: {int(d//3600):02d}:{int((d%3600)//60):02d}")

cats = [("Bastão", "bg-bastao"), ("Fila Bastão", "bg-fila"), ("Atividade", "bg-atividade"), ("Reunião", "bg-reuniao"), ("Projeto", "bg-projeto"), ("Treinamento", "bg-treinamento"), ("Sessão", "bg-sessao"), ("Almoço", "bg-almoco"), ("Ausente", "bg-ausente")]

if st.toggle("🔵 Equipe Eproc", value=st.session_state.show_eproc, key="show_eproc"):
    with st.container(border=True): render_grid(df_status[df_status['Sistema']=='Eproc'], cats)
st.write("")
if st.toggle("⚫ Equipe Legados", value=st.session_state.show_legado, key="show_legado"):
    with st.container(border=True): render_grid(df_status[df_status['Sistema']=='Legados'], cats)
