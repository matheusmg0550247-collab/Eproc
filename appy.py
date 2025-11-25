# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# (Mantenha esta seção)
# ============================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, date, time
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json # Usado para serialização de logs

# --- Constantes de Consultores (Mantidas) ---
CONSULTORES = sorted([
   "Bárbara", "Bruno", "Cláudia", "Douglas", "Fábio", "Glayce", "Isac",
    "Isabela", "Ivana", "Leonardo", "Michael", "Morôni",  "Pablo", "Ranyer",
    "Victoria"
])

# --- FUNÇÃO DE CACHE GLOBAL (Mantida) ---
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    """Inicializa e retorna o dicionário de estado GLOBAL compartilhado."""
    print("--- Inicializando o Cache de Estado GLOBAL (Executa Apenas 1x) ---")
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        'lunch_warning_info': None, # Aviso de almoço Global
        'daily_logs': [] # Log persistente para o relatório
    }

# --- Constantes ---
# Webhook para Relatório Diário (Mantido para a função send_daily_report)
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = ""

# -- Constantes de Registro de Atividade (Mantidas) --
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"

# Webhook para Rascunho de Chamados (Mantido)
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"

# Webhook para Registro de Sessão (MUDOU: Mensagem/Notificação)
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"

# Webhook para Checklist HTML (MUDOU: Retorno do Formulário HTML)
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"

# Dados das Câmaras (Mantidas)
CAMARAS_DICT = {
    "Cartório da 1ª Câmara Cível": "caciv1@tjmg.jus.br",
    "Cartório da 2ª Câmara Cível": "caciv2@tjmg.jus.br",
    "Cartório da 3ª Câmara Cível": "caciv3@tjmg.jus.br",
    "Cartório da 4ª Câmara Cível": "caciv4@tjmg.jus.br",
    "Cartório da 5ª Câmara Cível": "caciv5@tjmg.jus.br",
    "Cartório da 6ª Câmara Cível": "caciv6@tjmg.jus.br",
    "Cartório da 7ª Câmara Cível": "caciv7@tjmg.jus.br",
    "Cartório da 8ª Câmara Cível": "caciv8@tjmg.jus.br",
    "Cartório da 9ª Câmara Cível": "caciv9@tjmg.jus.br",
    "Cartório da 10ª Câmara Cível": "caciv10@tjmg.jus.br",
    "Cartório da 11ª Câmara Cível": "caciv11@tjmg.jus.br",
    "Cartório da 12ª Câmara Cível": "caciv12@tjmg.jus.br",
    "Cartório da 13ª Câmara Cível": "caciv13@tjmg.jus.br",
    "Cartório da 14ª Câmara Cível": "caciv14@tjmg.jus.br",
    "Cartório da 15ª Câmara Cível": "caciv15@tjmg.jus.br",
    "Cartório da 16ª Câmara Cível": "caciv16@tjmg.jus.br",
    "Cartório da 17ª Câmara Cível": "caciv17@tjmg.jus.br",
    "Cartório da 18ª Câmara Cível": "caciv18@tjmg.jus.br",
    "Cartório da 19ª Câmara Cível": "caciv19@tjmg.jus.br",
    "Cartório da 20ª Câmara Cível": "caciv20@tjmg.jus.br",
    "Cartório da 21ª Câmara Cível": "caciv21@tjmg.jus.br"
}
CAMARAS_OPCOES = sorted(list(CAMARAS_DICT.keys()))

# Formulário "Atividade" (Mantidas)
REG_USUARIO_OPCOES = ["Cartório", "Externo", "Gabinete", "Interno"]
REG_SISTEMA_OPCOES = ["Conveniados/Outros", "Eproc", "Themis", "JIPE", "SIAP"]
REG_CANAL_OPCOES = ["Email", "Telefone", "Whatsapp"]
REG_DESFECHO_OPCOES = ["Escalonado", "Resolvido - Cesupe"]
# Formulário "Presencial" (Mantidas)
REG_PRESENCIAL_ATIVIDADE_OPCOES = ["Sessão", "Homologação", "Treinamento", "Chamado/Jira", "Atendimento", "Outros"]

