import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from datetime import datetime
import os
import json
import socket 
import requests

# --- BIBLIOTECAS GOOGLE OAUTH ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Migrador SQL - Cloud v3", layout="wide", page_icon="🧰")

# --- 2. TRAVA DE SEGURANÇA ---
if not st.session_state.get('autenticado'):
    st.error("🚫 Acesso negado! Por favor, faça login no Portal primeiro.")
    st.stop()

# --- 3. VERIFICAÇÃO DE PERMISSÃO ---
if not st.session_state.get('p1', False):
    st.warning("⚠️ Você não tem permissão para acessar o Migrador.")
    st.stop()

st.title("🧰 SQL Smart Migrator (v3 Cloud)")

# --- CONFIGURAÇÃO DE CAMINHOS E SECRETS ---
PASTA_CREDENCIAIS = "Credencials"
ARQUIVO_TOKEN = os.path.join(PASTA_CREDENCIAIS, "token.json") if os.path.exists(PASTA_CREDENCIAIS) else "token.json"
ID_PADRAO_DRIVE = "1M2OZgy3MV8JcYyvMngVE5ZDEHChwmCR2" 
SCOPES = ['https://www.googleapis.com/auth/drive.file']

DRIVERS_SQL_SERVER = ["ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server", "SQL Server"]
DEFAULT_PORTS = {"SQL Server": "1433", "MySQL": "3306", "PostgreSQL": "5432"}

# --- NOVO: FUNÇÃO DE DIAGNÓSTICO DE REDE ---
def testar_porta_rede(host, port, timeout=2):
    """Verifica se a porta TCP está acessível antes de tentar login no banco."""
    try:
        port = int(port)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

# --- FUNÇÕES GOOGLE ---
def autenticar_google_drive():
    creds = None
    if "google" in st.secrets and "token_json" in st.secrets["google"]:
        try:
            token_info = json.loads(st.secrets["google"]["token_json"])
            creds = Credentials.from_authorized_user_info(token_info, SCOPES)
        except: pass

    if creds and creds.expired and creds.refresh_token:
        try: creds.refresh(Request())
        except: creds = None

    if not creds:
        if "google" in st.secrets:
            try:
                client_config = json.loads(st.secrets["google"]["client_secret"])
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                if os.getenv("STREAMLIT_RUNTIME_ENV"):
                    return None, "Token expirado nas Secrets."
                creds = flow.run_local_server(port=8090)
            except Exception as e: return None, str(e)
        else: return None, "Secrets não configuradas."

    return build('drive', 'v3', credentials=creds), "OK"

def upload_para_drive(service, caminho_arquivo, nome_arquivo, id_pasta):
    try:
        file_metadata = {'name': nome_arquivo, 'parents': [id_pasta]}
        media = MediaFileUpload(caminho_arquivo, mimetype='text/csv')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True, file.get('id')
    except Exception as e: return False, str(e)

# --- FUNÇÕES DE BANCO DE DADOS ---
def montar_url_universal(tipo, driver_sql, host, port, db, user, pwd):
    port = int(port) if port and str(port).isnumeric() else None 
    if tipo == "SQL Server":
        conn_str = f"DRIVER={{{driver_sql}}};SERVER={host},{port};DATABASE={db};UID={user};PWD={pwd};TrustServerCertificate=yes;"
        return URL.create("mssql+pyodbc", query={"odbc_connect": conn_str})
    elif tipo == "MySQL":
        return URL.create("mysql+pymysql", username=user, password=pwd, host=host, port=port or 3306, database=db)
    elif tipo == "PostgreSQL":
        return URL.create("postgresql+psycopg2", username=user, password=pwd, host=host, port=port or 5432, database=db)
    return None

def testar_conexao(url):
    try:
        eng = create_engine(url)
        with eng.connect() as c: return True, None, eng
    except Exception as e: return False, str(e), None

def listar_bancos_disponiveis(tipo, driver, host, port, user, pwd):
    db_sistema = "master" if tipo == "SQL Server" else "postgres" if tipo == "PostgreSQL" else ""
    if tipo == "MySQL": db_sistema = ""
    try:
        url = montar_url_universal(tipo, driver, host, port, db_sistema, user, pwd)
        eng = create_engine(url)
        with eng.connect() as conn:
            if tipo == "SQL Server": q = "SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb')"
            elif tipo == "PostgreSQL": q = "SELECT datname FROM pg_database WHERE datistemplate = false"
            else: q = "SHOW DATABASES"
            res = conn.execute(text(q))
            if tipo == "MySQL":
                bancos_sistema = ['information_schema', 'mysql', 'performance_schema', 'sys']
                return [r[0] for r in res if r[0] not in bancos_sistema]
            return [r[0] for r in res]
    except Exception as e:
        # Retorna None explicitamente para diferenciar de lista vazia
        st.error(f"Erro de conexão SQL: {e}") 
        return None 

