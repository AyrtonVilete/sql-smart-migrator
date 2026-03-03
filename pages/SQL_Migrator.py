import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import URL
from datetime import datetime
import os
import io
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
# 1. CONFIGURAÇÃO 
# ==========================================
st.set_page_config(page_title="V-Nexus SQL Smart Migrator", layout="wide", page_icon="🧰")

# Inicializa as variáveis de sessão essenciais
if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []

# --- NOVA CONFIGURAÇÃO CLOUD (BRIDGE API) ---
URL_API_DRIVE = "https://v-nexus-drive.onrender.com/upload"
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

# --- NOVA FUNÇÃO DE UPLOAD VIA BRIDGE API (RENDER) ---
def enviar_para_bridge_drive(df, nome_tabela):
    """Envia o DataFrame para a API Bridge no Render, que faz o upload para o Drive."""
    try:
        # 1. Transforma o DataFrame em CSV diretamente na memória
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8')
        csv_buffer.seek(0)
        
        # 2. Prepara o nome do arquivo com data e hora
        timestamp = datetime.now().strftime("%d%m%Y_%H%M")
        nome_arquivo = f"bkp_{nome_tabela}_{timestamp}.csv"
        
        # 3. Dispara a requisição POST para a sua API no Render
        files = {"file": (nome_arquivo, csv_buffer, "text/csv")}
        data = {"folder_id": ID_PADRAO_DRIVE}
        
        response = requests.post(URL_API_DRIVE, files=files, data=data, timeout=60)
        
        if response.status_code == 200:
            return True, response.json().get("file_id")
        else:
            return False, f"Erro na API Bridge: {response.text}"
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
        if st.button("📡 Verificar Status Bridge API"):
            try:
                # Chama o "/" da sua API para ver se está online
                res = requests.get("https://v-nexus-drive.onrender.com/", timeout=10)
                if res.status_code == 200:
                    st.success("API Bridge Online! 🚀")
                else:
                    st.error("API respondeu com erro.")
            except:
                st.error("API Offline ou em modo de espera (Render).")
        
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
        if st.button("⬅️ Voltar ao Portal", use_container_width=True):
            st.switch_page("Login.py") # Mantive o nome Login.py caso este seja o arquivo principal

        st.caption("v4.0 - Cloud Edition + IA Integrada")

# ==========================================
# 4. INTERFACE DO PAINEL PRINCIPAL (CENTRO)
# ==========================================
def desenhar_painel_principal():
    st.title("🧰 SQL Smart Migrator (v4 Cloud + IA)")
    
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
        
        # 1. Tenta conectar na origem para puxar as tabelas
        tabelas_disponiveis = []
        eng_origem_temp = None
        if src_data[4]: # Se o banco de origem já estiver definido
            url_s = montar_url_universal(*src_data)
            ok_s, _, eng_origem_temp = testar_conexao(url_s)
            if ok_s:
                tabelas_disponiveis = listar_tabelas(eng_origem_temp)

        # --- A CHECKBOX LIVRE ---
        # Agora ela NUNCA fica bloqueada. O usuário tem total controle.
        usa_lista = st.checkbox("📋 Selecionar tabela da lista (Desmarque para digitar manualmente)", value=True)

        # 2. Interface de Seleção (Alinhamento rigoroso no topo das colunas)
        c1, c2, c3 = st.columns(3)
        
        with c1: 
            if usa_lista:
                if tabelas_disponiveis:
                    tabela_origem = st.selectbox("Tabela de Origem", tabelas_disponiveis)
                else:
                    # Dropdown informativo se o banco ainda não foi selecionado
                    tabela_origem_dummy = st.selectbox("Tabela de Origem", ["⚠️ Conecte o banco de origem para listar..."], disabled=True)
                    tabela_origem = "" # Variável limpa para não bugar o botão de Preview
            else:
                tabela_origem = st.text_input("Tabela de Origem (Manual)")
                
            tabela_destino = st.text_input("Tabela no Destino", value=tabela_origem)
            
        with c2: 
            pk = st.text_input("Coluna ID (Para Inteligente)", help="Chave primária para evitar duplicidade.")
            
        with c3: 
            modo = st.selectbox("Estratégia de Migração", ["Inteligente (Filtrar Existentes)", "Append (Adicionar)", "Replace (Substituir)"])

        # 3. Área de Preview (Largura Total - Fora das colunas)
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
        
        # Botão mágico de Pré-visualização
        if st.button("👁️ Visualizar Dados (Preview)", use_container_width=True):
            if query_sql and src_data[4]: # Checa se tem query e banco selecionado
                try:
                    url_s = montar_url_universal(*src_data)
                    ok, err, eng_s = testar_conexao(url_s)
                    if ok:
                        with st.spinner("Executando query na origem..."):
                            df_preview = pd.read_sql(query_sql, eng_s)
                            st.success(f"✅ Sucesso! A query retornou {len(df_preview)} linhas.")
                            st.dataframe(df_preview.head(50), use_container_width=True) # Mostra no máximo 50 para não pesar a tela
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
    # --- NOVO: PAINEL DE TRATAMENTO DE DADOS ---
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
                with st.spinner("📦 Extraindo e enviando para nuvem..."):
                    t, d, h, p, db, u, pw = src_data
                    url = montar_url_universal(t, d, h, p, db, u, pw)
                    ok, err, eng = testar_conexao(url)
                    if ok:
                        try:
                            # Extrai os dados
                            df = obter_dataframe_origem(eng)
                            
                            # Envia para a Bridge API
                            sucesso, resultado = enviar_para_bridge_drive(df, tabela_destino)
                            
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