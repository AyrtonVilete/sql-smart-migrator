import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import URL
from datetime import datetime
import os
import pickle
import socket 
import requests
import io

# --- BIBLIOTECAS GOOGLE OAUTH ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# ==========================================
# 1. CONFIGURAÇÃO 
# ==========================================
st.set_page_config(page_title="V-Nexus SQL Smart Migrator", layout="wide", page_icon="🧰")

# Inicializa as variáveis de sessão essenciais
if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []

# --- NOVA CONFIGURAÇÃO CLOUD (DIRETO GOOGLE DRIVE) ---
CREDENTIALS_PATH = os.path.join('credentials', 'credentials.json')
TOKEN_PATH = os.path.join('credentials', 'token.pickle')

# Escopo necessário para ver/gerenciar arquivos no Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file']
ID_PADRAO_DRIVE = "1M2OZgy3MV8JcYyvMngVE5ZDEHChwmCR2" 

# Variáveis Auxiliares de Banco
DRIVERS_SQL_SERVER = ["ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server", "SQL Server"]
DEFAULT_PORTS = {"SQL Server": "1433", "MySQL": "3306", "PostgreSQL": "5432"}

# ==========================================
# 2. FUNÇÕES DE BACKEND (BANCO, IA, REDE, CLOUD)
# ==========================================

def testar_porta_rede(host, port, timeout=2):
    try:
        port = int(port)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

# --- FUNÇÕES DE AUTENTICAÇÃO E ENVIO DIRETO PARA O DRIVE ---
def validate_google_auth():
    """Valida ou cria o token de acesso do Google Drive localmente."""
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                return False, f"Erro: Arquivo não encontrado em {CREDENTIALS_PATH}!"
            
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=8080, prompt='select_account')
            
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('drive', 'v3', credentials=creds)
        about = service.about().get(fields="user").execute()
        user_email = about['user']['emailAddress']
        return True, f"Google Drive Conectado! ({user_email})"
    except Exception as e:
        return False, f"Falha na comunicação: {str(e)}"

def fazer_upload_direto_google(df, nome_tabela):
    """
    Converte o DataFrame em CSV e envia direto para o Google Drive.
    """
    creds = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        return False, "Credenciais inválidas. Por favor, valide o acesso na Sidebar primeiro."

    try:
        service = build('drive', 'v3', credentials=creds)

        # 1. Converter DataFrame para CSV em memória
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8')
        output.seek(0)
        
        # 2. Configurar metadados do arquivo (usando a variável global de ID que você definiu)
        file_metadata = {
            'name': f'backup_{nome_tabela}.csv',
            'mimeType': 'text/csv',
            'parents': [ID_PADRAO_DRIVE]  
        }

        # 3. Preparar o upload
        media = MediaIoBaseUpload(
            io.BytesIO(output.getvalue().encode('utf-8')), 
            mimetype='text/csv', 
            resumable=True
        )

        # 4. Executar o upload
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        return True, file.get('id')

    except Exception as e:
        return False, str(e)

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

def listar_tabelas(eng):
    try:
        insp = inspect(eng)
        return insp.get_table_names()
    except Exception as e:
        return []
    
def obter_chave_primaria(eng, nome_tabela):
    """Busca a chave primária da tabela automaticamente no banco de dados."""
    try:
        insp = inspect(eng)
        pk_info = insp.get_pk_constraint(nome_tabela)
        
        # Verifica se encontrou a PK e se ela tem colunas
        if pk_info and 'constrained_columns' in pk_info and len(pk_info['constrained_columns']) > 0:
            return pk_info['constrained_columns'][0]
    except Exception:
        pass
    return ""

def obter_schema_banco(eng):
    """Lê as tabelas e colunas do banco para criar o 'Mapa' para a IA."""
    try:
        insp = inspect(eng)
        schema_texto = "Estrutura do Banco de Dados:\n"
        
        tabelas = insp.get_table_names() 
        
        for tabela in tabelas:
            colunas = insp.get_columns(tabela)
            detalhes_colunas = [f"{c['name']} ({str(c['type'])})" for c in colunas]
            schema_texto += f"- Tabela '{tabela}': {', '.join(detalhes_colunas)}\n"
            
        return schema_texto
    except Exception as e:
        return f"Erro ao ler o schema do banco: {e}"

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
                    st.info("✅ **Diagnóstico:** A porta está ABERTA e acessível.\nO problema provavelmente é **Usuário/Senha incorretos**.")
                else:
                    st.error(f"⛔ **Diagnóstico Crítico:** A porta {port} está FECHADA.")

    if st.session_state[chave_lista]:
        db = st.selectbox("Selecione o Banco", st.session_state[chave_lista], key=f"{k}_db_s")
    else:
        db = st.text_input("Nome do Banco (Manual)", key=f"{k}_db_m")

    return tipo, drv, host, port, db, user, pwd

