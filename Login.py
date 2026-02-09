import streamlit as st
from sqlalchemy import create_engine, text

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Portal Vilete Tech", page_icon="🔐", layout="centered")

# --- INICIALIZAÇÃO DO ESTADO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- FUNÇÃO DE CONEXÃO ---
def conectar_banco():
    # Puxa a URI configurada nas Secrets do Streamlit Cloud
    return create_engine(st.secrets["supabase"]["url_conexao"])

# --- FUNÇÃO DE LOGIN ---
def validar_login(usuario, senha):
    try:
        engine = conectar_banco()
        with engine.connect() as conn:
            # Busca usuário ativo com senha correspondente
            query = text("""
                SELECT nome_exibicao, projeto_migrador 
                FROM tb_usuarios 
                WHERE usuario = :u AND senha = :p AND ativo = true
            """)
            return conn.execute(query, {"u": usuario, "p": senha}).fetchone()
    except Exception as e:
        st.error(f"Erro ao validar login: {e}")
        return None

# --- FUNÇÃO DE CADASTRO ---
def criar_usuario(nome, user, senha):
    try:
        engine = conectar_banco()
        with engine.connect() as conn:
            # Verifica se o usuário já existe no banco
            check = conn.execute(text("SELECT id FROM tb_usuarios WHERE usuario = :u"), {"u": user}).fetchone()
            if check:
                return False, "Este usuário já está cadastrado."
            
            # Insere o novo usuário (projeto_migrador inicia como False por segurança)
            query = text("""
                INSERT INTO tb_usuarios (nome_exibicao, usuario, senha, projeto_migrador, ativo) 
                VALUES (:n, :u, :p, false, true)
            """)
            conn.execute(query, {"n": nome, "u": user, "p": senha})
            conn.commit()
            return True, "Cadastro realizado com sucesso! Solicite ao admin a liberação dos sistemas."
    except Exception as e:
        return False, f"Erro técnico ao cadastrar: {e}"

# --- LÓGICA DE NAVEGAÇÃO ---

# 1. TELA INICIAL (Não Autenticado)
if not st.session_state.autenticado:
    # Esconde a sidebar nativa do Streamlit para forçar o login
    st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>🔐 Portal Vilete Tech</h1>", unsafe_allow_html=True)
    
    tab_login, tab_cadastro = st.tabs(["🔑 Acessar Portal", "📝 Criar Nova Conta"])
    
    with tab_login:
        with st.form("form_login"):
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                res = validar_login(u, p)
                if res:
                    st.session_state.autenticado = True
                    st.session_state.nome = res[0]
                    st.session_state.p1 = res[1] # Permissão do Migrador
                    st.rerun()
                else:
                    st.error("Credenciais incorretas ou conta inativa.")

    with tab_cadastro:
        with st.form("form_registro"):
            n_nome = st.text_input("Nome Completo")
            n_user = st.text_input("Nome de Usuário")
            n_pass = st.text_input("Crie uma Senha", type="password")
            if st.form_submit_button("Finalizar Cadastro", use_container_width=True):
                if n_nome and n_user and n_pass:
                    ok, msg = criar_usuario(n_nome, n_user, n_pass)
                    if ok: st.success(msg)
                    else: st.error(msg)
                else:
                    st.warning("Preencha todos os campos obrigatórios.")

# 2. DASHBOARD PRINCIPAL (Autenticado)
else:
    st.title(f"🚀 Bem-vindo ao seu Portal, {st.session_state.nome}")
    
    # Configuração da Barra Lateral (Sidebar)
    st.sidebar.title("🛠️ Menu de Navegação")
    st.sidebar.success(f"Conectado como: {st.session_state.nome}")
    
    # Verifica permissão para mostrar o link do Migrador
    if st.session_state.p1:
        st.sidebar.page_link("pages/Script.py", label="Abrir Migrador SQL", icon="🧰")
    else:
        st.sidebar.warning("Migrador: Aguardando Liberação")

    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair do Portal"):
        st.session_state.autenticado = False
        st.rerun()

    # Cards de Status no Portal
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.info("### 🧰 Migrador SQL")
        if st.session_state.p1:
            st.success("Acesso: LIBERADO ✅")
            st.caption("Acesse pela barra lateral 👈")
        else:
            st.warning("Acesso: BLOQUEADO 🔒")
            st.caption("Contate o administrador para liberar.")

    with c2:
        st.write("### 📊 Projeto 2")
        st.write("🏗️ Em breve...")

    with c3:
        st.write("### 🛡️ Projeto 3")
        st.write("🏗️ Em breve...")