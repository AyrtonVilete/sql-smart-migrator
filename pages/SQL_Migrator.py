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

# ==========================================
# 1. CONFIGURAÇÃO E SEGURANÇA
# ==========================================
st.set_page_config(page_title="Migrador SQL - Cloud v3", layout="wide", page_icon="🧰")

if not st.session_state.get('autenticado'):
    st.error("🚫 Acesso negado! Por favor, faça login no Portal primeiro.")
    st.stop()

if not st.session_state.get('p1', False):
    st.warning("⚠️ Você não tem permissão para acessar o Migrador.")
    st.stop()

# Inicializa as variáveis de sessão essenciais
if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []

# Variáveis Globais
PASTA_CREDENCIAIS = "Credencials"
ARQUIVO_TOKEN = os.path.join(PASTA_CREDENCIAIS, "token.json") if os.path.exists(PASTA_CREDENCIAIS) else "token.json"
ID_PADRAO_DRIVE = "1M2OZgy3MV8JcYyvMngVE5ZDEHChwmCR2" 
SCOPES = ['https://www.googleapis.com/auth/drive.file']
DRIVERS_SQL_SERVER = ["ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server", "SQL Server"]
DEFAULT_PORTS = {"SQL Server": "1433", "MySQL": "3306", "PostgreSQL": "5432"}

# ==========================================
# 2. FUNÇÕES DE BACKEND (BANCO, IA, REDE)
# ==========================================
def testar_porta_rede(host, port, timeout=2):
    try:
        port = int(port)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

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
        st.error(f"Erro de conexão SQL: {e}") 
        return None 

def consultar_ia_render(prompt_usuario, historico):
    try:
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
        return f"🚨 Erro Crítico de Comunicação: {e}"

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

    if st.button(f"🔍 Listar Bancos", key=f"btn_l_{k}", use_container_width=True):
        with st.spinner("Conectando e buscando bancos..."):
            resultado = listar_bancos_disponiveis(tipo, drv, host, port, user, pwd)
            
            if resultado is not None:
                st.session_state[chave_lista] = resultado
                st.success(f"{len(resultado)} bancos encontrados!")
            else:
                st.session_state[chave_lista] = []
                st.markdown("---")
                st.warning("⚠️ Iniciando diagnóstico de rede automático...")
                porta_aberta = testar_porta_rede(host, port)
                
                if porta_aberta:
                    st.info("✅ **Diagnóstico:** A porta está ABERTA e acessível.\nO problema provavelmente é **Usuário/Senha incorretos** ou o driver ODBC.")
                else:
                    st.error(f"⛔ **Diagnóstico Crítico:** A porta {port} está FECHADA ou INACESSÍVEL.\nO Firewall bloqueou a conexão.")
                    if tipo == "SQL Server":
                        with st.expander(f"💡 Solução Rápida", expanded=True):
                            st.code(f'New-NetFirewallRule -DisplayName "SQL Server Port {port}" -Direction Inbound -LocalPort {port} -Protocol TCP -Action Allow', language="powershell")

    if st.session_state[chave_lista]:
        db = st.selectbox("Selecione o Banco", st.session_state[chave_lista], key=f"{k}_db_s")
    else:
        db = st.text_input("Nome do Banco (Manual)", key=f"{k}_db_m")

    return tipo, drv, host, port, db, user, pwd

# ==========================================
# 3. INTERFACE DA SIDEBAR (MENU ESQUERDO)
# ==========================================
def desenhar_sidebar():
    with st.sidebar:
        st.header("☁️ Google Drive")
        if st.button("📡 Testar Conexão Google"):
            srv, msg = autenticar_google_drive()
            if srv: 
                user = srv.about().get(fields="user").execute()
                st.success(f"Logado como: {user['user']['displayName']}")
            else: st.error(msg)
        
        st.divider()
        
        # Agente de IA na Sidebar
        st.header("🤖 Assistente de IA")
        st.caption("Ajuda rápida com scripts e análises.")

        # Container isolado para o chat não estourar a tela
        caixa_chat = st.container(height=350)
        with caixa_chat:
            for msg in st.session_state.mensagens_chat:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # Input do chat fica fixo abaixo da caixa
        if prompt := st.chat_input("Dúvidas com SQL?", key="chat_sidebar"):
            # 1. Salva a mensagem do usuário
            st.session_state.mensagens_chat.append({"role": "user", "content": prompt})
            with caixa_chat:
                with st.chat_message("user"):
                    st.markdown(prompt)
                # 2. Mostra carregamento e chama API
                with st.chat_message("assistant"):
                    with st.spinner("Consultando nuvem..."):
                        resposta_texto = consultar_ia_render(prompt, st.session_state.mensagens_chat[:-1])
                        st.markdown(resposta_texto)
            # 3. Salva a resposta da IA
            st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_texto})

        st.divider()
        if st.button("⬅️ Voltar ao Menu Principal", use_container_width=True):
            st.switch_page("Login.py")

        st.caption("v4.0 - Cloud Edition + IA Integrada")

