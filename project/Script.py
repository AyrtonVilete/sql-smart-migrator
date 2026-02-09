import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from datetime import datetime
import os
import json
import socket
import platform

# --- BIBLIOTECAS GOOGLE OAUTH ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Tenta importar pyodbc, mas trata erro caso o driver não esteja instalado no Linux
try:
    import pyodbc
    TEM_PYODBC = True
except ImportError:
    TEM_PYODBC = False

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Migrador SQL Híbrido", layout="wide", page_icon="🌐")
st.title("🌐 Migrador SQL (Local & Nuvem)")

# --- DETECÇÃO DE AMBIENTE ---
def detectar_ambiente():
    """
    Retorna True se estivermos rodando em Nuvem (Streamlit Cloud/PythonAnywhere)
    Retorna False se for Localhost.
    """
    try:
        # Verifica variáveis comuns de ambiente de nuvem
        if os.environ.get('STREAMLIT_SERVER_HEADLESS') == 'true':
            return True
        if os.environ.get('PYTHONANYWHERE_DOMAIN'):
            return True
        return False
    except:
        return False

IS_CLOUD = detectar_ambiente()

# --- CONFIGURAÇÃO DE CAMINHOS ---
PASTA_CREDENCIAIS = "Credencials"
ID_PADRAO_DRIVE = "1M2OZgy3MV8JcYyvMngVE5ZDEHChwmCR2" 
SCOPES = ['https://www.googleapis.com/auth/drive.file']

if not os.path.exists(PASTA_CREDENCIAIS):
    os.makedirs(PASTA_CREDENCIAIS)

ARQUIVO_CLIENT_SECRET = os.path.join(PASTA_CREDENCIAIS, "client_secret.json")
ARQUIVO_TOKEN = os.path.join(PASTA_CREDENCIAIS, "token.json")

# --- FUNÇÕES AUXILIARES DE SISTEMA ---
def obter_drivers_disponiveis():
    """
    Lista os drivers ODBC instalados no sistema operacional atual.
    Vital para funcionar em Linux (Nuvem) onde os nomes são diferentes.
    """
    drivers_detectados = []
    if TEM_PYODBC:
        try:
            drivers_detectados = pyodbc.drivers()
        except:
            pass
    
    # Adiciona opções padrão caso não detecte nada ou para garantir compatibilidade
    lista_padrao = [
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 18 for SQL Server",
        "SQL Server",
        "FreeTDS", # Comum em Linux
        "Outro (Digitar Manualmente)"
    ]
    
    # Une as listas removendo duplicados e mantendo a ordem
    return list(dict.fromkeys(drivers_detectados + lista_padrao))

# --- FUNÇÕES GOOGLE ---
def autenticar_google_drive():
    creds = None
    # 1. Tenta carregar o token local (se existir)
    if os.path.exists(ARQUIVO_TOKEN):
        try:
            creds = Credentials.from_authorized_user_file(ARQUIVO_TOKEN, SCOPES)
        except:
            pass

    # 2. Se não houver token válido, inicia o login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                creds = None
        
        if not creds:
            # Tenta ler das Secrets do Streamlit Cloud
            if "google" in st.secrets:
                client_config = json.loads(st.secrets["google"]["client_secret"])
                # Usamos from_client_config para não precisar do arquivo .json
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
                
                # IMPORTANTE: run_local_server exige interação manual. 
                # No Cloud, isso abrirá a aba de login para você.
                creds = flow.run_local_server(port=8090)
                
                # Opcional: Salva o token localmente se estiver em dev
                if not os.getenv("STREAMLIT_RUNTIME_ENV"): # Detecta se NÃO está no cloud
                    with open(ARQUIVO_TOKEN, 'w') as token:
                        token.write(creds.to_json())
            else:
                return None, "Atenção: client_secret.json não encontrado e Secrets não configuradas."

    return build('drive', 'v3', credentials=creds), "OK"