# --- COMPONENTE VISUAL DE INPUT (MODIFICADO) ---
def render_inputs(titulo, k):
    st.subheader(titulo)
    tipo = st.selectbox("Tecnologia", ["SQL Server", "MySQL", "PostgreSQL"], key=f"{k}_t")
    drv = st.selectbox("Driver", DRIVERS_SQL_SERVER, key=f"{k}_d") if tipo == "SQL Server" else None
    
    c_h, c_p = st.columns([3, 1])
    with c_h: host = st.text_input("Host / IP", "localhost", key=f"{k}_h")
    with c_p: port = st.text_input("Porta", DEFAULT_PORTS[tipo], key=f"{k}_p")
    
    c_u, c_pass = st.columns(2)
    with c_u: user = st.text_input("Usuário", key=f"{k}_u")
    with c_pass: pwd = st.text_input("Senha", type="password", key=f"{k}_pw")

    chave_lista = f"list_{k}"
    if chave_lista not in st.session_state: st.session_state[chave_lista] = []

    # --- LÓGICA DO BOTÃO COM DIAGNÓSTICO ---
    if st.button(f"🔍 Listar Bancos", key=f"btn_l_{k}", use_container_width=True):
        with st.spinner("Conectando e buscando bancos..."):
            resultado = listar_bancos_disponiveis(tipo, drv, host, port, user, pwd)
            
            if resultado is not None:
                st.session_state[chave_lista] = resultado
                st.success(f"{len(resultado)} bancos encontrados!")
            else:
                # SE FALHAR O SQL, RODAMOS O DIAGNÓSTICO DE REDE
                st.session_state[chave_lista] = []
                st.markdown("---")
                st.warning("⚠️ Iniciando diagnóstico de rede automático...")
                
                porta_aberta = testar_porta_rede(host, port)
                
                if porta_aberta:
                    st.info("""
                    ✅ **Diagnóstico:** A porta está ABERTA e acessível.
                    O problema provavelmente é **Usuário/Senha incorretos** ou o driver ODBC não está instalado corretamente.
                    """)
                else:
                    st.error(f"""
                    ⛔ **Diagnóstico Crítico:** A porta {port} está FECHADA ou INACESSÍVEL.
                    O Firewall do servidor ou da rede está bloqueando a conexão.
                    """)
                    
                    # Exibe solução para SQL Server no Windows
                    if tipo == "SQL Server":
                        with st.expander(f"💡 Solução Rápida (PowerShell)", expanded=True):
                            st.caption("Execute no servidor como Administrador para liberar a porta:")
                            st.code(f"""
New-NetFirewallRule -DisplayName "SQL Server Port {port}" -Direction Inbound -LocalPort {port} -Protocol TCP -Action Allow
                            """, language="powershell")

    if st.session_state[chave_lista]:
        db = st.selectbox("Selecione o Banco", st.session_state[chave_lista], key=f"{k}_db_s")
    else:
        db = st.text_input("Nome do Banco (Manual)", key=f"{k}_db_m")

    return tipo, drv, host, port, db, user, pwd

def consultar_ia_render(prompt_usuario, historico):
    try:
        # A URL mágica da sua API que já está na nuvem
        url_api = "https://api-sql-migrator.onrender.com/chat"
        
        texto_historico = ""
        for msg in historico[-4:]: 
            papel = "Usuário" if msg["role"] == "user" else "IA"
            texto_historico += f"{papel}: {msg['content']}\n"
            
        prompt_final = prompt_usuario
        if texto_historico:
            prompt_final = f"Contexto da conversa recente:\n{texto_historico}\n\nNova instrução/pergunta: {prompt_usuario}"

        response = requests.post(url_api, json={"mensagem_usuario": prompt_final})
        
        if response.status_code == 200:
            return response.json()['resposta']
        else:
            return f"🚨 Erro na API do Render: Status {response.status_code}"
            
    except Exception as e:
        return f"🚨 Erro Crítico de Comunicação com a API: {e}"

# --- SIDEBAR ---
with st.sidebar:
    st.header("☁️ Google Drive")
    if st.button("📡 Testar Conexão Google"):
        srv, msg = autenticar_google_drive()
        if srv: 
            user = srv.about().get(fields="user").execute()
            st.success(f"Logado como: {user['user']['displayName']}")
        else: st.error(msg)
    
    st.divider()
    
    # --- NOVO: AGENTE DE IA NA SIDEBAR ---
    st.header("🤖 Assistente de IA")
    st.caption("Ajuda rápida com scripts e análises.")

    if "mensagens_chat" not in st.session_state:
        st.session_state.mensagens_chat = []

    # Cria uma caixa com altura fixa e barra de rolagem (Fica muito mais limpo!)
    caixa_chat = st.container(height=350)

    with caixa_chat:
        for msg in st.session_state.mensagens_chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # O input do chat fixado embaixo da caixa
    if prompt := st.chat_input("Dúvidas com SQL?", key="chat_sidebar"):
        
        # 1. Salva e mostra a mensagem do usuário
        st.session_state.mensagens_chat.append({"role": "user", "content": prompt})
        with caixa_chat:
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # 2. Mostra o balão da IA carregando
            with st.chat_message("assistant"):
                with st.spinner("Consultando a nuvem..."):
                    # Manda para o Render
                    resposta_texto = consultar_ia_render(prompt, st.session_state.mensagens_chat[:-1])
                    st.markdown(resposta_texto)
                    
        # 3. Salva a resposta da IA no histórico
        st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_texto})

    st.divider()
    
    if st.button("⬅️ Voltar ao Menu Principal", use_container_width=True):
        st.switch_page("Login.py")

    st.markdown("---")
    st.caption("v4.0 - Cloud Edition + NetDiag + IA Integrada")