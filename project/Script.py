import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from datetime import datetime
import os
import json

# --- BIBLIOTECAS GOOGLE OAUTH ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Migrador SQL - Cloud v3", layout="wide", page_icon="☁️")
st.title("☁️ Migrador SQL (Versão Cloud)")

# --- CONFIGURAÇÃO ---
PASTA_CREDENCIAIS = "Credencials"
ARQUIVO_TOKEN = os.path.join(PASTA_CREDENCIAIS, "token.json") if os.path.exists(PASTA_CREDENCIAIS) else "token.json"
ID_PADRAO_DRIVE = "1M2OZgy3MV8JcYyvMngVE5ZDEHChwmCR2" 
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- FUNÇÕES GOOGLE (OTIMIZADA PARA NUVEM) ---
def autenticar_google_drive():
    creds = None
    
    # 1. TENTA CARREGAR DAS SECRETS (Prioridade Total para o Streamlit Cloud)
    if "google" in st.secrets:
        if "token_json" in st.secrets["google"]:
            try:
                token_info = json.loads(st.secrets["google"]["token_json"])
                creds = Credentials.from_authorized_user_info(token_info, SCOPES)
            except Exception as e:
                st.warning(f"Aviso: Não foi possível ler o token das Secrets. Tentando outros métodos.")

    # 2. TENTA CARREGAR ARQUIVO LOCAL (Fallback para seu PC)
    if not creds:
        try:
            if os.path.exists(ARQUIVO_TOKEN):
                creds = Credentials.from_authorized_user_file(ARQUIVO_TOKEN, SCOPES)
        except:
            pass

    # 3. VALIDAÇÃO E RENOVAÇÃO AUTOMÁTICA
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            st.error(f"Erro ao renovar acesso: {e}")
            creds = None

    # 4. CASO NÃO TENHA TOKEN VÁLIDO
    if not creds:
        if "google" in st.secrets:
            try:
                client_config = json.loads(st.secrets["google"]["client_secret"])
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                
                if os.getenv("STREAMLIT_RUNTIME_ENV"):
                    return None, "Token expirado. Por favor, gere um novo token localmente e atualize as Secrets."
                
                creds = flow.run_local_server(port=8090)
                
                if os.path.exists(PASTA_CREDENCIAIS):
                    with open(ARQUIVO_TOKEN, 'w') as token:
                        token.write(creds.to_json())
            except Exception as e:
                return None, f"Erro na autenticação: {e}"
        else:
            return None, "Configuração de segredos ausente."

    try:
        service = build('drive', 'v3', credentials=creds)
        return service, "OK"
    except Exception as e:
        return None, f"Erro ao criar serviço: {e}"

def upload_para_drive(service, caminho_arquivo, nome_arquivo, id_pasta):
    try:
        file_metadata = {'name': nome_arquivo, 'parents': [id_pasta]}
        media = MediaFileUpload(caminho_arquivo, mimetype='text/csv')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True, file.get('id')
    except Exception as e:
        return False, str(e)

# --- FUNÇÕES DE BANCO DE DADOS ---
DRIVERS_SQL_SERVER = ["ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server", "SQL Server"]
DEFAULT_PORTS = {"SQL Server": "1433", "MySQL": "3306", "PostgreSQL": "5432"}

def montar_url_universal(tipo, driver_sql, host, port, db, user, pwd):
    port = int(port) if port and port.isnumeric() else None
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
    try:
        url = montar_url_universal(tipo, driver, host, port, db_sistema, user, pwd)
        eng = create_engine(url)
        with eng.connect() as conn:
            if tipo == "SQL Server":
                q = "SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb')"
            elif tipo == "PostgreSQL":
                q = "SELECT datname FROM pg_database WHERE datistemplate = false"
            else:
                q = "SHOW DATABASES"
            return [r[0] for r in conn.execute(text(q))]
    except Exception as e:
        st.error(f"Erro ao listar: {e}")
        return []

# --- INTERFACE ---
with st.sidebar:
    st.header("☁️ Status Cloud")
    if "google" in st.secrets:
        if st.button("🔑 Conectar ao Google Drive"):
            srv, msg = autenticar_google_drive()
            if srv: st.success("Autenticado!")
            else: st.error(msg)
    else:
        st.error("Secrets não configuradas.")

col1, col2 = st.columns(2)

def render_inputs(titulo, k):
    st.subheader(titulo)
    tipo = st.selectbox("Tecnologia", ["SQL Server", "MySQL", "PostgreSQL"], key=f"{k}_t")
    drv = st.selectbox("Driver", DRIVERS_SQL_SERVER, key=f"{k}_d") if tipo == "SQL Server" else None
    h = st.text_input("Host", "localhost", key=f"{k}_h")
    p = st.text_input("Porta", DEFAULT_PORTS[tipo], key=f"{k}_p")
    u = st.text_input("Usuário", key=f"{k}_u")
    pw = st.text_input("Senha", type="password", key=f"{k}_pw")
    db = st.text_input("Banco (Schema)", key=f"{k}_db")
    return tipo, drv, h, p, db, u, pw

with col1: src_data = render_inputs("1. Origem", "src")
with col2: dst_data = render_inputs("2. Destino", "dst")

st.divider()
tab = st.text_input("Tabela para Migrar")
if st.button("🚀 Executar Migração Cloud", type="primary"):
    if not tab: st.error("Defina a tabela.")
    else:
        with st.status("Migrando...") as s:
            t, d, h, p, db, u, pw = src_data
            url = montar_url_universal(t, d, h, p, db, u, pw)
            ok, err, eng = testar_conexao(url)
            if ok:
                df = pd.read_sql_table(tab, eng)
                st.dataframe(df.head())
                s.update(label="Migração Concluída!", state="complete")
            else:
                st.error(err)