BASTAO_EMOJI = "💙"
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']
STATUSES_DE_SAIDA = ['Atendimento', 'Almoço', 'Saída Temporária', 'Ausente', 'Sessão']
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_LUNCH_WARNING = 'https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGZlbHN1azB3b2drdTI1eG10cDEzeWpmcmtwenZxNTV0bnc2OWgzZSYlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/bNlqpmBJRDMpxulfFB/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
# URL da Imagem Novembro Azul
NOVEMBRO_AZUL_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/novembro-azul.png"

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

# (Funções save_state, load_state, send_chat_notification_internal, play_sound_html,
# send_atividade_to_chat, send_presencial_to_chat, send_chamado_to_chat, 
# send_sessao_to_chat, load_logs, save_logs, log_status_change, format_time_duration, 
# send_daily_report, init_session_state, find_next_holder_index, check_and_assume_baton
# permanecem inalteradas, exceto conforme definido nas constantes)

def date_serializer(obj):
    """Serializador para objetos datetime (usado em logs)."""
    if isinstance(obj, datetime): return obj.isoformat()
    if isinstance(obj, timedelta): return obj.total_seconds()
    if isinstance(obj, (date, time)): return obj.isoformat()
    return str(obj)

def save_state():
    """Salva o estado da sessão local (st.session_state) no cache GLOBAL."""
    global_data = get_global_state_cache()
    try:
        global_data['status_texto'] = st.session_state.status_texto.copy()
        global_data['bastao_queue'] = st.session_state.bastao_queue.copy()
        global_data['skip_flags'] = st.session_state.skip_flags.copy()
        global_data['current_status_starts'] = st.session_state.current_status_starts.copy()
        global_data['bastao_counts'] = st.session_state.bastao_counts.copy()
        global_data['priority_return_queue'] = st.session_state.priority_return_queue.copy()
        global_data['bastao_start_time'] = st.session_state.bastao_start_time
        global_data['report_last_run_date'] = st.session_state.report_last_run_date
        global_data['rotation_gif_start_time'] = st.session_state.get('rotation_gif_start_time')
        global_data['lunch_warning_info'] = st.session_state.get('lunch_warning_info')
        
        global_data['daily_logs'] = json.loads(json.dumps(st.session_state.daily_logs, default=date_serializer))
        
        print(f'*** Estado GLOBAL Salvo (Cache de Recurso) ***')
    except Exception as e: 
        print(f'Erro ao salvar estado GLOBAL: {e}')

def load_state():
    """Carrega o estado do cache GLOBAL."""
    global_data = get_global_state_cache()
    
    loaded_logs = global_data.get('daily_logs', [])
    if loaded_logs and isinstance(loaded_logs[0], dict):
             deserialized_logs = loaded_logs
    else:
        try: 
             deserialized_logs = json.loads(loaded_logs)
        except: 
             deserialized_logs = loaded_logs 
    
    final_logs = []
    for log in deserialized_logs:
        if isinstance(log, dict):
            if 'duration' in log and not isinstance(log['duration'], timedelta):
                try: log['duration'] = timedelta(seconds=float(log['duration']))
                except: log['duration'] = timedelta(0)
            if 'timestamp' in log and isinstance(log['timestamp'], str):
                try: log['timestamp'] = datetime.fromisoformat(log['timestamp'])
                except: log['timestamp'] = datetime.min
            final_logs.append(log)

    loaded_data = {k: v for k, v in global_data.items() if k != 'daily_logs'}
    loaded_data['daily_logs'] = final_logs
    
    return loaded_data

def send_chat_notification_internal(consultor, status):
    """Envia notificação de giro do bastão (não o relatório)."""
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        message_template = "🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {app_url}"
        message_text = message_template.format(consultor=consultor, app_url=APP_URL_CLOUD) 
        chat_message = {"text": message_text}
        try:
            response = requests.post(CHAT_WEBHOOK_BASTAO, json=chat_message)
            response.raise_for_status()
            print(f"Notificação de bastão enviada para {consultor}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar notificação de bastão: {e}")
            return False
    return False


def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'

