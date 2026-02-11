# -*- coding: utf-8 -*-
"""
dashboard.py — Central Unificada de Bastão
Versão consolidada com os patches descritos em Patches.txt / Apply patches.

Objetivos principais:
- Sem streamlit_autorefresh (Patch 2): atualização via watcher (fragment).
- Cache TTL reduzido (Patch 3): load_state_from_db ttl=3.
- Browser ID "lazy" (Patch 4): só tenta JS se lib existir.
- Watcher com deserialização + comparação segura (Patch 5).
- CSS botões compactos ❌ / ⬆️ (Patch 6 + Patch 8).
- Status editável apenas para o usuário logado (Patch 7), usando OPCOES_STATUS_FILA (Patch 9).
- Função handle_chamado_submission existente (Patch 10).
- Função handle_sugestao_submission corrigida (Patch 11).

Obs.: Este arquivo foi gerado para ser auto-suficiente e manter as funcionalidades centrais do controle do bastão.
Se seu projeto já tiver utils.py, ele será usado; caso contrário, há fallbacks internos.
"""
from __future__ import annotations

import base64
import gc
import io
import json
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st

# -------------------------
# Dependências opcionais
# -------------------------
try:
    from streamlit_javascript import st_javascript  # type: ignore
except Exception:
    st_javascript = None  # type: ignore

# streamlit_autorefresh removido — watcher é suficiente (Patch 2)
st_autorefresh = None  # noqa: F401


# -------------------------
# Utils (preferir do projeto)
# -------------------------
def _fallback_get_brazil_time() -> datetime:
    # timezone Brasil (SP). Se pytz não existir, usa localtime.
    try:
        import pytz  # type: ignore

        return datetime.now(pytz.timezone("America/Sao_Paulo"))
    except Exception:
        return datetime.now()


def _fallback_get_secret(section: str, key: str, default: str = "") -> str:
    try:
        sec = st.secrets.get(section, {})
        if isinstance(sec, dict):
            return str(sec.get(key, default) or default)
    except Exception:
        pass
    return default


def _fallback_send_to_chat(_: str) -> bool:
    # placeholder — mantém compatibilidade
    return True


try:
    # no seu projeto, estes devem existir
    from utils import get_brazil_time, get_secret, send_to_chat  # type: ignore
except Exception:
    get_brazil_time = _fallback_get_brazil_time  # type: ignore
    get_secret = _fallback_get_secret  # type: ignore
    send_to_chat = _fallback_send_to_chat  # type: ignore


# -------------------------
# Supabase
# -------------------------
try:
    from supabase import create_client  # type: ignore
except Exception:
    create_client = None  # type: ignore


# -------------------------
# Constantes e listas
# -------------------------
DB_TABLE_APP_STATE = "app_state"

# IDs base (compatibilidade)
LOGMEIN_DB_ID = 1  # compartilhado

# Tipos de registro (para webhooks)
H_EXTRAS = "HORAS_EXTRAS"
ATENDIMENTOS = "ATENDIMENTOS"
CHAMADOS = "CHAMADOS"
ERRO_NOVIDADE = "ERRO_NOVIDADE"
SUGESTAO = "SUGESTAO"

# Listas (podem ser ajustadas pelo seu projeto)
REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]

OPCOES_ATIVIDADES_STATUS = [
    "HP",
    "E-mail",
    "WhatsApp Plantão",
    "Homologação",
    "Redação Documentos",
    "Outros",
]

# Patch 9 — opções usadas no patch 7 (Status só do logado)
OPCOES_STATUS_FILA = [
    "Aguardando",
    "Atividade",
    "Projeto",
    "Treinamento",
    "Reunião",
    "Sessão",
    "Atendimento Presencial",
    "Saída rápida",
    "Almoço",
]

# Indicadores rápidos (📞 ☕)
DEFAULT_QUICK_INDIC = {"telefone": False, "cafe": False}

# -------------------------
# Helpers
# -------------------------
def _normalize_nome(txt: str) -> str:
    if not isinstance(txt, str):
        return ""
    txt = "".join(ch for ch in unicodedata.normalize("NFKD", txt) if not unicodedata.combining(ch))
    txt = re.sub(r"\s+", " ", txt).strip().lower()
    return txt


