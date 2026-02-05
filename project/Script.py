import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from datetime import datetime
import os

# --- BIBLIOTECAS GOOGLE OAUTH ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Migrador SQL Completo", layout="wide", page_icon="🚀")
st.title("🚀 Migrador SQL")

# --- VARIÁVEIS FIXAS ---
PASTA_CREDENCIAIS = "Credencials"
ID_PADRAO_DRIVE = "1M2OZgy3MV8JcYyvMngVE5ZDEHChwmCR2" # Sua pasta fixa
SCOPES = ['https://www.googleapis.com/auth/drive.file']

if not os.path.exists(PASTA_CREDENCIAIS):
    os.makedirs(PASTA_CREDENCIAIS)

ARQUIVO_CLIENT_SECRET = os.path.join(PASTA_CREDENCIAIS, "client_secret.json")
ARQUIVO_TOKEN = os.path.join(PASTA_CREDENCIAIS, "token.json")

ARQUIVO_CLIENT_LOCK = os.path.join(PASTA_CREDENCIAIS, "client_secret.lock")

# --- FUNÇÕES GOOGLE ---
def autenticar_google_drive():
    creds = None
    
    # 1. Tenta carregar o token da pasta 'Credencials'
    if os.path.exists(ARQUIVO_TOKEN):
        try:
            creds = Credentials.from_authorized_user_file(ARQUIVO_TOKEN, SCOPES)
        except:
            pass 
    # 2. Se não houver credenciais válidas, inicia o fluxo de autenticação
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                creds = None
        
        if not creds:
            # Verifica se o 'client_secret.json' está dentro da pasta 'Credencials'
            if not os.path.exists(ARQUIVO_CLIENT_SECRET):
                # Retorna um erro claro mostrando onde o sistema procurou
                return None, f"Arquivo não encontrado em: {ARQUIVO_CLIENT_SECRET}"
            
            # Inicia o fluxo OAuth na porta 8090
            flow = InstalledAppFlow.from_client_secrets_file(ARQUIVO_CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=8090)
            
            # Salva o novo token dentro da pasta 'Credencials'
            with open(ARQUIVO_TOKEN, 'w') as token:
                token.write(creds.to_json())
                
    return build('drive', 'v3', credentials=creds), "OK"

def upload_para_drive(service, caminho_arquivo, nome_arquivo, id_pasta):
    try:
        file_metadata = {'name': nome_arquivo, 'parents': [id_pasta]}
        media = MediaFileUpload(caminho_arquivo, mimetype='text/csv')
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return True, file.get('id')
    except Exception as e:
        return False, str(e)

# --- FUNÇÕES SQL ---
DRIVERS_SQL_SERVER = ["ODBC Driver 17 for SQL Server", "ODBC Driver 18 for SQL Server", "SQL Server", "Outro"]

def montar_connection_url(driver, manual, host, user, pwd, db, trust):
    d_final = manual if driver == "Outro" else driver
    conn_str = f"DRIVER={{{d_final}}};SERVER={host};DATABASE={db};UID={user};PWD={pwd};"
    if trust: conn_str += "TrustServerCertificate=yes;Encrypt=yes;"
    return URL.create("mssql+pyodbc", query={"odbc_connect": conn_str})

def testar_conexao(url):
    try:
        eng = create_engine(url)
        with eng.connect() as c: return True, None, eng
    except Exception as e: return False, str(e), None

def render_db_inputs(k):
    st.subheader(f"Configuração {k}")
    d = st.selectbox("Driver", DRIVERS_SQL_SERVER, key=f"{k}_d")
    h = st.text_input("Host", value=".\\SQLEXPRESS", key=f"{k}_h")
    db = st.text_input("Banco", key=f"{k}_db")
    u = st.text_input("User", value="sa", key=f"{k}_u")
    p = st.text_input("Senha", type="password", key=f"{k}_p")
    t = st.checkbox("Trust SSL", value=True, key=f"{k}_t")
    return d, "", h, u, p, db, t

# --- INTERFACE ---
with st.sidebar:
    st.header("☁️ Status Google Drive")
    folder_id = st.text_input("ID Pasta Drive", value=ID_PADRAO_DRIVE)
    
    if os.path.exists(ARQUIVO_TOKEN):
        st.success("✅ Login Salvo")
        
        col_teste, col_sair = st.columns(2)
        
        # BOTÃO 1: TESTAR CONEXÃO
        with col_teste:
            if st.button("📡 Testar API"):
                with st.spinner("Validando token..."):
                    try:
                        service, msg = autenticar_google_drive()
                        
                        if service:
                            about_info = service.about().get(fields="user").execute()
                            
                            email_usuario = about_info['user']['emailAddress']
                            nome_usuario = about_info['user']['displayName']
                        
                            st.toast(f"Token Válido! Olá, {nome_usuario}", icon="✅")
                            st.info(f"Conectado como:\n{email_usuario}")
                        else:
                            st.error(f"Falha na autenticação: {msg}")
                            
                    except Exception as e:
                        st.error("Erro ao validar token.")
                        st.caption(f"Detalhe técnico: {e}")

        # BOTÃO 2: LOGOUT
        with col_sair:
            if st.button("🚪 Sair"):
                try:
                    os.remove(ARQUIVO_TOKEN)
                    st.rerun()
                except:
                    st.error("Erro ao apagar token.")
    
    else:
        st.info("O login será solicitado na primeira execução.")