# --- Função Geradora do HTML Personalizado (ATUALIZADA) ---
def gerar_html_checklist(consultor_nome, camara_nome, data_sessao_formatada):
    """Gera o código HTML do checklist com lógica de abas, data de corte e linguagem inclusiva."""
    
    # ATUALIZADO: Usando o novo webhook para o retorno do formulário HTML
    webhook_destino = GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML
    
    html_template = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Acompanhamento de Sessão - {camara_nome}</title>
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
    .container {{ max-width: 800px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    h1 {{ color: #003366; font-size: 24px; border-bottom: 2px solid #003366; padding-bottom: 10px; margin-bottom: 20px; }}
    .intro-box {{ background-color: #eef4fa; border-left: 5px solid #003366; padding: 15px; margin-bottom: 25px; font-size: 14px; line-height: 1.5; }}
    
    /* Layout lado a lado para Câmara e Responsável */
    .row-flex {{ display: flex; gap: 20px; margin-bottom: 20px; align-items: flex-end; }}
    .col-flex {{ flex: 1; }}
    
    .field-label {{ font-weight: bold; display: block; margin-bottom: 5px; color: #444; }}
    .static-value {{ background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; border-radius: 4px; color: #555; font-weight: 500; min-height: 20px; display: flex; align-items: center; }}
    select, input[type="text"] {{ width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; box-sizing: border-box; }}
    
    .field-group {{ margin-bottom: 20px; }}

    /* Estilo dos Cabeçalhos de Seção (I. Pré-Sessão, II. Pós-Sessão) */
    .section-header {{ background-color: #003366; color: white; padding: 10px 15px; border-radius: 4px; margin-top: 25px; margin-bottom: 15px; font-size: 15px; font-weight: bold; }}
    
    .checklist-title {{ font-size: 22px; font-weight: bold; color: #333; margin-top: 30px; margin-bottom: 5px; }}
    .checklist-desc {{ font-size: 14px; color: #666; font-style: italic; margin-bottom: 20px; }}
    
    .checkbox-item {{ margin-bottom: 15px; display: flex; align-items: flex-start; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
    .checkbox-item:last-child {{ border-bottom: none; }}
    .checkbox-item input[type="checkbox"] {{ margin-right: 10px; margin-top: 3px; width: 18px; height: 18px; accent-color: #003366; cursor: pointer; flex-shrink: 0; }}
    .checkbox-item label {{ cursor: pointer; line-height: 1.4; font-size: 14px; color: #444; }}
    .checkbox-item label strong {{ color: #000; }}
    
    /* Estilo para input de Outros */
    .other-input {{ margin-top: 5px; width: 100%; display: none; margin-left: 28px; }}
    
    .btn-submit {{ background-color: #28a745; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 4px; cursor: pointer; display: block; width: 100%; margin-top: 30px; transition: background 0.3s; font-weight: bold; }}
    .btn-submit:hover {{ background-color: #218838; }}
    
    /* Classe para ocultar/mostrar seções */
    .hidden {{ display: none; }}
</style>
<script>
    function toggleSetor() {{
        const setor = document.getElementById("setor").value;
        const divCartorio = document.getElementById("checklist-cartorio-container");
        const divGabinete = document.getElementById("checklist-gabinete-container");
        
        if (setor === "Cartório") {{
            divCartorio.style.display = "block";
            divGabinete.style.display = "none";
        }} else {{
            divCartorio.style.display = "none";
            divGabinete.style.display = "block";
        }}
    }}

    // Função para mostrar/ocultar caixa de texto de Outros
    function toggleOther(checkboxId, inputId) {{
        const checkboxEl = document.getElementById(checkboxId);
        const inputEl = document.getElementById(inputId);
        
        if (checkboxEl.checked) {{
            inputEl.style.display = "block";
            inputEl.focus();
        }} else {{
            inputEl.style.display = "none";
            inputEl.value = ""; // Limpa se desmarcar
        }}
    }}

    function enviarWebhook() {{
        const webhookUrl = '{webhook_destino}';
        
        const nomeUsuario = document.getElementById('nome_usuario').value;
        if (!nomeUsuario) {{
            alert("Por favor, preencha o nome do Responsável antes de enviar.");
            return;
        }}

        const setor = document.getElementById('setor').value;
        
        // Determina qual container está ativo
        let containerAtivo;
        if (setor === "Cartório") {{
            containerAtivo = document.getElementById("checklist-cartorio-container");
        }} else {{
            containerAtivo = document.getElementById("checklist-gabinete-container");
        }}
        
        // Coleta os checkboxes marcados dentro do container ativo
        const checks = containerAtivo.querySelectorAll('input[type="checkbox"]:checked');
        let itensMarcados = [];
        
        checks.forEach((chk) => {{
            let val = "- " + chk.value;
            // Verifica se é o checkbox de Outros e pega o texto
            if (chk.id === "c_chk_outros_pre") {{
                const textoOutros = document.getElementById("c_input_outros_pre").value;
                if (textoOutros) val += ": " + textoOutros;
            }}
            if (chk.id === "c_chk_outros_pos") {{
                const textoOutros = document.getElementById("c_input_outros_pos").value;
                if (textoOutros) val += ": " + textoOutros;
            }}
            if (chk.id === "g_chk_outros_pre") {{
                const textoOutros = document.getElementById("g_input_outros_pre").value;
                if (textoOutros) val += ": " + textoOutros;
            }}
            if (chk.id === "g_chk_outros_pos") {{
                const textoOutros = document.getElementById("g_input_outros_pos").value;
                if (textoOutros) val += ": " + textoOutros;
            }}
            itensMarcados.push(val);
        }});
        
        if (itensMarcados.length === 0 && confirm("Nenhuma dúvida foi marcada. Deseja enviar mesmo assim como 'Sem dúvidas'?") === false) {{
            return;
        }}
        
        // --- LÓGICA DE DATA PARA O NOME DO CONSULTOR (WebHook) ---
        // Data da sessão vem como DD/MM/AAAA do Python
        const dataSessaoStr = "{data_sessao_formatada}";
        const parts = dataSessaoStr.split('/');
        // Cria objeto Date (ano, mes-1, dia). Assume formato PT-BR.
        const dataSessaoObj = new Date(parts[2], parts[1] - 1, parts[0]);
        
        // Data de hoje (Zera horas para comparar apenas datas)
        const hoje = new Date();
        hoje.setHours(0,0,0,0);
        
        let consultorResponsavel = "{consultor_nome}";
        
        // Se hoje for maior (depois) que a data da sessão, muda para Cesupe
        if (hoje > dataSessaoObj) {{
            consultorResponsavel = "Cesupe";
        }}
        
        const msgTexto = 
            "*📝 Retorno de Checklist de Sessão*\\n" +
            "*Câmara:* {camara_nome}\\n" +
            "*Data:* {data_sessao_formatada}\\n" +
            "*Responsável (Local):* " + nomeUsuario + "\\n" +
            "*Consultor(a) Técnico(a):* " + consultorResponsavel + "\\n" +
            "*Setor:* " + setor + "\\n\\n" +
            "*Dúvidas/Pontos de Atenção:*" + (itensMarcados.length > 0 ? "\\n" + itensMarcados.join("\\n") : "\\nNenhuma dúvida reportada (Checklist OK).");

        const payload = {{ text: msgTexto }};

        fetch(webhookUrl, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(payload)
        }})
        .then(response => {{
            if (response.ok) {{
                alert('Formulário enviado com sucesso! O(A) consultor(a) já recebeu suas informações.');
            }} else {{
                alert('Falha ao enviar. Tente novamente.');
            }}
        }})
        .catch(error => {{
            console.error('Erro:', error);
            alert('Erro ao enviar (Verifique sua conexão).');
        }});
    }}
    
    window.onload = function() {{
        toggleSetor();
    }};
</script>
</head>
<body>

<div class="container">
    <h1>Acompanhamento de Sessão</h1>
    
    <div class="intro-box">
        <strong>Olá!</strong> Sou o(a) consultor(a) <strong>{consultor_nome}</strong> responsável pelo acompanhamento técnico da sua sessão.<br><br>
        Meu objetivo é garantir que todos os trâmites ocorram com fluidez na data agendada <strong>({data_sessao_formatada})</strong>. Abaixo, apresento um check-list dos procedimentos essenciais.<br><br>
        <strong>Caso tenha dúvida ou insegurança em alguma etapa, marque a caixa correspondente e envie o formulário.</strong> Isso me permitirá atuar preventivamente.
    </div>

    <div class="row-flex">
        <div class="col-flex">
            <label class="field-label">Câmara:</label>
            <div class="static-value">{camara_nome}</div>
        </div>
        <div class="col-flex">
            <label class="field-label">Responsável (Seu Nome):</label>
            <input type="text" id="nome_usuario" placeholder="Digite seu nome">
        </div>
    </div>

    <div class="field-group">
        <label class="field-label">Data da Sessão:</label>
        <div class="static-value">{data_sessao_formatada}</div>
    </div>

    <div class="field-group">
        <label class="field-label">Qual é o seu Setor?</label>
        <select id="setor" onchange="toggleSetor()">
            <option value="Cartório">Cartório (Secretaria)</option>
            <option value="Gabinete">Gabinete</option>
        </select>
    </div>

    <div id="checklist-cartorio-container">
        <div class="checklist-title">Check-list: Cartório (Secretaria)</div>
        <div class="checklist-desc">Responsável pela gestão administrativa, prazos e publicações.</div>
        
        <div class="section-header">I. Pré-Sessão (Fechamento da Pauta até a Abertura da Sessão)</div>
        
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk1" value="Cartório: Criar e Abrir a Sessão">
            <label for="c_chk1"><strong>Criar e Abrir Pauta:</strong> Criar cronograma e abrir a pauta para inclusão de processos.</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk2" value="Cartório: Verificar Manifestações Desembargadores">
            <label for="c_chk2"><strong>Verificar Manifestações:</strong> Certificar-se de que todos os desembargadores manifestaram (Pedidos de vista, Retirados de pauta, Acompanhamentos de voto, Votos de declaração, Votos divergentes)[cite: 8, 9, 10, 11, 12, 13].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk3" value="Cartório: Marcar Destaques Visualizados">
            <label for="c_chk3"><strong>Marcar Destaques Visualizados:</strong> Marcar os destaques dos votos como visualizados (garante que alterações posteriores sejam sinalizadas pelo sistema)[cite: 14].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk4" value="Cartório: Lançar Previsão de Resultado">
            <label for="c_chk4"><strong>Lançar Previsão de Resultado:</strong> Sinalizar a importância de "Lançar a previsão do resultado do julgamento"[cite: 15].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk5" value="Cartório: Verificar Manter Voto">
            <label for="c_chk5"><strong>Verificar Manter Voto:</strong> Conferir se o gabinete marcou a opção de manter o voto para próxima sessão em processos que serão retirados de pauta[cite: 16].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk6" value="Cartório: Fechar e Publicar Pauta">
            <label for="c_chk6"><strong>Fechar e Publicar Pauta:</strong> Fechamento, geração de pauta e lançamento de intimações no DJEN.</label>
        </div>
        <div class="checkbox-item" style="flex-wrap: wrap;">
            <input type="checkbox" id="c_chk_outros_pre" value="Cartório Pré-Sessão: Outros" onclick="toggleOther('c_chk_outros_pre', 'c_input_outros_pre')">
            <label for="c_chk_outros_pre"><strong>Outros na Preparação:</strong> (Descreva abaixo)</label>
            <input type="text" id="c_input_outros_pre" class="other-input" placeholder="Digite sua dúvida...">
        </div>

        <div class="section-header">II. Durante e Pós-Sessão (Encerramento)</div>

        <div class="checkbox-item">
            <input type="checkbox" id="c_chk7" value="Cartório: Abrir e Julgar Processos">
            <label for="c_chk7"><strong>Julgamento (Abrir/Marcar/Salvar):</strong> Acompanhar o Cartório ao "Abrir a sessão" [cite: 19], e para cada processo: Marcar como "em julgamento" [cite: 22], "Salvar resultado" [cite: 23] e Desmarcar[cite: 24].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk8" value="Cartório: Atualizar Resultados e Eventos">
            <label for="c_chk8"><strong>Atualizar Resultados:</strong> Rodar "Atualizar Resultados da Sessão de Julgamento" e Lançar os eventos de resultado[cite: 26].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk9" value="Cartório: Encerrar e Gerar Ata">
            <label for="c_chk9"><strong>Finalização:</strong> "Encerrar da sessão" [cite: 27] e "Gerar ata"[cite: 28].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk10" value="Cartório Pós: Minutas não Assinadas">
            <label for="c_chk10"><strong>Pós-Sessão:</strong> Aplicar o filtro de "Minutas não assinadas" e entrar em contato com os gabinetes para assinatura[cite: 34, 35].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk11" value="Cartório Pós: Retirados de Pauta">
            <label for="c_chk11"><strong>Pós-Sessão:</strong> Verificar se há processos retirados de pauta e se o Gabinete marcou a opção para manter o processo para próxima sessão[cite: 36].</label>
        </div>
        <div class="checkbox-item" style="flex-wrap: wrap;">
            <input type="checkbox" id="c_chk_outros_pos" value="Cartório Pós-Sessão: Outros" onclick="toggleOther('c_chk_outros_pos', 'c_input_outros_pos')">
            <label for="c_chk_outros_pos"><strong>Outros no Encerramento:</strong> (Descreva abaixo)</label>
            <input type="text" id="c_input_outros_pos" class="other-input" placeholder="Digite sua dúvida...">
        </div>
    </div>

    <div id="checklist-gabinete-container" class="hidden">
        <div class="checklist-title">Check-list: Gabinete</div>
        <div class="checklist-desc">Foco na análise processual, votos e disponibilização de documentos.</div>
        
        <div class="section-header">I. Pré-Sessão (Análise e Inclusão)</div>
        
        <div class="checkbox-item">
            <input type="checkbox" id="g_chk1" value="Gabinete: Inclusão e Minutas">
            <label for="g_chk1"><strong>Inclusão/Minutas:</strong> Selecionar processos para inclusão na sessão e criar Relatório/Voto liberando visualização para Colegiado.</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="g_chk2" value="Gabinete: Destaques/Vistas">
            <label for="g_chk2"><strong>Destaques/Vistas:</strong> Analisar divergências/vistas e inserir destaques próprios.</label>
        </div>
        <div class="checkbox-item" style="flex-wrap: wrap;">
            <input type="checkbox" id="g_chk_outros_pre" value="Gabinete Pré-Sessão: Outros" onclick="toggleOther('g_chk_outros_pre', 'g_input_outros_pre')">
            <label for="g_chk_outros_pre"><strong>Outros na Preparação:</strong> (Descreva abaixo)</label>
            <input type="text" id="g_input_outros_pre" class="other-input" placeholder="Digite sua dúvida...">
        </div>

        <div class="section-header">II. Pós-Sessão (Formalização)</div>

        <div class="checkbox-item">
            <input type="checkbox" id="g_chk5" value="Gabinete: Filtro e Assinatura de Minutas">
            <label for="g_chk5"><strong>Assinatura:</strong> Aplicar o "Filtro minutas para assinar" [cite: 39] e realizar a assinatura do Relatório/Voto/Acórdão no status "Para Assinar"[cite: 35].</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="g_chk6" value="Gabinete: Juntada e Evento Final">
            <label for="g_chk6"><strong>Movimentação Final:</strong> Juntada de relatório/voto/acórdão [cite: 40] e Lançamento do Evento “Remetidos os votos com acórdão”[cite: 41].</label>
        </div>
        <div class="checkbox-item" style="flex-wrap: wrap;">
            <input type="checkbox" id="g_chk_outros_pos" value="Gabinete Pós-Sessão: Outros" onclick="toggleOther('g_chk_outros_pos', 'g_input_outros_pos')">
            <label for="g_chk_outros_pos"><strong>Outros na Formalização:</strong> (Descreva abaixo)</label>
            <input type="text" id="g_input_outros_pos" class="other-input" placeholder="Digite sua dúvida...">
        </div>
    </div>

    <button class="btn-submit" onclick="enviarWebhook()">Enviar Dúvidas ao(à) Consultor(a)</button>
</div>

</body>
</html>
    """
    return html_template

# (As demais funções, incluindo as de envio de registro, permanecem inalteradas)

# --- Callbacks de Formulário de Registro (MODIFICADA) ---

# ... (handle_atividade_submission, handle_presencial_submission, set_chamado_step, handle_chamado_submission permanecem inalteradas)

def handle_sessao_submission():
    """Callback: Envio do Registro de Sessão."""
    print("CALLBACK: handle_sessao_submission")
    
    consultor = st.session_state.consultor_selectbox
    # Pega o texto final editado pelo usuário no text_area
    texto_final = st.session_state.get("sessao_msg_preview", "")
    
    # Dados para gerar o HTML
    camara = st.session_state.get('sessao_camara_select', 'Não informada')
    data_obj = st.session_state.get('sessao_data_input')
    data_formatada = data_obj.strftime("%d/%m/%Y") if data_obj else 'Não informada'
    data_nome_arquivo = data_obj.strftime("%d-%m-%Y") if data_obj else 'SemData'
    
    # IMPORTANTE: A mensagem enviada é o texto_final (que já está no novo padrão)
    success = send_sessao_to_chat(consultor, texto_final)
    
    if success:
        st.session_state.last_reg_status = "success_sessao"
        st.session_state.sessao_msg_preview = "" # Limpa a prévia após envio
        
        # GERA O HTML E ARMAZENA NO SESSION STATE PARA DOWNLOAD
        html_content = gerar_html_checklist(consultor, camara, data_formatada)
        st.session_state.html_content_cache = html_content
        st.session_state.html_download_ready = True
        st.session_state.html_filename = f"Checklist_{data_nome_arquivo}.html" # Nome do arquivo com data
        
        st.session_state.registro_tipo_selecao = None # Fecha o formulário
    else:
        st.session_state.last_reg_status = "error_sessao"
        st.session_state.html_download_ready = False


# --- Formulário "Registro de Sessão" (MODIFICADA: Lógica de atualização de texto) ---

# ... (O restante da seção de callbacks, incluindo set_chamado_step e handle_chamado_submission, permanece inalterado)

# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

# ... (Toda a execução principal até a lógica de Registro de Sessão permanece inalterada)

# No bloco de Registro de Sessão (dentro da Seção 4):

# ...

# --- Formulário "Registro de Sessão" ---
elif st.session_state.registro_tipo_selecao == "Registro de Sessão":
    st.subheader("Registro de Sessão")
    
    # Função para atualizar o texto da sessão automaticamente (Reatividade)
    def atualizar_texto_sessao():
        data_input = st.session_state.get('sessao_data_input')
        camara_input = st.session_state.get('sessao_camara_select')
        consultor_atual = st.session_state.consultor_selectbox
        
        if data_input and camara_input:
            nome_consultor_txt = consultor_atual if consultor_atual and consultor_atual != "Selecione um nome" else "[NOME DO(A) CONSULTOR(A)]"
            data_formatada = data_input.strftime("%d/%m/%Y")
            
            # Pega o e-mail correspondente do dicionário
            email_setor = CAMARAS_DICT.get(camara_input, "")
            
            # NOVO CORPO DA MENSAGEM
            texto_gerado = (
                f"Prezada equipe do {camara_input},\n\n"
                f"Meu nome é {nome_consultor_txt}, sou assistente de processos judiciais da CESUPE/TJMG e serei o(a) responsável pelo acompanhamento técnico da sessão de julgamento agendada para o dia {data_formatada}.\n\n"
                "Com o objetivo de agilizar o atendimento e a verificação de eventuais demandas, encaminharei um formulário em HTML para preenchimento de algumas informações prévias. As respostas retornarão diretamente para mim, permitindo a análise antecipada da situação e, sempre que possível, a definição prévia da orientação ou solução a ser adotada. O preenchimento não é obrigatório, mas contribuirá para tornar o suporte mais eficaz.\n\n"
                "Ressalto que continuamos disponíveis para sanar quaisquer dúvidas por meio do nosso suporte. Caso eu esteja indisponível no momento do contato, retornarei o mais breve possível.\n\n"
                "Após a realização da sessão, o suporte técnico voltará a ser prestado de forma rotineira pelo nosso setor. Havendo dúvidas ou necessidade de suporte, entre em contato conosco pelo telefone **3232-2640**.\n\n"
                "Permaneço à disposição e agradeço a colaboração.\n\n"
                "Atenciosamente,\n"
                f"{nome_consultor_txt}\n"
                "Assistente de Processos Judiciais – CESUPE/TJMG\n\n"
                f"Email do setor: {email_setor}"
            )
            st.session_state['sessao_msg_preview'] = texto_gerado
        else:
            st.session_state['sessao_msg_preview'] = ""

    col_sessao_1, col_sessao_2 = st.columns(2)
    with col_sessao_1:
        # Adicionado on_change para disparar atualização imediata
        st.date_input("Data da Sessão:", format="DD/MM/YYYY", key='sessao_data_input', on_change=atualizar_texto_sessao)
    with col_sessao_2:
        # Adicionado on_change para disparar atualização imediata
        st.selectbox("Selecione a Câmara:", CAMARAS_OPCOES, index=None, key='sessao_camara_select', on_change=atualizar_texto_sessao)
        
    st.markdown("**Prévia da Mensagem (Editável):**")
    # O valor agora é lido diretamente do estado 'sessao_msg_preview'
    st.text_area(
        "Mensagem:", 
        key="sessao_msg_preview",
        height=450, 
        label_visibility="collapsed"
    )
    
    st.button(
        "Enviar Mensagem de Sessão",
        type="primary",
        use_container_width=True,
        on_click=handle_sessao_submission
    )
