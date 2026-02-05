import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from datetime import datetime
import os
import json
from sqlalchemy import text

# --- BIBLIOTECAS GOOGLE OAUTH ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Migrador SQL", layout="wide", page_icon="🧰")
st.title("🧰 Migrador SQL")

# --- CONFIGURAÇÃO DE CAMINHOS ---
PASTA_CREDENCIAIS = "Credencials"
ID_PADRAO_DRIVE = "1M2OZgy3MV8JcYyvMngVE5ZDEHChwmCR2" 
SCOPES = ['https://www.googleapis.com/auth/drive.file']

if not os.path.exists(PASTA_CREDENCIAIS):
    os.makedirs(PASTA_CREDENCIAIS)

ARQUIVO_CLIENT_SECRET = os.path.join(PASTA_CREDENCIAIS, "client_secret.json")
ARQUIVO_TOKEN = os.path.join(PASTA_CREDENCIAIS, "token.json")

# --- FUNÇÕES GOOGLE ---
def autenticar_google_drive():
    creds = None
    if os.path.exists(ARQUIVO_TOKEN):
        try: creds = Credentials.from_authorized_user_file(ARQUIVO_TOKEN, SCOPES)
        except: pass
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try: creds.refresh(Request())
            except: creds = None
        if not creds:
            if not os.path.exists(ARQUIVO_CLIENT_SECRET): return None, "Falta client_secret.json"
            flow = InstalledAppFlow.from_client_secrets_file(ARQUIVO_CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=8090)
            with open(ARQUIVO_TOKEN, 'w') as token: token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds), "OK"

def upload_para_drive(service, caminho_arquivo, nome_arquivo, id_pasta):
    try:
        file_metadata = {'name': nome_arquivo, 'parents': [id_pasta]}
        media = MediaFileUpload(caminho_arquivo, mimetype='text/csv')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True, file.get('id')
    except Exception as e: return False, str(e)

# --- FUNÇÕES DE BANCO DE DADOS (UNIVERSAL) ---

DRIVERS_SQL_SERVER = [
    "ODBC Driver 17 for SQL Server", 
    "ODBC Driver 18 for SQL Server", 
    "ODBC Driver 13 for SQL Server", 
    "SQL Server",                    
    "Outro (Digitar Manualmente)"
]

DEFAULT_PORTS = {
    "SQL Server": "1433",
    "MySQL": "3306",
    "PostgreSQL": "5432"
}

# --- ATUALIZAÇÃO DA FUNÇÃO DE URL ---
def montar_url_universal(tipo, driver_sql, manual_sql, host, port, db, user, pwd):
    """
    Monta a URL de forma segura, tratando senhas com caracteres especiais.
    """
    port = int(port) if port and port.isnumeric() else None # Garante que a porta é número

    if tipo == "SQL Server":
        driver_final = manual_sql if driver_sql == "Outro (Digitar Manualmente)" else driver_sql
        # SQL Server exige a string ODBC exata
        conn_str = f"DRIVER={{{driver_final}}};SERVER={host},{port};DATABASE={db};UID={user};PWD={pwd};TrustServerCertificate=yes;"
        return URL.create("mssql+pyodbc", query={"odbc_connect": conn_str})
    
    elif tipo == "MySQL":
        # Usa URL.create para escapar automaticamente senhas com @ ou :
        return URL.create(
            "mysql+pymysql",
            username=user,
            password=pwd,
            host=host,
            port=port or 3306,
            database=db
        )
    
    elif tipo == "PostgreSQL":
        # Usa URL.create para escapar automaticamente senhas com @ ou :
        return URL.create(
            "postgresql+psycopg2",
            username=user,
            password=pwd,
            host=host,
            port=port or 5432,
            database=db
        )
    
    return None

