# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json
import base64
import io
from supabase import create_client
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Importações locais
from repository import load_state_from_db, save_state_to_db
from utils import (get_brazil_time, get_secret, send_to_chat, get_img_as_base64)

# ... [MANTENHA AS CONFIGURAÇÕES E LISTAS EXISTENTES AQUI (CONSULTORES, CAMARAS, ETC)] ...
# (Para economizar espaço, estou resumindo as listas, mas mantenha as suas originais)
CONSULTORES = sorted([
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
    "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
    "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
])
# ... (Mantenha o resto das constantes igual) ...
# REPLICAR O RESTO DAS SUAS CONSTANTES AQUI
REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]
CAMARAS_DICT = {"Cartório da 1ª Câmara Cível": "caciv1@tjmg.jus.br", "Cartório da 2ª Câmara Cível": "caciv2@tjmg.jus.br", "Cartório da 3ª Câmara Cível": "caciv3@tjmg.jus.br", "Cartório da 4ª Câmara Cível": "caciv4@tjmg.jus.br", "Cartório da 5ª Câmara Cível": "caciv5@tjmg.jus.br", "Cartório da 6ª Câmara Cível": "caciv6@tjmg.jus.br", "Cartório da 7ª Câmara Cível": "caciv7@tjmg.jus.br", "Cartório da 8ª Câmara Cível": "caciv8@tjmg.jus.br", "Cartório da 9ª Câmara Cível": "caciv9@tjmg.jus.br", "Cartório da 10ª Câmara Cível": "caciv10@tjmg.jus.br", "Cartório da 11ª Câmara Cível": "caciv11@tjmg.jus.br", "Cartório da 12ª Câmara Cível": "caciv12@tjmg.jus.br", "Cartório da 13ª Câmara Cível": "caciv13@tjmg.jus.br", "Cartório da 14ª Câmara Cível": "caciv14@tjmg.jus.br", "Cartório da 15ª Câmara Cível": "caciv15@tjmg.jus.br", "Cartório da 16ª Câmara Cível": "caciv16@tjmg.jus.br", "Cartório da 17ª Câmara Cível": "caciv17@tjmg.jus.br", "Cartório da 18ª Câmara Cível": "caciv18@tjmg.jus.br", "Cartório da 19ª Câmara Cível": "caciv19@tjmg.jus.br", "Cartório da 20ª Câmara Cível": "caciv20@tjmg.jus.br", "Cartório da 21ª Câmara Cível": "caciv21@tjmg.jus.br"}
CAMARAS_OPCOES = sorted(list(CAMARAS_DICT.keys()))
OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]
OPCOES_PROJETOS = ["Soma", "Treinamentos Eproc", "Manuais Eproc", "Cartilhas Gabinetes", "Notebook Lm", "Inteligência artifical cartórios"]
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
PUG2026_FILENAME = "pug2026.png"
GOOGLE_CHAT_WEBHOOK_BACKUP = get_secret("chat", "backup")
CHAT_WEBHOOK_BASTAO = get_secret("chat", "bastao")
GOOGLE_CHAT_WEBHOOK_REGISTRO = get_secret("chat", "registro")
SHEETS_WEBHOOK_URL = get_secret("sheets", "url")

# --- CONEXÃO ---
def get_supabase():
    try: return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except: return None

# --- BANCO ---
def verificar_duplicidade_certidao(tipo, n_processo=None, data_evento=None, hora_periodo=None):
    sb = get_supabase()
    if not sb: return False
    try:
        query = sb.table("certidoes_registro").select("*").eq("tipo", tipo)
        if tipo in ['Física', 'Eletrônica'] and n_processo:
            proc_limpo = str(n_processo).strip().rstrip('.')
            response = query.ilike("n_processo", f"%{proc_limpo}%").execute()
            return len(response.data) > 0
        elif tipo == 'Geral' and data_evento:
            data_str = data_evento.isoformat() if hasattr(data_evento, 'isoformat') else str(data_evento)
            query = query.eq("data_evento", data_str)
            if hora_periodo: query = query.eq("hora_periodo", hora_periodo)
            response = query.execute()
            return len(response.data) > 0
    except: return False
    return False

def salvar_certidao_db(dados):
    sb = get_supabase()
    if not sb: return False
    try:
        sb.table("certidoes_registro").insert(dados).execute()
        return True
    except: raise