def clean_data_for_db(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: clean_data_for_db(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_data_for_db(i) for i in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return obj.total_seconds()
    return obj


def _parse_dt(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, (int, float)):
        # epoch seconds
        try:
            return datetime.fromtimestamp(val)
        except Exception:
            return None
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
    return None


def _parse_td(val: Any) -> Optional[timedelta]:
    if val is None:
        return None
    if isinstance(val, timedelta):
        return val
    if isinstance(val, (int, float)):
        try:
            return timedelta(seconds=float(val))
        except Exception:
            return None
    return None


def format_time_duration(duration: Any) -> str:
    td = duration if isinstance(duration, timedelta) else _parse_td(duration)
    if not td:
        return "--:--:--"
    s = int(td.total_seconds())
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def post_n8n(url: str, payload: Dict[str, Any]) -> bool:
    if not url:
        return False
    try:
        resp = requests.post(url, json=payload, timeout=12)
        if getattr(resp, "status_code", 200) >= 400:
            return False
        return True
    except requests.exceptions.Timeout:
        return False
    except Exception:
        return False


# -------------------------
# Supabase cached
# -------------------------
@st.cache_resource(ttl=3600)
def get_supabase():
    if create_client is None:
        return None
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception:
        st.cache_resource.clear()
        return None


@st.cache_data(ttl=3, show_spinner=False)  # Patch 3
def load_state_from_db(app_id: int) -> Dict[str, Any]:
    sb = get_supabase()
    if not sb:
        return {}
    try:
        res = sb.table(DB_TABLE_APP_STATE).select("data").eq("id", app_id).execute()
        if res.data and len(res.data) > 0:
            data = res.data[0].get("data", {}) or {}
            if isinstance(data, dict):
                return data
        return {}
    except Exception:
        return {}


def save_state_to_db(app_id: int, state_data: Dict[str, Any]) -> bool:
    sb = get_supabase()
    if not sb:
        return False
    try:
        sanitized_data = clean_data_for_db(state_data)
        sb.table(DB_TABLE_APP_STATE).upsert({"id": app_id, "data": sanitized_data}).execute()
        st.session_state["_last_save_time"] = time.time()
        st.session_state["_toast_msg"] = "✅ Registro salvo."
        return True
    except Exception as e:
        st.session_state["_toast_msg"] = f"🔥 ERRO ao salvar no banco: {e}"
        return False


# -------------------------
# Device / IP
# -------------------------
def get_browser_id() -> str:
    # Patch 4: lazy — só tenta se a lib existir
    if st_javascript is None:
        return "no_js_lib"
    js_code = r"""
    (function() {
      let id = localStorage.getItem("device_id");
      if (!id) {
        id = "id_" + Math.random().toString(36).substr(2, 9);
        localStorage.setItem("device_id", id);
      }
      return id;
    })();
    """
    try:
        return str(st_javascript(js_code, key="browser_id_tag") or "unknown_device")
    except Exception:
        return "unknown_device"


def get_remote_ip() -> str:
    # Streamlit Cloud: pode falhar — fallback seguro
    try:
        from streamlit.web.server.websocket_headers import ClientWebSocketRequest  # type: ignore

        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and ctx.session_id:
            session_info = st.runtime.get_instance().get_client(ctx.session_id)
            if session_info:
                request = session_info.request
                if isinstance(request, ClientWebSocketRequest):
                    if "X-Forwarded-For" in request.headers:
                        return request.headers["X-Forwarded-For"].split(",")[0]
                    return request.remote_ip
    except Exception:
        pass
    return "Unknown"


# -------------------------
# Estado (fila / bastão)
# -------------------------
def get_bastao_holder_atual() -> Optional[str]:
    return next(
        (c for c, s in (st.session_state.get("status_texto") or {}).items() if isinstance(s, str) and "Bastão" in s),
        None,
    )


def find_next_holder_index(current_index: int, queue: List[str], skips: Dict[str, bool]) -> int:
    if not queue:
        return -1
    n = len(queue)
    start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        if not skips.get(queue[idx], False):
            return idx
    if n > 1:
        proximo_imediato_idx = (current_index + 1) % n
        nome_escolhido = queue[proximo_imediato_idx]
        st.session_state["skip_flags"][nome_escolhido] = False
        return proximo_imediato_idx
    return -1


def get_proximos_bastao(holder: Optional[str], n: int = 2) -> List[str]:
    queue = st.session_state.get("bastao_queue") or []
    skips = st.session_state.get("skip_flags") or {}
    if not queue:
        return []
    if not holder or holder not in queue:
        holder = queue[0]
    idx = queue.index(holder)
    proximos: List[str] = []
    cursor = idx
    while len(proximos) < n:
        nxt = find_next_holder_index(cursor, queue, skips)
        if nxt == -1:
            break
        nxt_name = queue[nxt]
        if nxt_name == holder or nxt_name in proximos:
            break
        proximos.append(nxt_name)
        cursor = nxt
    return proximos


def log_status_change(consultor: str, old_status: str, new_status: str, duration: timedelta) -> None:
    now_br = get_brazil_time()
    logs = st.session_state.get("daily_logs")
    if not isinstance(logs, list):
        logs = []
    logs.append(
        {
            "timestamp": now_br.isoformat(),
            "consultor": consultor,
            "old_status": old_status or "Fila",
            "new_status": new_status or "Fila",
            "duration_seconds": int(duration.total_seconds() if isinstance(duration, timedelta) else 0),
            "ip": st.session_state.get("device_id_val", "unknown"),
        }
    )
    if len(logs) > 150:
        logs[:] = logs[-150:]
    st.session_state["daily_logs"] = logs
    st.session_state["current_status_starts"][consultor] = now_br


def reset_day_state() -> None:
    consultores = st.session_state.get("CONSULTORES_RUNTIME") or []
    st.session_state["bastao_queue"] = []
    st.session_state["status_texto"] = {n: "Indisponível" for n in consultores}
    st.session_state["daily_logs"] = []
    st.session_state["report_last_run_date"] = get_brazil_time()


def ensure_daily_reset() -> None:
    # Patch 3/robustez: nunca zera por data corrompida
    now_br = get_brazil_time()
    last_run = st.session_state.get("report_last_run_date")

    if isinstance(last_run, str):
        try:
            last_run_dt = datetime.fromisoformat(last_run).date()
        except Exception:
            last_run_dt = now_br.date()
    elif isinstance(last_run, datetime):
        last_run_dt = last_run.date()
    elif isinstance(last_run, date):
        last_run_dt = last_run
    else:
        last_run_dt = now_br.date()

    if now_br.date() > last_run_dt:
        # Aqui você poderia enviar relatórios webhooks (mantido simples)
        reset_day_state()
        st.session_state["report_last_run_date"] = now_br
        save_state()


def check_and_assume_baton(forced_successor: Optional[str] = None, immune_consultant: Optional[str] = None) -> bool:
    queue: List[str] = st.session_state.get("bastao_queue") or []
    skips: Dict[str, bool] = st.session_state.get("skip_flags") or {}
    status_texto: Dict[str, str] = st.session_state.get("status_texto") or {}
    consultores: List[str] = st.session_state.get("CONSULTORES_RUNTIME") or []

    current_holder = get_bastao_holder_atual()
    is_valid = bool(current_holder and current_holder in queue)
    target = forced_successor or (current_holder if is_valid else None)

    if not target:
        curr_idx = queue.index(current_holder) if (current_holder and current_holder in queue) else -1
        idx = find_next_holder_index(curr_idx, queue, skips)
        target = queue[idx] if idx != -1 else None

    changed = False
    now = get_brazil_time()

    # garante exclusividade do bastão
    for c in consultores:
        if c == immune_consultant:
            continue
        if c != target and "Bastão" in (status_texto.get(c) or ""):
            old = status_texto.get(c) or ""
            log_status_change(c, old, "Indisponível", now - st.session_state["current_status_starts"].get(c, now))
            status_texto[c] = "Indisponível"
            changed = True

    if target:
        curr_s = status_texto.get(target) or ""
        if "Bastão" not in curr_s:
            old_s = curr_s
            new_s = f"Bastão  {old_s}".strip() if old_s and old_s != "Indisponível" else "Bastão"
            log_status_change(target, old_s, new_s, now - st.session_state["current_status_starts"].get(target, now))
            status_texto[target] = new_s
            st.session_state["bastao_start_time"] = now
            st.session_state["skip_flags"][target] = False
            st.session_state["play_sound"] = True
            notify_bastao_giro(reason="assume_bastao", actor=target)
            changed = True
    else:
        if current_holder and current_holder != immune_consultant:
            old = status_texto.get(current_holder) or ""
            log_status_change(current_holder, old, "Indisponível", now - st.session_state["current_status_starts"].get(current_holder, now))
            status_texto[current_holder] = "Indisponível"
            changed = True

    st.session_state["status_texto"] = status_texto
    if changed:
        save_state()
    return changed


def update_status(novo_status: str, marcar_indisponivel: bool = False, manter_fila_atual: bool = False) -> None:
    selected = st.session_state.get("consultor_selectbox")
    if not selected or selected == "Selecione um nome":
        st.warning("Selecione um(a) consultor(a).")
        return

    ensure_daily_reset()
    now_br = get_brazil_time()
    current = st.session_state["status_texto"].get(selected, "") or ""
    forced_successor: Optional[str] = None
    current_holder = get_bastao_holder_atual()

    # guarda estado anterior se entrando em almoço
    if novo_status == "Almoço":
        st.session_state["previous_states"][selected] = {
            "status": current,
            "in_queue": selected in st.session_state["bastao_queue"],
        }

    if marcar_indisponivel or (novo_status == "Indisponível"):
        st.session_state["skip_flags"][selected] = True
        if selected in st.session_state["bastao_queue"]:
            if selected == current_holder:
                idx = st.session_state["bastao_queue"].index(selected)
                nxt = find_next_holder_index(idx, st.session_state["bastao_queue"], st.session_state["skip_flags"])
                if nxt != -1:
                    forced_successor = st.session_state["bastao_queue"][nxt]
            st.session_state["bastao_queue"].remove(selected)

    elif manter_fila_atual:
        if selected not in st.session_state["bastao_queue"]:
            st.session_state["bastao_queue"].append(selected)
        st.session_state["skip_flags"][selected] = False

    # define status final
    final_status = (novo_status or "").strip()
    if selected == current_holder and selected in st.session_state["bastao_queue"]:
        final_status = ("Bastão  " + final_status).strip() if final_status else "Bastão"
    if not final_status and (selected not in st.session_state["bastao_queue"]):
        final_status = "Indisponível"

    log_status_change(selected, current, final_status, now_br - st.session_state["current_status_starts"].get(selected, now_br))
    st.session_state["status_texto"][selected] = final_status

    check_and_assume_baton(forced_successor=forced_successor)
    save_state()


def toggle_queue(consultor: str) -> None:
    ensure_daily_reset()
    if consultor in st.session_state["bastao_queue"]:
        current_holder = get_bastao_holder_atual()
        forced_successor: Optional[str] = None
        if consultor == current_holder:
            idx = st.session_state["bastao_queue"].index(consultor)
            nxt = find_next_holder_index(idx, st.session_state["bastao_queue"], st.session_state["skip_flags"])
            if nxt != -1:
                forced_successor = st.session_state["bastao_queue"][nxt]
        st.session_state["bastao_queue"].remove(consultor)
        st.session_state["status_texto"][consultor] = "Indisponível"
        check_and_assume_baton(forced_successor=forced_successor)
    else:
        st.session_state["bastao_queue"].append(consultor)
        st.session_state["skip_flags"][consultor] = False
        if consultor in st.session_state["priority_return_queue"]:
            st.session_state["priority_return_queue"].remove(consultor)
        st.session_state["status_texto"][consultor] = ""
        check_and_assume_baton()
        notify_bastao_giro(reason="enter_bastao", actor=consultor)
    save_state()


def rotate_bastao() -> None:
    ensure_daily_reset()
    selected = st.session_state.get("consultor_selectbox")
    if not selected or selected == "Selecione um nome":
        st.warning("Selecione um(a) consultor(a).")
        return

    queue: List[str] = st.session_state.get("bastao_queue") or []
    skips: Dict[str, bool] = st.session_state.get("skip_flags") or {}
    current_holder = get_bastao_holder_atual()

    if selected != current_holder:
        st.error(f"⚠️ Apenas quem está com o bastão ({current_holder}) pode passá-lo!")
        return

    if current_holder not in queue:
        check_and_assume_baton()
        return

    current_index = queue.index(current_holder)
    next_idx = find_next_holder_index(current_index, queue, skips)
    if next_idx == -1 and len(queue) > 1:
        next_idx = (current_index + 1) % len(queue)

    if next_idx == -1:
        st.warning("Ninguém elegível.")
        check_and_assume_baton()
        return

    next_holder = queue[next_idx]
    now_br = get_brazil_time()

    # limpa bastão do atual
    old_h_status = st.session_state["status_texto"].get(current_holder, "") or ""
    new_h_status = old_h_status.replace("Bastão  ", "").replace("Bastão", "").strip()
    log_status_change(current_holder, old_h_status, new_h_status, now_br - (st.session_state.get("bastao_start_time") or now_br))
    st.session_state["status_texto"][current_holder] = new_h_status

    # seta bastão no próximo
    old_n_status = st.session_state["status_texto"].get(next_holder, "") or ""
    new_n_status = f"Bastão  {old_n_status}".strip() if old_n_status else "Bastão"
    log_status_change(next_holder, old_n_status, new_n_status, timedelta(0))
    st.session_state["status_texto"][next_holder] = new_n_status
    st.session_state["bastao_start_time"] = now_br
    st.session_state["bastao_counts"][current_holder] = st.session_state["bastao_counts"].get(current_holder, 0) + 1
    st.session_state["play_sound"] = True

    notify_bastao_giro(reason="rotate", actor=current_holder)
    save_state()


# -------------------------
# Indicadores rápidos 📞 ☕
# -------------------------
def _get_quick_indic(nome: str) -> Dict[str, bool]:
    qi = st.session_state.get("quick_indicators")
    if not isinstance(qi, dict):
        qi = {}
        st.session_state["quick_indicators"] = qi
    return dict(qi.get(nome, DEFAULT_QUICK_INDIC))


def _set_quick_indic(nome: str, telefone: Optional[bool] = None, cafe: Optional[bool] = None) -> None:
    qi = st.session_state.get("quick_indicators")
    if not isinstance(qi, dict):
        qi = {}
        st.session_state["quick_indicators"] = qi
    cur = _get_quick_indic(nome)
    if telefone is not None:
        cur["telefone"] = bool(telefone)
        if telefone:
            cur["cafe"] = False
    if cafe is not None:
        cur["cafe"] = bool(cafe)
        if cafe:
            cur["telefone"] = False
    qi[nome] = cur
    st.session_state["quick_indicators"] = qi
    save_state()


def _icons_telefone_cafe(indic: Dict[str, bool]) -> str:
    parts: List[str] = []
    if indic.get("telefone"):
        parts.append("📞")
    if indic.get("cafe"):
        parts.append("☕")
    return (" " + " ".join(parts)) if parts else ""


def toggle_quick_telefone() -> None:
    nome = st.session_state.get("consultor_selectbox")
    if not nome or nome == "Selecione um nome":
        st.warning("Selecione um(a) consultor(a).")
        return
    cur = _get_quick_indic(nome)
    _set_quick_indic(nome, telefone=not cur.get("telefone", False))


def toggle_quick_cafe() -> None:
    nome = st.session_state.get("consultor_selectbox")
    if not nome or nome == "Selecione um nome":
        st.warning("Selecione um(a) consultor(a).")
        return
    cur = _get_quick_indic(nome)
    _set_quick_indic(nome, cafe=not cur.get("cafe", False))


# -------------------------
# Webhooks — bastão / registros
# -------------------------
N8N_WEBHOOK_BASTAO_GIRO = get_secret("n8n", "bastao_giro") or get_secret("chat", "bastao_eq1") or get_secret("chat", "bastao_eq2")
N8N_WEBHOOK_REGISTROS = get_secret("n8n", "registros") or get_secret("chat", "registro")


def notify_bastao_giro(reason: str = "update", actor: Optional[str] = None) -> bool:
    try:
        holder = get_bastao_holder_atual()
        if not holder and st.session_state.get("bastao_queue"):
            holder = st.session_state["bastao_queue"][0]

        lista_proximos = get_proximos_bastao(holder, n=2)
        txt_proximos = ", ".join(lista_proximos) if lista_proximos else "Ninguém"
        nome_equipe = st.session_state.get("team_name", "Equipe")

        msg_final = f"🔄 Troca de Bastão - {nome_equipe}\n\n👤 Agora: {holder}\n🔜 Próximos: {txt_proximos}"

        payload = {
            "evento": "bastao_giro",
            "motivo": reason,
            "timestamp": get_brazil_time().isoformat(),
            "team_id": st.session_state.get("team_id"),
            "team_name": nome_equipe,
            "actor": actor,
            "com_bastao_agora": holder,
            "proximos": lista_proximos,
            "tamanho_fila": len(st.session_state.get("bastao_queue") or []),
            "message": msg_final,
        }
        return post_n8n(N8N_WEBHOOK_BASTAO_GIRO, payload)
    except Exception:
        return False


def notify_registro_ferramenta(tipo: str, actor: str, dados: Optional[Dict[str, Any]] = None, mensagem: Optional[str] = None) -> bool:
    # Patch 5/7: campo message sempre preenchido
    if not mensagem:
        mensagem = f"Novo registro {tipo} por {actor}"

    payload = {
        "evento": "registro_ferramenta",
        "tipo": tipo,
        "timestamp": get_brazil_time().isoformat(),
        "team_id": st.session_state.get("team_id"),
        "team_name": st.session_state.get("team_name"),
        "actor": actor,
        "dados": dados or {},
        "message": mensagem,
    }
    return post_n8n(N8N_WEBHOOK_REGISTROS, payload)


def send_horas_extras_to_chat(consultor: str, data_ref: date, inicio: datetime, tempo: str, motivo: str) -> bool:
    msg = (
        "⏰ Registro de Horas Extras\n\n"
        f"👤 Consultor: {consultor}\n"
        f"📅 Data: {data_ref.strftime('%d/%m/%Y')}\n"
        f"🕐 Início: {inicio.strftime('%H:%M')}\n"
        f"⏱️ Tempo Total: {tempo}\n"
        f"📝 Motivo: {motivo}"
    )
    return notify_registro_ferramenta(
        H_EXTRAS,
        consultor,
        dados={"data": data_ref.strftime("%d/%m/%Y"), "inicio": inicio.strftime("%H:%M"), "tempo": tempo, "motivo": motivo},
        mensagem=msg,
    )


def send_atendimento_to_chat(
    consultor: str,
    data_ref: date,
    usuario: str,
    nome_setor: str,
    sistema: str,
    descricao: str,
    canal: str,
    desfecho: str,
    jira_opcional: str = "",
) -> bool:
    jira_str = f"\n🔢 Jira: CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = (
        "📋 Novo Registro de Atendimento\n\n"
        f"👤 Consultor: {consultor}\n"
        f"📅 Data: {data_ref.strftime('%d/%m/%Y')}\n"
        f"👥 Usuário: {usuario}\n"
        f"🏢 Nome/Setor: {nome_setor}\n"
        f"💻 Sistema: {sistema}\n"
        f"📝 Descrição: {descricao}\n"
        f"📞 Canal: {canal}\n"
        f"✅ Desfecho: {desfecho}{jira_str}"
    )
    return notify_registro_ferramenta(
        ATENDIMENTOS,
        consultor,
        dados={
            "data": data_ref.strftime("%d/%m/%Y"),
            "usuario": usuario,
            "setor": nome_setor,
            "sistema": sistema,
            "descricao": descricao,
            "canal": canal,
            "desfecho": desfecho,
            "jira": jira_opcional,
        },
        mensagem=msg,
    )


def send_chamado_to_chat(consultor: str, texto: str) -> bool:
    if not consultor or consultor == "Selecione um nome" or not (texto or "").strip():
        return False
    data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
    msg = f"🆘 Rascunho de Chamado/Jira\n📅 Data: {data_envio}\n\n👤 Autor: {consultor}\n\n📝 Texto:\n{texto}"
    return notify_registro_ferramenta(CHAMADOS, consultor, dados={"texto": texto, "data": data_envio}, mensagem=msg)


# Patch 10 — função faltante no código antigo
def handle_chamado_submission() -> bool:
    """Submete o chamado a partir do textarea."""
    consultor = st.session_state.get("consultor_selectbox", "")
    texto = st.session_state.get("chamado_textarea", "")
    return send_chamado_to_chat(consultor, texto)


# Patch 11 — corrigido
def handle_sugestao_submission(consultor: str, texto: str) -> bool:
    data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
    ip_usuario = get_remote_ip()
    msg = f"💡 Nova Sugestão\n📅 Data: {data_envio}\n👤 Autor: {consultor}\n🌐 IP: {ip_usuario}\n\n📝 Sugestão:\n{texto}"
    return notify_registro_ferramenta(SUGESTAO, consultor, dados={"texto": texto, "data": data_envio, "ip": ip_usuario}, mensagem=msg)


# -------------------------
# Session init + sync
# -------------------------
def memory_sweeper() -> None:
    if "last_cleanup" not in st.session_state:
        st.session_state["last_cleanup"] = time.time()
        return
    if time.time() - st.session_state["last_cleanup"] > 300:
        st.session_state["word_buffer"] = None
        gc.collect()
        st.session_state["last_cleanup"] = time.time()

    if "last_hard_cleanup" not in st.session_state:
        st.session_state["last_hard_cleanup"] = time.time()
    if time.time() - st.session_state["last_hard_cleanup"] > 14400:  # 4h
        st.cache_data.clear()
        gc.collect()
        st.session_state["last_hard_cleanup"] = time.time()


def init_session_state(team_id: int, consultores_list: List[str]) -> None:
    # Patch 4: browser_id lazy — só chama aqui e com try
    if "device_id_val" not in st.session_state:
        try:
            st.session_state["device_id_val"] = get_browser_id()
        except Exception:
            st.session_state["device_id_val"] = "unknown_device"

    st.session_state["CONSULTORES_RUNTIME"] = list(consultores_list)

    if "db_loaded" not in st.session_state:
        db = load_state_from_db(team_id)
        if db:
            st.session_state.update(db)
        st.session_state["db_loaded"] = True

    defaults: Dict[str, Any] = {
        "bastao_start_time": None,
        "report_last_run_date": datetime.min,
        "rotation_gif_start_time": None,
        "play_sound": False,
        "gif_warning": False,
        "lunch_warning_info": None,
        "last_reg_status": None,
        "auxilio_ativo": False,
        "active_view": None,
        "consultor_selectbox": st.session_state.get("consultor_logado") or "Selecione um nome",
        "status_texto": {n: "Indisponível" for n in consultores_list},
        "bastao_queue": [],
        "skip_flags": {},
        "current_status_starts": {n: get_brazil_time() for n in consultores_list},
        "bastao_counts": {n: 0 for n in consultores_list},
        "priority_return_queue": [],
        "daily_logs": [],
        "previous_states": {},
        "quick_indicators": {},
        "_last_save_time": 0.0,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # normaliza tipos
    if isinstance(st.session_state.get("report_last_run_date"), str):
        dt = _parse_dt(st.session_state.get("report_last_run_date"))
        st.session_state["report_last_run_date"] = dt or get_brazil_time()

    bst = _parse_dt(st.session_state.get("bastao_start_time"))
    st.session_state["bastao_start_time"] = bst

    # status starts
    starts = st.session_state.get("current_status_starts")
    if isinstance(starts, dict):
        for n in consultores_list:
            st.session_state["current_status_starts"][n] = _parse_dt(starts.get(n)) or get_brazil_time()

    # flags default
    for n in consultores_list:
        st.session_state["skip_flags"].setdefault(n, False)


def save_state() -> None:
    tid = st.session_state.get("team_id")
    if not tid:
        return

    state_to_save = {
        "status_texto": st.session_state.get("status_texto", {}),
        "bastao_queue": st.session_state.get("bastao_queue", []),
        "skip_flags": st.session_state.get("skip_flags", {}),
        "current_status_starts": st.session_state.get("current_status_starts", {}),
        "bastao_counts": st.session_state.get("bastao_counts", {}),
        "priority_return_queue": st.session_state.get("priority_return_queue", []),
        "bastao_start_time": st.session_state.get("bastao_start_time"),
        "report_last_run_date": st.session_state.get("report_last_run_date"),
        "daily_logs": st.session_state.get("daily_logs", []),
        "previous_states": st.session_state.get("previous_states", {}),
        "quick_indicators": st.session_state.get("quick_indicators", {}),
    }
    save_state_to_db(int(tid), state_to_save)
    load_state_from_db.clear()


def sync_state_from_db() -> None:
    # Se salvei há pouco, não puxa do banco (evita "pisar" no local)
    if time.time() - float(st.session_state.get("_last_save_time", 0)) < 3.0:
        return
    tid = st.session_state.get("team_id")
    if not tid:
        return
    db_data = load_state_from_db(int(tid))
    if not db_data:
        return

    # Patch 5: deserialização
    if "report_last_run_date" in db_data:
        db_data["report_last_run_date"] = _parse_dt(db_data.get("report_last_run_date")) or st.session_state.get("report_last_run_date")
    if "bastao_start_time" in db_data:
        db_data["bastao_start_time"] = _parse_dt(db_data.get("bastao_start_time"))
    if "current_status_starts" in db_data and isinstance(db_data["current_status_starts"], dict):
        fixed = {}
        for k, v in db_data["current_status_starts"].items():
            fixed[k] = _parse_dt(v) or get_brazil_time()
        db_data["current_status_starts"] = fixed

    st.session_state.update(db_data)


# -------------------------
# Watcher (Patch 5)
# -------------------------
@st.fragment(run_every=20)
def watcher_de_atualizacoes() -> None:
    try:
        if time.time() - float(st.session_state.get("_last_save_time", 0)) < 5.0:
            return

        tid = st.session_state.get("team_id")
        sb = get_supabase()
        if not sb or not tid:
            return

        res = sb.table(DB_TABLE_APP_STATE).select("data").eq("id", int(tid)).execute()
        if not (res.data and len(res.data) > 0):
            return

        remote_data = res.data[0].get("data", {}) or {}
        if not isinstance(remote_data, dict):
            return

        rem_status = remote_data.get("status_texto", {}) or {}
        rem_queue = remote_data.get("bastao_queue", []) or []
        loc_status = st.session_state.get("status_texto", {}) or {}
        loc_queue = st.session_state.get("bastao_queue", []) or []

        # comparação segura
        if rem_status != loc_status or rem_queue != loc_queue:
            load_state_from_db.clear()
            sync_state_from_db()
            st.rerun()
    except Exception:
        return


# -------------------------
# UI
# -------------------------
def _inject_css() -> None:
    st.markdown(
        """
        <style>
          .sticky-topbar { position: sticky; top: 0; z-index: 999; background: rgba(255,255,255,0.98);
                           border-bottom: 1px solid #eee; padding: 8px 12px; margin-bottom: 10px; }
          .sticky-topbar .muted { color: #666; font-size: 0.85rem; }

          /* Patch 6: Botão ❌ compacto na fila */
          .small-remove-btn button {
            padding: 2px 8px !important;
            min-height: 28px !important;
            max-height: 28px !important;
            font-size: 14px !important;
            line-height: 1 !important;
            border-radius: 8px !important;
            width: auto !important;
            min-width: 32px !important;
            max-width: 36px !important;
          }

          /* Patch 8: Botão ⬆️ compacto nos Indisponíveis */
          .small-back-btn button {
            padding: 2px 8px !important;
            min-height: 28px !important;
            max-height: 28px !important;
            font-size: 14px !important;
            line-height: 1 !important;
            border-radius: 8px !important;
            width: auto !important;
            min-width: 32px !important;
            max-width: 36px !important;
          }

          .queue-pill {
            display:inline-block; padding: 4px 10px; border-radius: 999px;
            border: 1px solid rgba(0,0,0,0.08); margin-right:6px; margin-bottom:6px;
            background: rgba(255,140,0,0.08);
            font-weight: 700;
          }
          .queue-pill.current { background: rgba(255,140,0,0.20); }
          .status-card { border: 1px solid rgba(0,0,0,0.06); border-radius: 14px; padding: 12px 14px; margin-bottom: 8px; }
          .status-card small { color: rgba(0,0,0,0.62); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _toast_if_any() -> None:
    msg = st.session_state.get("_toast_msg")
    if not msg:
        return
    try:
        st.toast(msg)
    except Exception:
        if str(msg).startswith("🔥"):
            st.error(msg)
        else:
            st.success(msg)
    st.session_state["_toast_msg"] = None


def _render_queue() -> None:
    holder = get_bastao_holder_atual()
    proximos = get_proximos_bastao(holder, n=2)
    queue = st.session_state.get("bastao_queue") or []

    st.subheader("🎭 Fila do Bastão")
    if not queue:
        st.info("Fila vazia. Entre na fila para iniciar a rotação.")
        return

    pills = []
    for n in queue:
        cls = "queue-pill current" if n == holder else "queue-pill"
        pills.append(f"<span class='{cls}'>{n}</span>")
    st.markdown("".join(pills), unsafe_allow_html=True)

    st.caption(f"👤 Com bastão: **{holder or '-'}**  |  🔜 Próximos: **{', '.join(proximos) if proximos else '-'}**")


def _render_status_overview(usuario_logado: str) -> None:
    st.subheader("📌 Status da equipe")
    status_texto: Dict[str, str] = st.session_state.get("status_texto") or {}
    consultores: List[str] = st.session_state.get("CONSULTORES_RUNTIME") or []

    for nome in consultores:
        status = status_texto.get(nome, "") or ""
        indic = _get_quick_indic(nome)
        icons = _icons_telefone_cafe(indic)

        can_edit = (nome == usuario_logado)  # Patch 7

        col1, col2, col3 = st.columns([3, 2, 2], vertical_alignment="center")

        with col1:
            st.markdown(f"<div class='status-card'><b>{nome}</b><br><small>{(status or 'Fila')}{icons}</small></div>", unsafe_allow_html=True)

        with col2:
            if can_edit:
                # status editável apenas para o logado
                opt = st.selectbox(
                    "Status",
                    options=["(Manter)"] + OPCOES_STATUS_FILA + ["Indisponível"],
                    key=f"status_sel_{nome}",
                    label_visibility="collapsed",
                )
                if opt != "(Manter)":
                    if opt == "Indisponível":
                        if st.button("Aplicar", key=f"apply_ind_{nome}"):
                            update_status("Indisponível", marcar_indisponivel=True)
                            st.rerun()
                    else:
                        if st.button("Aplicar", key=f"apply_{nome}"):
                            update_status(opt, marcar_indisponivel=(opt == "Almoço"), manter_fila_atual=True)
                            st.rerun()
            else:
                st.selectbox(
                    "Status",
                    options=["(Somente leitura)"],
                    key=f"ro_{nome}",
                    disabled=True,
                    label_visibility="collapsed",
                )

        with col3:
            # Controles de fila só para o logado
            if can_edit:
                in_queue = nome in (st.session_state.get("bastao_queue") or [])
                btn_lbl = "Sair da fila" if in_queue else "Entrar na fila"
                if st.button(btn_lbl, key=f"q_{nome}"):
                    toggle_queue(nome)
                    st.rerun()
            else:
                st.button("—", key=f"noop_{nome}", disabled=True)


def _render_quick_controls(usuario_logado: str) -> None:
    st.subheader("⚡ Indicadores rápidos")
    if not usuario_logado:
        st.info("Faça login para usar os indicadores.")
        return

    c1, c2, c3 = st.columns([1, 1, 2], vertical_alignment="center")

    with c1:
        if st.button("📞", help="Marcar Telefone"):
            toggle_quick_telefone()
            st.rerun()

    with c2:
        if st.button("☕", help="Marcar Café"):
            toggle_quick_cafe()
            st.rerun()

    with c3:
        indic = _get_quick_indic(usuario_logado)
        st.caption(f"Status rápido de **{usuario_logado}**: {_icons_telefone_cafe(indic) or '—'}")


def _render_actions(usuario_logado: str) -> None:
    st.subheader("🎛️ Ações")
    c1, c2, c3 = st.columns([2, 2, 2], vertical_alignment="center")

    with c1:
        if st.button("🔄 Passar Bastão (apenas quem está com ele)", use_container_width=True):
            rotate_bastao()
            st.rerun()

    with c2:
        if st.button("👤 Assumir Bastão (forçar)", use_container_width=True):
            # força bastão para o logado, mantendo fila
            if usuario_logado and usuario_logado != "Selecione um nome":
                if usuario_logado not in st.session_state["bastao_queue"]:
                    st.session_state["bastao_queue"].insert(0, usuario_logado)
                check_and_assume_baton(forced_successor=usuario_logado, immune_consultant=usuario_logado)
                st.rerun()

    with c3:
        if st.button("💾 Salvar agora", use_container_width=True):
            save_state()
            st.rerun()


def _render_registros(usuario_logado: str) -> None:
    st.subheader("🧾 Registros")
    if not usuario_logado or usuario_logado == "Selecione um nome":
        st.info("Faça login para registrar.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["⏰ Horas Extras", "📋 Atendimento", "🆘 Chamado/Jira", "💡 Sugestão"])

    with tab1:
        colA, colB = st.columns([1, 1])
        with colA:
            data_ref = st.date_input("Data", value=get_brazil_time().date(), key="hx_data")
        with colB:
            inicio_hora = st.time_input("Início", value=get_brazil_time().time().replace(second=0, microsecond=0), key="hx_inicio")
        tempo = st.text_input("Tempo Total (HH:MM)", value="01:00", key="hx_tempo")
        motivo = st.text_area("Motivo", key="hx_motivo")
        if st.button("Enviar Horas Extras", key="hx_send"):
            dt_inicio = datetime.combine(data_ref, inicio_hora)
            ok = send_horas_extras_to_chat(usuario_logado, data_ref, dt_inicio, tempo, motivo)
            st.success("Enviado ✅" if ok else "Falhou ❌")

    with tab2:
        data_ref = st.date_input("Data", value=get_brazil_time().date(), key="at_data")
        usuario = st.text_input("Usuário", key="at_usuario")
        setor = st.text_input("Nome/Setor", key="at_setor")
        sistema = st.selectbox("Sistema", options=REG_SISTEMA_OPCOES, key="at_sistema")
        canal = st.selectbox("Canal", options=REG_CANAL_OPCOES, key="at_canal")
        desfecho = st.selectbox("Desfecho", options=REG_DESFECHO_OPCOES, key="at_desfecho")
        descricao = st.text_area("Descrição", key="at_desc")
        jira = st.text_input("Jira (opcional - só número)", key="at_jira")
        if st.button("Enviar Atendimento", key="at_send"):
            ok = send_atendimento_to_chat(usuario_logado, data_ref, usuario, setor, sistema, descricao, canal, desfecho, jira)
            st.success("Enviado ✅" if ok else "Falhou ❌")

    with tab3:
        st.text_area("Texto do chamado", key="chamado_textarea", height=220)
        if st.button("Enviar Chamado", key="ch_send"):
            ok = handle_chamado_submission()
            st.success("Enviado ✅" if ok else "Falhou ❌")

    with tab4:
        sugest = st.text_area("Sugestão", key="sug_texto", height=220)
        if st.button("Enviar Sugestão", key="sug_send"):
            ok = handle_sugestao_submission(usuario_logado, sugest)
            st.success("Enviado ✅" if ok else "Falhou ❌")


def render_dashboard(
    team_id: int,
    team_name: str,
    consultores_list: List[str],
    webhook_key: str,
    app_url: str,
    other_team_id: int,
    other_team_name: str,
    usuario_logado: str,
) -> None:
    # ---- Estado e contexto
    st.session_state["team_id"] = int(team_id)
    st.session_state["team_name"] = team_name
    st.session_state["other_team_id"] = int(other_team_id)
    st.session_state["other_team_name"] = other_team_name
    st.session_state["webhook_key"] = webhook_key
    st.session_state["app_url"] = app_url

    if usuario_logado:
        st.session_state["consultor_logado"] = usuario_logado
        if st.session_state.get("consultor_selectbox") in (None, "", "Selecione um nome"):
            st.session_state["consultor_selectbox"] = usuario_logado

    init_session_state(int(team_id), consultores_list)
    memory_sweeper()
    ensure_daily_reset()

    # watcher (Patch 5)
    watcher_de_atualizacoes()

    # ---- UI
    _inject_css()
    _toast_if_any()

    # topbar
    try:
        _user_top = st.session_state.get("consultor_logado") or "-"
        _team_top = st.session_state.get("team_name") or team_name or "-"
        _now_top = get_brazil_time().strftime("%d/%m/%Y %H:%M:%S")
        st.markdown(
            f"<div class='sticky-topbar'>"
            f"<div style='display:flex; justify-content:space-between; align-items:center; gap:12px;'>"
            f"<div><b>👤 Logado como:</b> {_user_top} &nbsp; <span class='muted'>|</span> &nbsp; <b>👥 Equipe:</b> {_team_top}</div>"
            f"<div class='muted'>🕒 {_now_top}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    st.info("🎗️ Fevereiro Laranja — Apoie a conscientização sobre leucemia.")

    # selector (somente leitura visual)
    st.session_state["consultor_selectbox"] = usuario_logado or st.session_state.get("consultor_selectbox", "Selecione um nome")

    _render_queue()
    _render_quick_controls(usuario_logado)
    _render_actions(usuario_logado)
    _render_status_overview(usuario_logado)
    _render_registros(usuario_logado)

    # garante bastão se houver fila
    if st.session_state.get("bastao_queue"):
        check_and_assume_baton()