def render_inputs_banco(titulo, k):
    st.subheader(titulo)
    
    # 1. Tipo e Driver
    tipo = st.selectbox("Tecnologia", ["SQL Server", "MySQL", "PostgreSQL"], key=f"{k}_type")
    
    driver_sql = None
    manual_sql = None
    if tipo == "SQL Server":
        driver_sql = st.selectbox("Versão Driver", DRIVERS_SQL_SERVER, key=f"{k}_drv")
        if driver_sql and "Outro" in driver_sql: 
            manual_sql = st.text_input("Driver Manual", key=f"{k}_man")
    
    # 2. Host e Credenciais
    c_h, c_p = st.columns([3, 1])
    with c_h: host = st.text_input("Host / IP", "localhost", key=f"{k}_host")
    with c_p: port = st.text_input("Porta", DEFAULT_PORTS[tipo], key=f"{k}_port")
    
    c_u, c_pass = st.columns(2)
    with c_u: user = st.text_input("Usuário", "sa" if tipo == "SQL Server" else "root", key=f"{k}_user")
    with c_pass: pwd = st.text_input("Senha", type="password", key=f"{k}_pwd")
    
    # --- LÓGICA DE LISTAGEM INTELIGENTE ---
    # Cria uma chave única para guardar a lista na memória do Streamlit
    chave_lista = f"lista_bancos_{k}"
    if chave_lista not in st.session_state:
        st.session_state[chave_lista] = []

    # Botão para listar
    if st.button(f"🔍 Listar Bancos no Servidor", key=f"btn_list_{k}", use_container_width=True):
        if host and user:
            with st.spinner("Buscando lista de bancos..."):
                lista = listar_bancos_disponiveis(tipo, driver_sql, manual_sql, host, port, user, pwd)
                if lista:
                    st.session_state[chave_lista] = lista
                    st.toast(f"{len(lista)} bancos encontrados!", icon="✅")
                else:
                    st.error("Nenhum banco encontrado ou erro de conexão.")
        else:
            st.warning("Preencha Host e Usuário para listar.")

    # Se tivermos uma lista na memória, mostramos o Selectbox
    if st.session_state[chave_lista]:
        db = st.selectbox("Selecione o Banco", st.session_state[chave_lista], key=f"{k}_db_select")
        # Opção para limpar e digitar manualmente se o usuário quiser
        if st.button("Digitar manualmente", key=f"btn_clear_{k}"):
            st.session_state[chave_lista] = []
            st.rerun()
    else:
        # Se não tiver lista, mostra campo de texto normal
        db = st.text_input("Nome do Banco (Schema)", key=f"{k}_db_manual", help="Clique na lupa acima para listar automaticamente")

    return tipo, driver_sql, manual_sql, host, port, db, user, pwd

def testar_conexao(url):
    try:
        eng = create_engine(url)
        with eng.connect() as c: return True, None, eng
    except Exception as e: return False, str(e), None

# --- SIDEBAR (Status Google) ---
# --- SIDEBAR (Status Google) ---
with st.sidebar:
    st.header("☁️ Status Google Drive")
    
    # MUDANÇA AQUI: Definimos a variável direto, sem input visual
    folder_id = ID_PADRAO_DRIVE 
    
    # Mostra apenas um status discreto se o ID está configurado no código
    if folder_id:
        st.caption(f"📁 Pasta Destino Configurada")
    else:
        st.error("⚠️ ID da Pasta não configurado no código!")

    if os.path.exists(ARQUIVO_TOKEN):
        st.success("✅ Login Salvo")
        
        # Cria colunas para os botões ficarem lado a lado
        col_test, col_logout = st.columns(2)
        
        with col_test:
            if st.button("📡 Testar API"):
                with st.spinner("Validando..."):
                    try:
                        s, _ = autenticar_google_drive()
                        if s: 
                            u = s.about().get(fields="user").execute()
                            st.toast(f"Token Válido! Olá {u['user']['displayName']}", icon="✅")
                    except: 
                        st.error("Erro no token")
        
        with col_logout:
            if st.button("🚪 Sair"):
                try:
                    os.remove(ARQUIVO_TOKEN)
                    st.rerun() 
                except:
                    st.error("Erro ao sair")

    else: 
        st.info("Login automático na execução.")

# Listar bancos disponíveis (para dropdown) - Pode ser usado para pré-carregar opções de banco