# --- GERADOR DE WORD ATUALIZADO ---
def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo):
    try:
        doc = Document()
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Arial'
        font.size = Pt(12)

        # Cabeçalho
        head = doc.add_paragraph()
        head.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = head.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        run.bold = True
        head.add_run("Rua Ouro Preto, Nº 1564 - Bairro Santo Agostinho - CEP 30170-041\nBelo Horizonte - MG - www.tjmg.jus.br\nAndar: 3º e 4º PV")
        
        doc.add_paragraph("\n")
        
        # Título
        # Usa um número fictício para Parecer, já que não temos contador automático sequencial no Word
        # No futuro poderia pegar do ID do banco se quisesse
        p_num = doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2025.")
        p_num.runs[0].bold = True
        
        # Assunto
        doc.add_paragraph(f"Assunto: Notifica erro no \"JPe - 2ª Instância\" ao peticionar.")
        
        # Data Extenso
        data_atual = datetime.now().strftime("%d de %B de %Y")
        doc.add_paragraph(f"\nExmo(a). Senhor(a) Relator(a),\n\nBelo Horizonte, {data_atual}")
        
        # Corpo
        corpo = doc.add_paragraph()
        corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        corpo.add_run(f"Informamos que na data de {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}.\n\n")
        corpo.add_run("O Chamado foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
        
        # Lógica Específica Física/Eletrônica
        if tipo == 'Física':
            corpo.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.\n\n")
        else:
            corpo.add_run("Informamos a indisponibilidade para fins de restituição de prazo ou providências que V.Exa julgar necessárias, nos termos da legislação vigente.\n\n")
            
        corpo.add_run("Colocamo-nos à disposição para outras informações que se fizerem necessárias.")
        
        doc.add_paragraph("\n\nRespeitosamente,")
        
        # Assinatura (Simulada conforme solicitado)
        doc.add_paragraph("\n\n___________________________________\nWaner Andrade Silva\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD\nDiretoria Executiva de Tecnologia da Informação e Comunicação - DIRTEC")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        print(e)
        return None

# ... [MANTENHA TODAS AS OUTRAS FUNÇÕES: save_state, load_logs, etc. IGUAIS AO ANTERIOR] ...
# (Copie do código anterior as funções: save_state, load_logs, format_time_duration, log_status_change, handlers, fila blindada, init_session_state, etc)

# ... [COLE AQUI O RESTANTE DO CÓDIGO DO APP.PY QUE MANDEI NA RESPOSTA ANTERIOR] ...
# ... [ATÉ CHEGAR NA PARTE DO VIEW: CERTIDÃO, ONDE MUDEI O BOTÃO] ...

# ================================
# VIEW: CERTIDÃO (FINAL)
# ================================
# ... (dentro do elif st.session_state.active_view == "certidao":) ...
            
            # ... (inputs de data, tipo, processo, etc) ...

            col_act1, col_act2 = st.columns([1, 1])
            
            with col_act1:
                if st.button("📄 Gerar Word (Sem Salvar)", use_container_width=True):
                    if c_consultor == "Selecione um nome": st.error("Selecione seu nome.")
                    else:
                        num = c_processo if c_processo else c_chamado
                        docx_file = gerar_docx_certidao_internal(tipo_certidao, num, c_data.strftime("%d/%m/%Y"), c_consultor, c_motivo)
                        if docx_file:
                            st.download_button("⬇️ Baixar DOCX", docx_file, file_name="certidao.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
            with col_act2:
                if st.button("💾 Salvar Registro", type="primary", use_container_width=True):
                    # ... (validações de erro_msg) ...
                    # ...
                    # Dentro do try/except do salvar:
                        try:
                            ja_existe = False
                            if tipo_certidao == "Geral":
                                ja_existe = verificar_duplicidade_certidao("Geral", data_evento=c_data, hora_periodo=c_hora)
                            else:
                                ja_existe = verificar_duplicidade_certidao(tipo_certidao, n_processo=c_processo)
                            
                            if ja_existe:
                                st.warning("⚠️ **Atenção: Já existe registro!**")
                                # REMOVIDO O EXPANDED=TRUE QUE DAVA ERRO
                                with st.popover("🚨 LER AVISO"):
                                    st.error(f"Já existe uma certidão **{tipo_certidao}** registrada para estes dados.")
                                    st.write("Não é necessário registrar novamente.")
                                    st.markdown("**Dúvidas? Falar com Matheus ou Gilberto.**")
                            else:
                                # ... (lógica de salvar) ...