def upload_para_drive(service, caminho_arquivo, nome_arquivo, id_pasta):
    try:
        file_metadata = {'name': nome_arquivo, 'parents': [id_pasta]}
        media = MediaFileUpload(caminho_arquivo, mimetype='text/csv')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True, file.get('id')
    except Exception as e: return False, str(e)

# --- FUNÇÕES DE BANCO DE DADOS ---

DEFAULT_PORTS = {
    "SQL Server": "1433",
    "MySQL": "3306",
    "PostgreSQL": "5432"
}

def montar_url_universal(tipo, driver_sql, manual_sql, host, port, db, user, pwd):
    port = int(port) if port and str(port).isnumeric() else None

    if tipo == "SQL Server":
        driver_final = manual_sql if driver_sql == "Outro (Digitar Manualmente)" else driver_sql
        # Conexão ODBC padrão
        conn_str = f"DRIVER={{{driver_final}}};SERVER={host},{port};DATABASE={db};UID={user};PWD={pwd};TrustServerCertificate=yes;"
        return URL.create("mssql+pyodbc", query={"odbc_connect": conn_str})
    
    elif tipo == "MySQL":
        return URL.create("mysql+pymysql", username=user, password=pwd, host=host, port=port or 3306, database=db)
    
    elif tipo == "PostgreSQL":
        return URL.create("postgresql+psycopg2", username=user, password=pwd, host=host, port=port or 5432, database=db)
    
    return None

def listar_bancos_disponiveis(tipo, driver, manual, host, port, user, pwd):
    db_sistema = "master" if tipo == "SQL Server" else "postgres" if tipo == "PostgreSQL" else ""
    if tipo == "MySQL": db_sistema = ""

    try:
        url = montar_url_universal(tipo, driver, manual, host, port, db_sistema, user, pwd)
        eng = create_engine(url)
        with eng.connect() as conn:
            if tipo == "SQL Server":
                q = "SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb')"
                return [r[0] for r in conn.execute(text(q))]
            elif tipo == "PostgreSQL":
                q = "SELECT datname FROM pg_database WHERE datistemplate = false"
                return [r[0] for r in conn.execute(text(q))]
            elif tipo == "MySQL":
                q = "SHOW DATABASES"
                return [r[0] for r in conn.execute(text(q)) if r[0] not in ['information_schema', 'mysql', 'performance_schema', 'sys']]
    except Exception as e:
        st.error(f"Erro ao listar: {e}")
        return []

def testar_conexao(url):
    try:
        eng = create_engine(url)
        with eng.connect() as c: return True, None, eng
    except Exception as e: return False, str(e), None

def render_inputs_banco(titulo, k):
    st.subheader(titulo)
    tipo = st.selectbox("Tecnologia", ["SQL Server", "MySQL", "PostgreSQL"], key=f"{k}_type")
    
    driver_sql = None
    manual_sql = None
    if tipo == "SQL Server":
        # CARREGA DRIVERS DINAMICAMENTE (Funciona em Local e Linux)
        lista_drivers = obter_drivers_disponiveis()
        driver_sql = st.selectbox("Versão Driver", lista_drivers, key=f"{k}_drv")
        if "Outro" in str(driver_sql): 
            manual_sql = st.text_input("Driver Manual", key=f"{k}_man")
    
    c_h, c_p = st.columns([3, 1])
    with c_h: host = st.text_input("Host / IP", "localhost", key=f"{k}_host")
    with c_p: port = st.text_input("Porta", DEFAULT_PORTS[tipo], key=f"{k}_port")
    
    c_u, c_pass = st.columns(2)
    with c_u: user = st.text_input("Usuário", "sa" if tipo == "SQL Server" else "root", key=f"{k}_user")
    with c_pass: pwd = st.text_input("Senha", type="password", key=f"{k}_pwd")
    
    # Auto-Listagem
    chave_lista = f"lista_bancos_{k}"
    if chave_lista not in st.session_state: st.session_state[chave_lista] = []

    if st.button(f"🔍 Listar Bancos", key=f"btn_list_{k}", use_container_width=True):
        if host and user:
            with st.spinner("Buscando..."):
                lista = listar_bancos_disponiveis(tipo, driver_sql, manual_sql, host, port, user, pwd)
                if lista:
                    st.session_state[chave_lista] = lista
                    st.toast(f"{len(lista)} bancos encontrados!", icon="✅")
                else: st.error("Nenhum banco encontrado.")
        else: st.warning("Preencha Host e Usuário.")

    if st.session_state[chave_lista]:
        db = st.selectbox("Selecione o Banco", st.session_state[chave_lista], key=f"{k}_db_select")
        if st.button("Digitar Manualmente", key=f"btn_clr_{k}"):
            st.session_state[chave_lista] = []
            st.rerun()
    else:
        db = st.text_input("Nome do Banco", key=f"{k}_db_manual")

    return tipo, driver_sql, manual_sql, host, port, db, user, pwd