def listar_bancos_disponiveis(tipo, driver, manual, host, port, user, pwd):
    """
    Versão DEBUG: Mostra o erro na tela se falhar.
    """
    # Define o banco de sistema para conexão inicial
    db_sistema = "master" if tipo == "SQL Server" else "postgres" if tipo == "PostgreSQL" else ""
    
    # MySQL conecta sem database especificado para listar
    if tipo == "MySQL": db_sistema = ""

    try:
        # Monta URL apontando para o banco de sistema
        url = montar_url_universal(tipo, driver, manual, host, port, db_sistema, user, pwd)
        eng = create_engine(url)
        
        # Tenta conectar (Aqui é onde geralmente falha)
        with eng.connect() as conn:
            if tipo == "SQL Server":
                # Query padrão para SQL Server
                q = "SELECT name FROM sys.databases WHERE name NOT IN ('master','tempdb','model','msdb')"
                return [r[0] for r in conn.execute(text(q))]
            
            elif tipo == "PostgreSQL":
                q = "SELECT datname FROM pg_database WHERE datistemplate = false"
                return [r[0] for r in conn.execute(text(q))]
            
            elif tipo == "MySQL":
                q = "SHOW DATABASES"
                # Filtra bancos de sistema do MySQL
                bancos_sistema = ['information_schema', 'mysql', 'performance_schema', 'sys']
                return [r[0] for r in conn.execute(text(q)) if r[0] not in bancos_sistema]

    except Exception as e:
        # AQUI ESTÁ A MUDANÇA: Mostra o erro técnico na interface
        st.error(f"Erro ao listar bancos: {e}")
        return []

# --- PAINEL PRINCIPAL DE CONFIGURAÇÃO ---
col1, col2 = st.columns(2)

# --- PAINEL PRINCIPAL DE CONFIGURAÇÃO (ATUALIZADO) ---
col1, col2 = st.columns(2)

# --- ORIGEM ---
with col1:
    src_data = render_inputs_banco("1. Origem (De onde vem)", "src")
    
    # Botão com feedback visual
    if st.button("🔌 Validar Origem", key="btn_src", use_container_width=True):
        t, d, m, h, p, db, u, pw = src_data
        
        if h and db and u: # Verifica se Host, Banco e Usuário estão preenchidos
            with st.spinner(f"Testando conexão com {t}..."):
                url = montar_url_universal(t, d, m, h, p, db, u, pw)
                ok, err, _ = testar_conexao(url)
                
                if ok: 
                    st.success(f"✅ Conexão {t}: SUCESSO!")
                else: 
                    st.error(f"❌ Falha ao conectar:")
                    st.code(err, language="text") # Mostra o erro técnico formatado
        else:
            st.warning("⚠️ Preencha Host, Banco e Usuário antes de testar.")

# --- DESTINO ---
with col2:
    dst_data = render_inputs_banco("2. Destino (Para onde vai)", "dst")
    
    # Botão com feedback visual
    if st.button("🔌 Validar Destino", key="btn_dst", use_container_width=True):
        t, d, m, h, p, db, u, pw = dst_data
        
        if h and db and u:
            with st.spinner(f"Testando conexão com {t}..."):
                url = montar_url_universal(t, d, m, h, p, db, u, pw)
                ok, err, _ = testar_conexao(url)
                
                if ok: 
                    st.success(f"✅ Conexão {t}: SUCESSO!")
                else: 
                    st.error(f"❌ Falha ao conectar:")
                    st.code(err, language="text")
        else:
            st.warning("⚠️ Preencha Host, Banco e Usuário antes de testar.")

st.markdown("---")

# --- PARÂMETROS ---
st.subheader("🛠️ Configuração da Migração")
c1, c2, c3 = st.columns(3)
with c1: tab = st.text_input("Nome da Tabela")
with c2: pk = st.text_input("Coluna ID (Primary Key)")
with c3: modo = st.selectbox("Estratégia", ["Inteligente (Filtrar Duplicados)", "Append (Adicionar)", "Replace (Substituir)"])

st.markdown("---")

# --- BOTÕES DE AÇÃO (SEPARADOS) ---
st.subheader("▶️ Painel de Execução")
col_bkp_local, col_bkp_cloud, col_full = st.columns([1, 1, 1.5])

# === BOTÃO 1: APENAS BACKUP LOCAL ===
with col_bkp_local:
    if st.button("💾 Backup Local (CSV)", use_container_width=True):
        if not tab: st.error("Informe a tabela."); st.stop()
        
        # Pega dados APENAS da origem
        t, d, m, h, p, db, u, pw = src_data
        url = montar_url_universal(t, d, m, h, p, db, u, pw)
        
        try:
            ok, err, eng = testar_conexao(url)
            if ok:
                df = pd.read_sql_table(tab, eng)
                fn = f"backup_{tab}_local.csv"
                df.to_csv(fn, index=False, sep=';')
                st.success(f"✅ Arquivo Gerado: {fn}")
                with open(fn, "rb") as f: st.download_button("Baixar Agora", f, file_name=fn)
            else:
                st.error(f"Erro Conexão Origem: {err}")
        except Exception as e: st.error(f"Erro: {e}")