def aplicar_transformacoes(df, config_limpeza):
    if df is None or df.empty:
        return df
    df_tratado = df.copy()
    if config_limpeza.get("remover_nulos"):
        df_tratado = df_tratado.dropna()
    if config_limpeza.get("preencher_nulos"):
        valor = config_limpeza.get("valor_nulo", "Não Informado")
        df_tratado = df_tratado.fillna(valor)
    if config_limpeza.get("remover_duplicadas"):
        df_tratado = df_tratado.drop_duplicates()
    colunas_mask = config_limpeza.get("colunas_mascarar", [])
    for col in colunas_mask:
        if col in df_tratado.columns:
            df_tratado[col] = df_tratado[col].astype(str).apply(
                lambda x: x[:3] + "***" if x and x.lower() not in ['nan', 'none'] else x
            )
    return df_tratado

# ==========================================
# 3. INTERFACE DA SIDEBAR (MENU ESQUERDO)
# ==========================================
def desenhar_sidebar():
    with st.sidebar:
        st.header("☁️ V-Nexus Cloud")
        
        if st.button("🔑 Autenticar Conta Google", use_container_width=True):
            with st.spinner("Validando acesso ao Drive..."):
                sucesso, mensagem = validate_google_auth()
                if sucesso:
                    st.success(mensagem)
                else:
                    st.error(mensagem)
        
        st.divider()
        
        st.header("🤖 Assistente de IA")
        st.caption("Ajuda rápida com scripts e análises.")

        caixa_chat = st.container(height=350)
        with caixa_chat:
            for msg in st.session_state.mensagens_chat:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        if prompt := st.chat_input("Dúvidas com SQL?", key="chat_sidebar"):
            st.session_state.mensagens_chat.append({"role": "user", "content": prompt})
            with caixa_chat:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Consultando IA..."):
                        resposta_texto = consultar_ia_render(prompt, st.session_state.mensagens_chat[:-1])
                        st.markdown(resposta_texto)

            st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_texto})

        st.divider()
        if st.button("⬅️ Voltar ao Portal", use_container_width=True):
            st.switch_page("Login.py") 

        st.caption("v4.0 - Smart Migrator")