# --- INTERFACE SIDEBAR ---
with st.sidebar:
    st.header("☁️ Status Google Drive")
    
    folder_id = ID_PADRAO_DRIVE # Variável oculta do usuário
    
    # Indicador de Ambiente
    if IS_CLOUD:
        st.info("🌐 Rodando em NUVEM")
    else:
        st.success("💻 Rodando LOCAL")

    if folder_id:
        st.caption("📁 Pasta Destino Configurada (Oculta)")
    else:
        st.error("⚠️ ID da Pasta não configurado no código!")

    if os.path.exists(ARQUIVO_TOKEN):
        st.success("✅ Login Ativo")
        col_test, col_logout = st.columns(2)
        with col_test:
            if st.button("📡 Ping API", use_container_width=True):
                with st.spinner("..."):
                    try:
                        srv, msg = autenticar_google_drive()
                        if srv: 
                            u = srv.about().get(fields="user").execute()
                            st.toast(f"Olá, {u['user']['displayName']}!", icon="✅")
                        else: st.error(msg)
                    except: st.error("Erro no token")
        with col_logout:
            if st.button("🚪 Sair", use_container_width=True):
                if os.path.exists(ARQUIVO_TOKEN):
                    os.remove(ARQUIVO_TOKEN)
                    st.rerun()
    else:
        st.warning("Não Autenticado")
        if IS_CLOUD:
            st.warning("⚠️ Na nuvem, faça upload do 'token.json' via FTP/Painel.")
        else:
            if st.button("🔑 Autenticar Agora", type="primary"):
                srv, msg = autenticar_google_drive()
                if srv: st.rerun()
                else: st.error(msg)

# --- PAINEL PRINCIPAL ---
col1, col2 = st.columns(2)

with col1:
    src_data = render_inputs_banco("1. Origem", "src")
    if st.button("🔌 Validar Origem", key="btn_src", use_container_width=True):
        t, d, m, h, p, db, u, pw = src_data
        if h and db and u:
            with st.spinner("Testando..."):
                url = montar_url_universal(t, d, m, h, p, db, u, pw)
                ok, err, _ = testar_conexao(url)
                if ok: st.success("✅ Conexão OK!")
                else: st.error("❌ Falha"); st.code(err)
        else: st.warning("Preencha os campos.")

with col2:
    dst_data = render_inputs_banco("2. Destino", "dst")
    if st.button("🔌 Validar Destino", key="btn_dst", use_container_width=True):
        t, d, m, h, p, db, u, pw = dst_data
        if h and db and u:
            with st.spinner("Testando..."):
                url = montar_url_universal(t, d, m, h, p, db, u, pw)
                ok, err, _ = testar_conexao(url)
                if ok: st.success("✅ Conexão OK!")
                else: st.error("❌ Falha"); st.code(err)
        else: st.warning("Preencha os campos.")

st.markdown("---")

st.subheader("🛠️ Migração")
c1, c2, c3 = st.columns(3)
with c1: tab = st.text_input("Tabela")
with c2: pk = st.text_input("Primary Key (ID)")
with c3: modo = st.selectbox("Estratégia", ["Inteligente", "Append", "Replace"])

st.subheader("▶️ Execução")
col_bkp, col_cloud, col_full = st.columns([1, 1, 1.5])