# === BOTÃO 2: BACKUP NUVEM (SEM MIGRAÇÃO) ===
with col_bkp_cloud:
    if st.button("☁️ Backup Nuvem (Drive)", use_container_width=True):
        if not tab: st.error("Informe a tabela."); st.stop()
        
        t, d, m, h, p, db, u, pw = src_data
        url = montar_url_universal(t, d, m, h, p, db, u, pw)
        
        status = st.status("Iniciando Backup Nuvem...", expanded=True)
        try:
            # 1. Leitura
            status.write(f"📖 Lendo {t}...")
            ok, err, eng = testar_conexao(url)
            if not ok: status.write("❌ Erro conexão"); st.stop()
            
            df = pd.read_sql_table(tab, eng)
            fn = f"backup_{tab}_cloud_{datetime.now().strftime('%H%M')}.csv"
            df.to_csv(fn, index=False, sep=';')
            status.write("💾 CSV Temporário criado.")
            
            # 2. Upload
            if folder_id:
                status.write("☁️ Autenticando Google...")
                srv, msg = autenticar_google_drive()
                if srv:
                    status.write("📤 Enviando...")
                    ok_up, res_up = upload_para_drive(srv, fn, fn, folder_id)
                    if ok_up:
                        os.remove(fn)
                        status.update(label="Sucesso Nuvem! ✅", state="complete")
                        st.success(f"Upload OK! ID: {res_up}")
                    else: st.error(res_up)
                else: st.error(msg)
            else: st.error("Sem ID da pasta.")
        except Exception as e: st.error(f"Erro: {e}")

# === BOTÃO 3: MIGRAÇÃO COMPLETA ===
with col_full:
    if st.button("🚀 MIGRAÇÃO TOTAL (Bancos + Drive)", type="primary", use_container_width=True):
        # Validação Geral
        t_s, d_s, m_s, h_s, p_s, db_s, u_s, pw_s = src_data
        t_d, d_d, m_d, h_d, p_d, db_d, u_d, pw_d = dst_data
        
        if not (db_s and db_d and tab): st.error("Preencha Origem, Destino e Tabela."); st.stop()
        
        status = st.status("Executando Migração Completa...", expanded=True)
        
        try:
            # 1. Conexões
            url_s = montar_url_universal(t_s, d_s, m_s, h_s, p_s, db_s, u_s, pw_s)
            url_d = montar_url_universal(t_d, d_d, m_d, h_d, p_d, db_d, u_d, pw_d)
            
            _, _, eng_s = testar_conexao(url_s)
            _, err_d, eng_d = testar_conexao(url_d)
            if err_d: raise Exception(f"Erro Destino: {err_d}")
            
            # 2. Leitura & Backup Nuvem
            status.write(f"📖 Lendo origem ({t_s})...")
            df = pd.read_sql_table(tab, eng_s)
            if df.empty: st.warning("Origem vazia"); st.stop()
            
            # Backup Nuvem Silencioso (Faz parte do processo total)
            if folder_id:
                try:
                    fn = f"bkp_full_{tab}.csv"
                    df.to_csv(fn, index=False, sep=';')
                    srv, _ = autenticar_google_drive()
                    if srv: upload_para_drive(srv, fn, fn, folder_id)
                    os.remove(fn)
                    status.write("☁️ Backup Nuvem OK.")
                except: status.write("⚠️ Falha no Drive (Ignorado).")
            
            # 3. Lógica de Migração (Inteligente)
            df_final = df
            if "Inteligente" in modo and pk:
                status.write("🕵️ Filtrando duplicados...")
                try:
                    ids = pd.read_sql_table(tab, eng_d, columns=[pk])
                    existentes = set(ids[pk].tolist())
                    df_final = df[~df[pk].isin(existentes)]
                except: pass
            
            # 4. Escrita
            metodo = "replace" if "Replace" in modo else "append"
            if not df_final.empty:
                status.write(f"🚀 Gravando em {t_d}...")
                df_final.to_sql(tab, eng_d, if_exists=metodo, index=False, chunksize=1000)
                status.update(label="Sucesso Total! 🏁", state="complete")
                st.balloons()
            else:
                status.update(label="Concluído (Nada a inserir)", state="complete")
                
        except Exception as e: st.error(f"Erro Crítico: {e}")