# ==========================================
# 4. INTERFACE DO PAINEL PRINCIPAL (CENTRO)
# ==========================================
def desenhar_painel_principal():
    st.title("🧰 SQL Smart Migrator")
    
    col_src, col_dst = st.columns(2)
    with col_src: src_data = render_inputs("1. Origem ", "src")
    with col_dst: dst_data = render_inputs("2. Destino ", "dst")

    st.divider()
    st.subheader("🛠️ Configuração e Extração")
    
    # --- SELETOR DE MODO ---
    tipo_migracao = st.radio(
        "Selecione o Modo de Operação:", 
        ["🚀 Modo Básico (Tabela Inteira)", "🔬 Modo Avançado (Query SQL Customizada)"],
        horizontal=True
    )

    st.markdown("---")
    
    # Variáveis que serão usadas pelos botões finais, independente do modo
    tabela_destino = ""
    pk = ""
    modo = ""
    query_sql = ""

    # --- LÓGICA DO MODO BÁSICO ---
    if "Básico" in tipo_migracao:
        st.info("💡 **Modo Básico:** Copia todos os dados de uma tabela diretamente para o destino.")
        
        tabelas_disponiveis = []
        eng_origem_temp = None
        if src_data[4]:
            url_s = montar_url_universal(*src_data)
            ok_s, _, eng_origem_temp = testar_conexao(url_s)
            if ok_s:
                tabelas_disponiveis = listar_tabelas(eng_origem_temp)

        usa_lista = st.checkbox("📋 Selecionar tabela da lista (Desmarque para digitar manualmente)", value=True)

        c1, c2, c3 = st.columns(3)
        
        tabela_origem = ""
        
        with c1: 
            if usa_lista:
                if tabelas_disponiveis:
                    tabela_origem = st.selectbox("Tabela de Origem", tabelas_disponiveis)
                else:
                    st.selectbox("Tabela de Origem", ["⚠️ Conecte o banco de origem..."], disabled=True)
            else:
                tabela_origem = st.text_input("Tabela de Origem (Manual)")
                
            tabela_destino = st.text_input("Tabela no Destino", value=tabela_origem)
            
        # --- BUSCA AUTOMÁTICA DA CHAVE PRIMÁRIA ---
        pk_automatica = ""
        if tabela_origem and eng_origem_temp:
            pk_automatica = obter_chave_primaria(eng_origem_temp, tabela_origem)
            
        with c2: 
            pk = st.text_input(
                "Coluna ID (Para Inteligente)", 
                value=pk_automatica, 
                disabled=True, 
                help="A Chave Primária é detectada automaticamente do banco de dados."
            )
            
            if tabela_origem and not pk_automatica:
                st.caption("⚠️ Nenhuma PK detectada nesta tabela.")
            
        with c3: 
            modo = st.selectbox("Estratégia de Migração", ["Inteligente (Filtrar Existentes)", "Append (Adicionar)", "Replace (Substituir)"])

        st.write("") 
        
        if tabela_origem and eng_origem_temp:
            col_vazia_esq, col_btn, col_vazia_dir = st.columns([1, 2, 1])
            
            with col_btn:
                btn_preview = st.button("👁️ Visualizar Dados da Tabela", use_container_width=True)
                
            if btn_preview:
                try:
                    with st.spinner(f"Carregando preview de {tabela_origem}..."):
                        query_prev = f"SELECT TOP 50 * FROM {tabela_origem}" if src_data[0] == "SQL Server" else f"SELECT * FROM {tabela_origem} LIMIT 50"
                        df_preview = pd.read_sql(query_prev, eng_origem_temp)
                        
                        st.success("✅ Preview gerado com sucesso!")
                        st.dataframe(df_preview, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao gerar preview: {e}")

    # --- LÓGICA DO MODO AVANÇADO ---
    else:
        st.info("💡 **Modo Avançado:** Escreva um SELECT para filtrar, juntar (JOIN) ou renomear colunas na origem. Apenas o resultado será migrado/salvo.")
        query_sql = st.text_area("Sua Query (SELECT ...)", placeholder="Ex: SELECT id, nome, email FROM clientes WHERE status = 'ativo'")
        
        if st.button("👁️ Visualizar Dados (Preview)", use_container_width=True):
            if query_sql and src_data[4]: 
                try:
                    url_s = montar_url_universal(*src_data)
                    ok, err, eng_s = testar_conexao(url_s)
                    if ok:
                        with st.spinner("Executando query na origem..."):
                            df_preview = pd.read_sql(query_sql, eng_s)
                            st.success(f"✅ Sucesso! A query retornou {len(df_preview)} linhas.")
                            st.dataframe(df_preview.head(50), use_container_width=True)
                    else:
                        st.error(f"Erro de conexão na origem: {err}")
                except Exception as e:
                    st.error(f"Erro ao executar a query: {e}")
            else:
                st.warning("Preencha as credenciais da Origem e escreva a Query primeiro.")
        
        c1, c2, c3 = st.columns(3)
        with c1: tabela_destino = st.text_input("Nome da Tabela de DESTINO")
        with c2: pk = st.text_input("Coluna ID (Para Inteligente)")
        with c3: modo = st.selectbox("Estratégia", ["Inteligente (Filtrar Existentes)", "Append (Adicionar)", "Replace (Substituir)"])

    # ==========================================
    # --- PAINEL DE TRATAMENTO DE DADOS ---
    # ==========================================
    st.markdown("---")
    st.subheader("🧹 Tratamento e Limpeza (Opcional)")
    
    config_limpeza = {}
    with st.expander("Clique para configurar regras de limpeza", expanded=False):
        c_limp1, c_limp2 = st.columns(2)
        
        with c_limp1:
            config_limpeza["remover_nulos"] = st.checkbox("🗑️ Remover linhas com valores Nulos")
            config_limpeza["remover_duplicadas"] = st.checkbox("👯 Remover linhas duplicadas")
            
        with c_limp2:
            config_limpeza["preencher_nulos"] = st.checkbox("✏️ Preencher Nulos com valor padrão")
            if config_limpeza["preencher_nulos"]:
                config_limpeza["valor_nulo"] = st.text_input("Valor para preencher", "Não Informado")
        
        colunas_disponiveis = []
        if 'df_preview' in locals():
            colunas_disponiveis = df_preview.columns.tolist()
            
        config_limpeza["colunas_mascarar"] = st.multiselect(
            "🔒 Mascarar Colunas Sensíveis (LGPD)", 
            options=colunas_disponiveis,
            help="Substitui parte do texto por *** para proteger dados como CPF, Email, etc."
        )

    st.markdown("---")
    st.subheader("🚀 Ações de Migração e Backup")

    # --- BOTÕES DE AÇÃO ---
    col_a, col_b, col_c = st.columns(3)

    def obter_dataframe_origem(eng):
        if "Básico" in tipo_migracao:
            return pd.read_sql_table(tabela_origem, eng)
        else:
            return pd.read_sql(query_sql, eng)

    with col_a:
        if st.button("💾 Backup Local", use_container_width=True):
            if not tabela_destino: st.error("Defina o nome da tabela de destino.")
            else:
                t, d, h, p, db, u, pw = src_data
                url = montar_url_universal(t, d, h, p, db, u, pw)
                ok, err, eng = testar_conexao(url)
                if ok:
                    try:
                        df = obter_dataframe_origem(eng)
                        csv = df.to_csv(index=False, sep=';').encode('utf-8')
                        st.download_button("⬇️ Baixar CSV", csv, f"bkp_{tabela_destino}.csv", "text/csv")
                    except Exception as e:
                        st.error(f"Erro na extração: {e}")
                else: st.error(err)

    with col_b:
        if st.button("☁️ Backup Drive", use_container_width=True):
            if not tabela_destino: 
                st.error("Defina o nome da tabela de destino.")
            else:
                with st.spinner("📦 Extraindo e enviando para o Google Drive..."):
                    t, d, h, p, db, u, pw = src_data
                    url = montar_url_universal(t, d, h, p, db, u, pw)
                    ok, err, eng = testar_conexao(url)
                    if ok:
                        try:
                            df = obter_dataframe_origem(eng)
                            
                            sucesso, resultado = fazer_upload_direto_google(df, tabela_destino)
                            
                            if sucesso:
                                st.success(f"Upload concluído! Arquivo ID: {resultado}")
                                st.balloons()
                            else:
                                st.error(f"Falha no upload: {resultado}")
                        except Exception as e:
                            st.error(f"Erro no processamento: {e}")
                    else:
                        st.error(f"Erro de conexão: {err}")

    with col_c:
        if st.button("🚀 Iniciar Migração", type="primary", use_container_width=True):
            if not (tabela_destino and src_data[4] and dst_data[4]): 
                st.error("Preencha o nome da tabela e selecione os bancos de origem e destino.")
            else:
                with st.status("Executando migração...") as s:
                    try:
                        url_s = montar_url_universal(*src_data)
                        url_d = montar_url_universal(*dst_data)
                        _, _, eng_s = testar_conexao(url_s)
                        _, _, eng_d = testar_conexao(url_d)
                        
                        # 1. Extração
                        df = obter_dataframe_origem(eng_s)
                        s.write(f"📖 {len(df)} registros extraídos da origem.")
                        
                        # 2. Transformação 
                        df = aplicar_transformacoes(df, config_limpeza)
                        s.write(f"🧹 Dados tratados. Restaram {len(df)} registros para envio.")
                        
                        # 3. Carga (Load)
                        if "Inteligente" in modo and pk:
                            try:
                                existentes = pd.read_sql(f"SELECT {pk} FROM {tabela_destino}", eng_d)[pk].tolist()
                                df = df[~df[pk].isin(existentes)]
                                s.write(f"🕵️ Filtrados: {len(df)} novos para inserir.")
                            except: 
                                s.write("⚠️ Tabela destino não existe ainda, ignorando filtro inteligente.")

                        metodo = "replace" if "Replace" in modo else "append"
                        df.to_sql(tabela_destino, eng_d, if_exists=metodo, index=False, chunksize=1000)
                        
                        s.update(label="Migração Concluída com Sucesso!", state="complete")
                        st.balloons()
                    except Exception as e:
                        s.update(label=f"Erro na migração.", state="error")
                        st.error(f"Detalhes do Erro: {e}")

# ==========================================
# 5. ORQUESTRADOR DE EXECUÇÃO
# ==========================================

desenhar_sidebar()
desenhar_painel_principal()