c1, c2 = st.columns(2)
with c1: src = render_db_inputs("Origem")
with c2: dst = render_db_inputs("Destino")

st.markdown("---")
ca, cb, cc = st.columns(3)
with ca: tab = st.text_input("Tabela")
with cb: pk = st.text_input("Primary Key (ID)", help="Obrigatório para Modo Inteligente")
with cc: modo = st.selectbox("Modo", ["Inteligente (Filtrar Duplicados)", "Append (Adicionar)", "Replace (Substituir)"])

if st.button("🚀 EXECUTAR PROCESSO COMPLETO", type="primary"):
    # 1. Validação
    s_drv, _, s_h, s_u, s_p, s_db, s_t = src
    d_drv, _, d_h, d_u, d_p, d_db, d_t = dst
    
    if not (s_h and s_db and tab):
        st.error("Preencha os dados da Origem e Tabela.")
        st.stop()
        
    if "Inteligente" in modo and not pk:
        st.error("⚠️ Para Modo Inteligente, você PRECISA informar a Primary Key (ID).")
        st.stop()

    status = st.status("Iniciando motor...", expanded=True)

    try:
        # --- PARTE 1: LEITURA E BACKUP ---
        status.write("🔌 Conectando na Origem...")
        url_s = montar_connection_url(s_drv, "", s_h, s_u, s_p, s_db, s_t)
        ok_s, err_s, eng_s = testar_conexao(url_s)
        if not ok_s: raise Exception(f"Erro Origem: {err_s}")
        
        status.write(f"📖 Lendo dados de '{tab}'...")
        try:
            # read_sql_table é blindado. Ele sanitiza o nome da tabela automaticamente.
            df_origem = pd.read_sql_table(tab, eng_s)
        except ValueError:
            # O Pandas lança ValueError se a tabela não existir
            st.error(f"❌ A tabela '{tab}' não foi encontrada no banco de origem.")
            st.stop()
        # ------------------------------------
        
        if df_origem.empty:
            st.warning("A tabela de origem está vazia.")
            st.stop()
            
        fname = f"backup_{tab}_{datetime.now().strftime('%H%M%S')}.csv"
        df_origem.to_csv(fname, index=False, sep=';')
        status.write("💾 Backup local gerado.")

        # --- PARTE 2: UPLOAD GOOGLE DRIVE ---
        service_drive = None
        if folder_id:
            try:
                status.write("☁️ Verificando autenticação Google...")
                service_drive, msg = autenticar_google_drive()
                if service_drive:
                    status.write("☁️ Enviando para o Drive...")
                    ok_up, res_up = upload_para_drive(service_drive, fname, fname, folder_id)
                    if ok_up:
                        status.write(f"✅ Upload Concluído! (ID: {res_up})")
                        os.remove(fname) # Remove local após sucesso
                    else:
                        st.error(f"Erro no Upload: {res_up}")
            except Exception as e:
                st.warning(f"Pulei o Drive por erro: {e}")

        # --- PARTE 3: TRANSFERÊNCIA SQL (A Lógica que faltava!) ---
        if d_h and d_db:
            status.write("🔌 Conectando no Destino...")
            url_d = montar_connection_url(d_drv, "", d_h, d_u, d_p, d_db, d_t)
            ok_d, err_d, eng_d = testar_conexao(url_d)
            if not ok_d: raise Exception(f"Erro Destino: {err_d}")

            df_final = df_origem
            dup_count = 0
            
            # Lógica do Modo Inteligente
            if "Inteligente" in modo:
                status.write("🕵️ Analisando duplicidades...")
                try:
                    # --- 🛡️ ALTERAÇÃO DE SEGURANÇA 2 ---
                    # Em vez de f"SELECT {pk}...", usamos a abstração:
                    ids_destino = pd.read_sql_table(tab, eng_d, columns=[pk])
                    # ------------------------------------
                    
                    if not ids_destino.empty:
                        # Otimização com SET para performance (O(1))
                        lista_ids = set(ids_destino[pk].tolist())
                        
                        mask = df_origem[pk].isin(lista_ids)
                        df_final = df_origem[~mask]
                        dup_count = mask.sum()
                    else:
                        dup_count = 0

                    status.write(f"📊 Análise: {len(df_final)} Novos | {dup_count} Duplicados (Ignorados)")
                
                except ValueError:
                    # Se der erro aqui, é provável que a tabela não exista no destino ainda
                    status.write("ℹ️ Tabela destino não existe. Tudo será inserido como novo.")
                except Exception as e:
                    # Outros erros (ex: coluna PK não existe)
                    status.warning(f"Aviso na verificação: {e}")

            # Define o comportamento de escrita
            metodo = "replace" if "Replace" in modo else "append"

            if not df_final.empty:
                status.write(f"🚀 Inserindo {len(df_final)} linhas no destino...")
                # to_sql já é seguro por natureza (usa parâmetros internamente)
                df_final.to_sql(tab, eng_d, if_exists=metodo, index=False, chunksize=1000)
                status.update(label="Sucesso Total! 🏁", state="complete")
                st.success(f"Processo finalizado! {len(df_final)} linhas transferidas.")
            else:
                status.update(label="Finalizado (Nada a inserir)", state="complete")
                st.info("Nenhum dado novo para transferir. Backup na nuvem está OK.")
                
    except Exception as e:
        status.update(label="Erro Crítico", state="error")
        st.error(f"Ocorreu um erro: {e}")