import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from datetime import datetime
import os

# Configuração da Página
st.set_page_config(page_title="Migrador Universal SQL", layout="wide", page_icon="💾")

st.title("💾 Migrador SQL")
st.info("Ferramenta para migrar tabelas entre bancos SQL Server com backup local em CSV.")
st.markdown("---")

# --- LISTA DE DRIVERS COMUNS (2015 a 2026) ---
# O SQL Server muda o driver recomendado a cada versão.
DRIVERS_SQL_SERVER = [
    "ODBC Driver 17 for SQL Server", # Padrão ouro (SQL 2017/2019)
    "ODBC Driver 18 for SQL Server", # Padrão do SQL 2022 (Exige TrustCertificate)
    "ODBC Driver 13 for SQL Server", # Antigo (SQL 2016)
    "SQL Server",                    # Legado (Genérico do Windows, funciona sempre mas é lento)
    "Outro (Digitar Manualmente)"
]

# --- FUNÇÃO DE MONTAGEM DE URI INTELIGENTE ---
def montar_connection_url(driver_choice, driver_manual, host, user, password, database, trust_cert):
    """
    Cria uma URL de conexão robusta para SQLAlchemy + PyODBC
    """
    driver_final = driver_manual if driver_choice == "Outro (Digitar Manualmente)" else driver_choice
    
    conn_str = (
        f"DRIVER={{{driver_final}}};"
        f"SERVER={host};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
    )
    
    # Versões novas exigem TrustServerCertificate=yes se não houver SSL configurado
    if trust_cert:
        conn_str += "TrustServerCertificate=yes;Encrypt=yes;"
    
    
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": conn_str})
    return connection_url

def testar_conexao(url):
    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            return True, None, engine
    except Exception as e:
        return False, str(e), None

# --- SIDEBAR: INSTRUÇÕES ---
with st.sidebar:
    st.header("💡 Dicas para SQL Express")
    st.markdown("""
    **1. Nome do Host:**
    No SQL Express, o host raramente é apenas `localhost`. Tente:
    * `localhost\\SQLEXPRESS`
    * `.\\SQLEXPRESS`
    * `SEU_NOME_DE_PC\\SQLEXPRESS`
    
    **2. Erro de SSL/TLS:**
    Se usar SQL 2022 ou Driver 18, marque a caixa **"Ignorar Erro de Certificado SSL"**.
    
    **3. TCP/IP:**
    O SQL Express vem com TCP/IP desativado. Verifique no *SQL Configuration Manager*.
    """)

# --- INTERFACE PRINCIPAL ---
col1, col2 = st.columns(2)

def renderizar_inputs_banco(titulo, chave_prefixo):
    st.subheader(titulo)
    
    # Seleção de Driver Inteligente
    drv = st.selectbox(
        "Versão do Driver ODBC", 
        DRIVERS_SQL_SERVER, 
        index=0, 
        key=f"{chave_prefixo}_drv_list"
    )
    
    drv_man = ""
    if drv == "Outro (Digitar Manualmente)":
        drv_man = st.text_input("Nome do Driver", key=f"{chave_prefixo}_drv_man")
    
    host = st.text_input("Host / Instância (ex: .\SQLEXPRESS)", value=".\\SQLEXPRESS", key=f"{chave_prefixo}_host")
    db = st.text_input("Banco de Dados", key=f"{chave_prefixo}_db")
    user = st.text_input("Usuário (sa)", value="sa", key=f"{chave_prefixo}_user")
    password = st.text_input("Senha", type="password", key=f"{chave_prefixo}_pass")
    
    trust = st.checkbox("Ignorar Erro de Certificado SSL (TrustServerCertificate)", value=True, key=f"{chave_prefixo}_trust", help="Obrigatório para SQL 2022 local")
    
    return drv, drv_man, host, user, password, db, trust

with col1:
    src_data = renderizar_inputs_banco("1. Origem", "src")

with col2:
    dst_data = renderizar_inputs_banco("2. Destino", "dst")

st.markdown("---")


st.subheader("3. Operação")
col_tbl, col_act = st.columns([3, 1])

with col_tbl:
    tabela_alvo = st.text_input("Nome da Tabela para Copiar")

with col_act:
    st.write("")
    st.write("") 
    btn_migrar = st.button("🚀 INICIAR OPERAÇÃO", type="primary", use_container_width=True)

if btn_migrar:
    s_drv, s_man, s_host, s_user, s_pass, s_db, s_trust = src_data
    d_drv, d_man, d_host, d_user, d_pass, d_db, d_trust = dst_data
    
    if not (s_host and s_user and s_db and tabela_alvo):
        st.error("Preencha todos os campos obrigatórios da Origem e o nome da Tabela.")
        st.stop()
        
    status = st.status("Processando...", expanded=True)
    
    try:
        # 1. CONEXÃO ORIGEM
        status.write("🔌 Testando conexão com a Origem...")
        url_src = montar_connection_url(s_drv, s_man, s_host, s_user, s_pass, s_db, s_trust)
        ok_src, erro_src, eng_src = testar_conexao(url_src)
        
        if not ok_src:
            status.update(label="Falha na Conexão de Origem", state="error")
            st.error(f"Erro detalhado: {erro_src}")
            st.stop()
            
        # 2. LEITURA
        status.write(f"📖 Lendo tabela '{tabela_alvo}'...")
        df = pd.read_sql(f"SELECT * FROM {tabela_alvo}", eng_src)
        
        if df.empty:
            status.update(label="Aviso: Tabela Vazia", state="complete")
            st.warning("A tabela existe mas não tem dados.")
            st.stop()
            
        st.dataframe(df.head(3), use_container_width=True)
        status.write(f"✅ {len(df)} linhas carregadas em memória.")

        # 3. BACKUP
        status.write("💾 Gerando arquivo de backup CSV...")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bkp_name = f"backup_{tabela_alvo}_{ts}.csv"
        df.to_csv(bkp_name, index=False, sep=';')
        
        with open(bkp_name, "rb") as f:
            st.download_button("Baixar Backup", f, file_name=bkp_name)

        # 4. CONEXÃO DESTINO E ESCRITA
        if d_host and d_db: 
            status.write("📤 Conectando no Destino...")
            url_dst = montar_connection_url(d_drv, d_man, d_host, d_user, d_pass, d_db, d_trust)
            ok_dst, erro_dst, eng_dst = testar_conexao(url_dst)
            
            if not ok_dst:
                status.update(label="Falha na Conexão de Destino", state="error")
                st.error(f"Erro no destino: {erro_dst}")
                st.stop()

            status.write("🚀 Transferindo dados...")
            # Verifica se usa replace ou append (aqui simplifiquei para replace para o teste, pode ajustar)
            df.to_sql(tabela_alvo, eng_dst, if_exists='replace', index=False, chunksize=1000)
            status.update(label="Sucesso Absoluto! 🏁", state="complete")
            st.success("Processo finalizado com sucesso!")
        else:
            status.update(label="Concluído (Apenas Backup)", state="complete")
            st.info("Nenhum destino configurado. Backup local realizado.")

    except Exception as e:
        status.update(label="Erro Crítico", state="error")
        st.error(f"Ocorreu um erro: {e}")