# ==========================================
# 4. INTERFACE DO PAINEL PRINCIPAL (CENTRO)
# ==========================================
def desenhar_painel_principal():
    st.title("🧰 SQL Smart Migrator (v3 Cloud)")
    
    col_src, col_dst = st.columns(2)
    with col_src: src_data = render_inputs("1. Origem ", "src")
    with col_dst: dst_data = render_inputs("2. Destino ", "dst")

    st.divider()
    st.subheader("🛠️ Configuração da Migração")
    c1, c2, c3 = st.columns(3)
    with c1: tabela = st.text_input("Nome da Tabela")
    with c2: pk = st.text_input("Coluna ID (Para Inteligente)")
    with c3: modo = st.selectbox("Estratégia", ["Inteligente (Filtrar Existentes)", "Append (Adicionar)", "Replace (Substituir)"])

    st.markdown("---")

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        if st.button("💾 Backup Local", use_container_width=True):
            if not tabela: st.error("Defina a tabela.")
            else:
                t, d, h, p, db, u, pw = src_data
                url = montar_url_universal(t, d, h, p, db, u, pw)
                ok, err, eng = testar_conexao(url)
                if ok:
                    df = pd.read_sql_table(tabela, eng)
                    csv = df.to_csv(index=False, sep=';').encode('utf-8')
                    st.download_button("Baixar CSV", csv, f"bkp_{tabela}.csv", "text/csv")
                else: st.error(err)

    with col_b:
        if st.button("☁️ Backup Drive", use_container_width=True):
            if not tabela: st.error("Defina a tabela.")
            else:
                with st.spinner("Fazendo upload..."):
                    t, d, h, p, db, u, pw = src_data
                    url = montar_url_universal(t, d, h, p, db, u, pw)
                    ok, err, eng = testar_conexao(url)
                    if ok:
                        df = pd.read_sql_table(tabela, eng)
                        fn = f"cloud_bkp_{tabela}.csv"
                        df.to_csv(fn, index=False, sep=';')
                        srv, msg = autenticar_google_drive()
                        if srv:
                            ok_up, res = upload_para_drive(srv, fn, fn, ID_PADRAO_DRIVE)
                            if ok_up: st.success(f"Upload OK! ID: {res}")
                            else: st.error(res)
                            if os.path.exists(fn): os.remove(fn)
                        else: st.error(msg)

    with col_c:
        if st.button("🚀 Iniciar Migração", type="primary", use_container_width=True):
            if not (tabela and src_data[4] and dst_data[4]): st.error("Preencha todos os campos.")
            else:
                with st.status("Executando migração...") as s:
                    url_s = montar_url_universal(*src_data)
                    url_d = montar_url_universal(*dst_data)
                    _, _, eng_s = testar_conexao(url_s)
                    _, _, eng_d = testar_conexao(url_d)
                    
                    df = pd.read_sql_table(tabela, eng_s)
                    s.write(f"📖 {len(df)} registros extraídos.")
                    
                    if "Inteligente" in modo and pk:
                        try:
                            existentes = pd.read_sql(f"SELECT {pk} FROM {tabela}", eng_d)[pk].tolist()
                            df = df[~df[pk].isin(existentes)]
                            s.write(f"🕵️ Filtrados: {len(df)} novos para inserir.")
                        except: s.write("⚠️ Tabela destino não existe, ignorando filtro.")

                    metodo = "replace" if "Replace" in modo else "append"
                    df.to_sql(tabela, eng_d, if_exists=metodo, index=False, chunksize=1000)
                    s.update(label="Migração Concluída!", state="complete")
                    st.balloons()

# ==========================================
# 5. ORQUESTRADOR DE EXECUÇÃO
# ==========================================
# Chama as funções na ordem correta, garantindo que o layout nunca quebre
desenhar_sidebar()
desenhar_painel_principal()