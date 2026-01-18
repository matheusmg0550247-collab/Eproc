import streamlit as st
import pandas as pd
from datetime import datetime
import time
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
import pytz
from supabase import create_client

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(
    page_title="Gestão Cesupe 2026",
    layout="wide",
    page_icon="🛡️"
)

# 2. ESTILIZAÇÃO CSS
st.markdown("""
    <style>
    div[data-testid="column"] { padding: 0px 2px !important; }
    .title-card {
        padding: 4px; border-radius: 4px; color: white; font-weight: 700;
        text-align: center; width: 100%; margin-bottom: 6px;
        text-transform: uppercase; font-size: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1); letter-spacing: 0.5px;
    }
    .bg-bastao { background-color: #D4AF37; }
    .bg-fila { background-color: #20c997; }
    .bg-atividade { background-color: #0056b3; }
    .bg-reuniao { background-color: #fd7e14; }
    .bg-projeto { background-color: #8b5cf6; }
    .bg-treinamento { background-color: #17a2b8; }
    .bg-sessao { background-color: #6f42c1; }
    .bg-almoco { background-color: #d9534f; }
    .bg-ausente { background-color: #6c757d; }
    
    .stPopover { display: flex; justify-content: center; margin-bottom: 4px; }
    div[data-testid="stPopover"] > button {
        width: 100% !important; font-size: 10px !important; font-weight: 600 !important;
        background-color: #f0f2f6 !important; border: 1px solid #e0e0e0 !important; border-radius: 12px !important;
        text-align: left !important; padding: 2px 8px !important; color: #31333F !important;
        white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;
        min-height: 28px !important; height: auto !important; line-height: 1.2 !important;
    }
    div[data-testid="stPopover"] > button:hover {
        border-color: #b0b0b0 !important; background-color: #e6e9ef !important; color: #000 !important;
    }
    .header-eproc { background-color: #e7f1ff; border-left: 4px solid #0056b3; padding: 8px; border-radius: 4px; color: #0056b3; font-weight: bold; margin-bottom: 8px; }
    .header-legado { background-color: #f3f3f3; border-left: 4px solid #555; padding: 8px; border-radius: 4px; color: #333; font-weight: bold; margin-bottom: 8px; }
    div[data-testid="stCheckbox"] label { font-size: 18px !important; font-weight: 700 !important; color: #333 !important; }
    .block-container { padding-top: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONFIGURAÇÕES GLOBAIS
SHEET_URL = "https://docs.google.com/spreadsheets/d/1KFt_JH5HPTPC9c0_1oJZJHGfKyUqZB1AMXwaDLrvQwk/edit?usp=sharing"
REFRESH_INT = 60 
FUSO_BR = pytz.timezone('America/Sao_Paulo')

LISTA_LEGADOS = [
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
    "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
    "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
]
LISTA_EPROC = [
    "Barbara Mara", "Bruno Glaicon", "Claudia Luiza", "Douglas Paiva", "Fábio Alves", 
    "Glayce Torres", "Isabela Dias", "Isac Candido", "Ivana Guimarães", "Leonardo Damaceno", 
    "Marcelo PenaGuerra", "Michael Douglas", "Morôni", "Pablo Victor Lenti Mol", 
    "Ranyer Segal", "Sarah Leal", "Victoria Lisboa"
]
TODOS_CONSULTORES = sorted(LISTA_LEGADOS + LISTA_EPROC)

def identificar_sistema(nome):
    return "Eproc" if nome in LISTA_EPROC else "Legados"

def encurtar_nome(nome_completo):
    partes = nome_completo.split()
    if len(partes) <= 2: return nome_completo
    if len(nome_completo) > 20: return f"{partes[0]} {partes[-1]}"
    return nome_completo

def formatar_negrito(texto):
    if pd.isna(texto) or not texto: return ""
    texto_limpo = str(texto).replace("Disponível", "Bastão")
    if "|" in texto_limpo:
        partes = texto_limpo.split("|", 1)
        return f"{partes[0].strip()} | **{partes[1].strip()}**"
    return texto_limpo

# --- CONEXÃO COM SUPABASE ---
@st.cache_resource
def get_supabase_client():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro config Supabase: {e}")
        return None

@st.cache_data(ttl=REFRESH_INT)
def carregar_dados_do_banco():
    """Lê o estado atual do banco e retorna DataFrames processados."""
    supabase = get_supabase_client()
    if not supabase: return pd.DataFrame(), pd.DataFrame()

    try:
        response = supabase.table("app_state").select("data").eq("id", 1).execute()
        if not response.data: return pd.DataFrame(), pd.DataFrame()
        
        data = response.data[0]['data']
        
        status_texto = data.get('status_texto', {})
        status_starts = data.get('current_status_starts', {})
        bastao_queue = data.get('bastao_queue', []) 
        skip_flags = data.get('skip_flags', {}) 
        
        raw_logs = data.get('daily_logs', [])
        df_logs = pd.DataFrame(raw_logs)
        if not df_logs.empty:
            if 'timestamp' in df_logs.columns:
                df_logs['Data e Horário'] = pd.to_datetime(df_logs['timestamp'], utc=True).dt.tz_convert(FUSO_BR).dt.tz_localize(None)
            df_logs = df_logs.rename(columns={'consultor': 'Consultor', 'new_status': 'Status Atual'})

        rows = []
        for consultor in TODOS_CONSULTORES:
            status = status_texto.get(consultor, "Indisponível")
            if not status: status = "Indisponível"
            
            start_str = status_starts.get(consultor, None)
            start_dt = None
            if start_str:
                try: start_dt = pd.to_datetime(start_str).tz_convert(FUSO_BR).tz_localize(None)
                except: 
                    try: start_dt = pd.to_datetime(start_str)
                    except: pass
            
            na_fila = consultor in bastao_queue
            pulando = skip_flags.get(consultor, False)
            
            rows.append({
                "Consultor": consultor,
                "Status Atual": status,
                "Data e Horário": start_dt,
                "Sistema": identificar_sistema(consultor),
                "Na Fila": na_fila,
                "Pulando": pulando
            })
            
        df_status = pd.DataFrame(rows)
        return df_status, df_logs

    except Exception as e:
        print(f"Erro ao ler banco: {e}")
        return pd.DataFrame(), pd.DataFrame()

# 4. REFRESH E ESTADO
if 'last_ref' not in st.session_state: st.session_state.last_ref = time.time()
if 'show_eproc' not in st.session_state: st.session_state.show_eproc = True
if 'show_legado' not in st.session_state: st.session_state.show_legado = True

st_autorefresh(interval=1000, key="timer_main")
restante = max(0, REFRESH_INT - int(time.time() - st.session_state.last_ref))
if restante == 0:
    st.session_state.last_ref = time.time()
    st.cache_data.clear()
    st.rerun()

# 5. PROCESSAMENTO
df_status, df_logs_hist = carregar_dados_do_banco()

ranking_bastoes = pd.DataFrame()
if not df_logs_hist.empty:
    hoje = datetime.now(FUSO_BR).date()
    logs_hoje = df_logs_hist[df_logs_hist['Data e Horário'].dt.date == hoje].copy()
    bastoes_hj = logs_hoje[
        (logs_hoje['Status Atual'].str.contains("Bastão", na=False)) & 
        (~logs_hoje['Status Atual'].str.contains("Fila", na=False))
    ]
    ranking_bastoes = bastoes_hj['Consultor'].value_counts().reset_index()
    ranking_bastoes.columns = ['Consultor', 'Qtd']

# --- DEFINIÇÃO DO DONO REAL ---
dono_bastao_real = None
if not df_status.empty:
    candidatos = df_status[df_status['Status Atual'].str.contains("Bastão", na=False)].copy()
    if not candidatos.empty:
        candidatos = candidatos.sort_values('Data e Horário', ascending=False)
        dono_bastao_real = candidatos.iloc[0]['Consultor']

def classificar_categoria(row):
    consultor = row['Consultor']
    status = str(row['Status Atual'])
    
    if consultor == dono_bastao_real: return "Bastão"
    if row['Na Fila']: return "Fila Bastão"
    for k in ["Almoço", "Reunião", "Sessão", "Ausente", "Projeto", "Treinamento"]:
        if k in status: return k
    if "Atividade" in status: return "Atividade"
    return "Ausente"

if not df_status.empty:
    df_status['Categoria Visual'] = df_status.apply(classificar_categoria, axis=1)

# --- DASHBOARD VISUAL ---
col_h, col_p = st.columns([2, 1])
now_br = datetime.now(FUSO_BR)

with col_h:
    c1, c2 = st.columns([0.1, 0.9])
    with c1: st.write("# 🛡️")
    with c2:
        st.title("Gestão Cesupe 2026")
        st.caption(f"Hoje: {now_br.strftime('%d/%m')} | Atualização: **{restante}s**")

    b1, b2 = st.columns([1, 4])
    with b1:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.session_state.last_ref = time.time()
            st.cache_data.clear()
            st.rerun()
    with b2:
        st.link_button("📂 Planilha", SHEET_URL)

with col_p:
    t_g1, t_g2 = st.tabs(["📊 Status", "🏆 Ranking"])
    with t_g1:
        if not df_status.empty:
            contagem = df_status['Categoria Visual'].value_counts().reset_index()
            contagem.columns = ['Status', 'Qtd']
            cores = {'Bastão':'#D4AF37','Fila Bastão':'#20c997','Ausente':'#6c757d','Almoço':'#d9534f',
                     'Sessão':'#6f42c1','Reunião':'#fd7e14','Projeto':'#8b5cf6','Atividade':'#0056b3'}
            fig = px.pie(contagem, values='Qtd', names='Status', hole=.5)
            fig.update_traces(marker=dict(colors=[cores.get(x, '#999') for x in contagem['Status']]), textinfo='value')
            fig.update_layout(showlegend=True, height=200, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)
    
    with t_g2:
        if not ranking_bastoes.empty:
            fig_bar = px.bar(ranking_bastoes.head(5), x='Consultor', y='Qtd', text='Qtd')
            fig_bar.update_traces(marker_color='#D4AF37')
            fig_bar.update_layout(height=200, margin=dict(t=10,b=0,l=0,r=0), xaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sem dados.")

st.divider()

# --- RENDERIZAÇÃO DAS COLUNAS (SEM ÍCONE DE SISTEMA NO LABEL) ---
def renderizar_grid(df_sistema, cats):
    cols = st.columns(9)
    for i, (n_col, css) in enumerate(cats):
        with cols[i]:
            st.markdown(f'<div class="title-card {css}">{n_col}</div>', unsafe_allow_html=True)
            
            if df_sistema.empty:
                continue

            filtrados = df_sistema[df_sistema['Categoria Visual'] == n_col]

            proximo_nome = None 

            if n_col == "Bastão":
                if not filtrados.empty: filtrados = filtrados.sort_values('Data e Horário', ascending=False)
            
            elif n_col == "Fila Bastão":
                if not filtrados.empty: 
                    filtrados = filtrados.sort_values('Data e Horário', ascending=True)
                    for _, row_f in filtrados.iterrows():
                        if not row_f['Pulando']:
                            proximo_nome = row_f['Consultor']
                            break
            else:
                filtrados = filtrados.sort_values('Consultor')

            if filtrados.empty:
                st.markdown(f"<div style='text-align:center; color:#ccc; font-size:12px;'>-</div>", unsafe_allow_html=True)
            else:
                for j, (idx_df, row) in enumerate(filtrados.iterrows()):
                    nome = encurtar_nome(row['Consultor'])
                    status_full = str(row['Status Atual'])
                    sis_class = "header-eproc" if row['Sistema'] == "Eproc" else "header-legado"
                    
                    # LABEL LIMPO (SEM CÍRCULO DO SISTEMA)
                    label = f"{nome}"
                    
                    # 1. DESTAQUES DE FILA (SEMÁFORO)
                    if n_col == "Bastão":
                         label = f"🟡 {nome}"
                    
                    elif n_col == "Fila Bastão":
                        if row['Consultor'] == proximo_nome:
                            label = f"🟢 {nome} :green[(PRÓXIMO)]"
                        elif row['Pulando']:
                            label = f"🟠 {nome} :orange[(PULOU)]"
                    
                    # 2. DETALHES DE TEXTO
                    if ":" in status_full:
                        detalhe = status_full.split(":", 1)[1].strip()
                        if "|" in detalhe: detalhe = detalhe.split("|")[0].strip()
                        if len(detalhe) > 12: detalhe = detalhe[:10] + "..."
                        label += f" - {detalhe}"

                    with st.popover(label, use_container_width=True):
                        st.markdown(f"<div class='{sis_class}'>{row['Consultor']}</div>", unsafe_allow_html=True)
                        st.write(f"Status: {formatar_negrito(status_full)}")
                        
                        if pd.notna(row['Data e Horário']):
                            agora = datetime.now(FUSO_BR).replace(tzinfo=None)
                            inicio = row['Data e Horário']
                            if inicio.tzinfo: inicio = inicio.replace(tzinfo=None)
                            
                            diff = agora - inicio
                            seg = int(diff.total_seconds())
                            if seg < 0: seg = 0
                            h, r = divmod(seg, 3600)
                            m, s = divmod(r, 60)
                            st.metric("Tempo no status", f"{h:02d}:{m:02d}:{s:02d}")
                            st.caption(f"Desde: {inicio.strftime('%H:%M')}")

cats = [
    ("Bastão", "bg-bastao"), 
    ("Fila Bastão", "bg-fila"), 
    ("Atividade", "bg-atividade"), 
    ("Reunião", "bg-reuniao"), 
    ("Projeto", "bg-projeto"), 
    ("Treinamento", "bg-treinamento"),
    ("Sessão", "bg-sessao"), 
    ("Almoço", "bg-almoco"), 
    ("Ausente", "bg-ausente")
]

df_eproc = df_status[df_status['Sistema'] == 'Eproc']
df_legado = df_status[df_status['Sistema'] == 'Legados']

eproc_on = st.toggle("🔵 Equipe Eproc", value=st.session_state.show_eproc, key="show_eproc")
if eproc_on:
    with st.container(border=True):
        renderizar_grid(df_eproc, cats)

st.write("") 

legado_on = st.toggle("⚫ Equipe Legados", value=st.session_state.show_legado, key="show_legado")
if legado_on:
    with st.container(border=True):
        renderizar_grid(df_legado, cats)