# BOTÃO 1: LOCAL
with col_bkp:
    if st.button("💾 Backup Local", use_container_width=True):
        if not tab: st.error("Informe tabela"); st.stop()
        t, d, m, h, p, db, u, pw = src_data
        try:
            url = montar_url_universal(t, d, m, h, p, db, u, pw)
            ok, err, eng = testar_conexao(url)
            if ok:
                df = pd.read_sql_table(tab, eng)
                fn = f"backup_{tab}_local.csv"
                df.to_csv(fn, index=False, sep=';')
                st.success(f"Gerado: {fn}")
                with open(fn, "rb") as f: st.download_button("Download", f, file_name=fn)
            else: st.error(err)
        except Exception as e: st.error(f"Erro: {e}")

# BOTÃO 2: NUVEM
with col_cloud:
    if st.button("☁️ Backup Drive", use_container_width=True):
        if not tab: st.error("Informe tabela"); st.stop()
        t, d, m, h, p, db, u, pw = src_data
        status = st.status("Processando...", expanded=True)
        try:
            url = montar_url_universal(t, d, m, h, p, db, u, pw)
            ok, err, eng = testar_conexao(url)
            if not ok: status.write("Erro conexão"); st.stop()
            
            df = pd.read_sql_table(tab, eng)
            fn = f"temp_{tab}.csv"
            df.to_csv(fn, index=False, sep=';')
            
            if folder_id:
                srv, msg = autenticar_google_drive()
                if srv:
                    upload_para_drive(srv, fn, fn, folder_id)
                    os.remove(fn)
                    status.update(label="Sucesso! ✅", state="complete")
                else: status.update(state="error", label=msg)
            else: status.error("Sem ID Pasta")
        except Exception as e: status.error(f"Erro: {e}")

# BOTÃO 3: TOTAL
with col_full:
    if st.button("🚀 MIGRAÇÃO TOTAL", type="primary", use_container_width=True):
        t_s, d_s, m_s, h_s, p_s, db_s, u_s, pw_s = src_data
        t_d, d_d, m_d, h_d, p_d, db_d, u_d, pw_d = dst_data
        
        if not (db_s and db_d and tab): st.error("Dados incompletos"); st.stop()
        
        status = st.status("Migrando...", expanded=True)
        try:
            url_s = montar_url_universal(t_s, d_s, m_s, h_s, p_s, db_s, u_s, pw_s)
            url_d = montar_url_universal(t_d, d_d, m_d, h_d, p_d, db_d, u_d, pw_d)
            
            _, _, eng_s = testar_conexao(url_s)
            _, err_d, eng_d = testar_conexao(url_d)
            if err_d: raise Exception(f"Destino: {err_d}")
            
            status.write("📖 Lendo origem...")
            df = pd.read_sql_table(tab, eng_s)
            if df.empty: st.warning("Vazia"); st.stop()
            
            # Backup Drive Silencioso
            if folder_id:
                try:
                    fn = f"bkp_full_{tab}.csv"
                    df.to_csv(fn, index=False, sep=';')
                    srv, _ = autenticar_google_drive()
                    if srv: upload_para_drive(srv, fn, fn, folder_id)
                    os.remove(fn)
                    status.write("☁️ Drive OK")
                except: pass

            # Lógica Inteligente
            df_final = df
            if "Inteligente" in modo and pk:
                status.write("🕵️ Verificando duplicados...")
                try:
                    ids = pd.read_sql_table(tab, eng_d, columns=[pk])
                    existentes = set(ids[pk].tolist())
                    df_final = df[~df[pk].isin(existentes)]
                except: pass

            metodo = "replace" if "Replace" in modo else "append"
            if not df_final.empty:
                status.write(f"🚀 Inserindo {len(df_final)} linhas...")
                df_final.to_sql(tab, eng_d, if_exists=metodo, index=False, chunksize=1000)
                status.update(label="Concluído! 🏁", state="complete")
                st.balloons()
            else: status.update(label="Nada novo.", state="complete")
            
        except Exception as e: status.update(state="error", label=str(e))