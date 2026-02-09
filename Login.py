import streamlit as st
import sys

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="V-Nexus | Suite", page_icon="💠", layout="wide")

# --- CSS PARA ESCONDER A NAVEGAÇÃO AUTOMÁTICA (O SEGREDO ESTÁ AQUI) ---
st.markdown("""
    <style>
        /* Esconde os links automáticos (Script, Login, etc.) */
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- MODO DE DEBUG ---
try:
    from sqlalchemy import create_engine, text
    import psycopg2 
except ImportError as e:
    st.error(f"❌ Erro Crítico: Biblioteca faltando! {e}")
    st.stop()

# --- INICIALIZAÇÃO DO ESTADO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- FUNÇÕES DE BANCO ---
def conectar_banco():
    if "supabase" not in st.secrets:
        st.error("❌ Erro: Configuração '[supabase]' não encontrada nas Secrets.")
        st.stop()
    return create_engine(st.secrets["supabase"]["url_conexao"])

def validar_login(usuario, senha):
    try:
        engine = conectar_banco()
        with engine.connect() as conn:
            query = text("SELECT nome_exibicao, projeto_migrador FROM tb_usuarios WHERE usuario = :u AND senha = :p AND ativo = true")
            return conn.execute(query, {"u": usuario, "p": senha}).fetchone()
    except Exception as e:
        st.error(f"⚠️ Erro de Conexão com Banco: {e}")
        return None

def criar_usuario(nome, user, senha):
    try:
        engine = conectar_banco()
        with engine.connect() as conn:
            check = conn.execute(text("SELECT id FROM tb_usuarios WHERE usuario = :u"), {"u": user}).fetchone()
            if check: return False, "Usuário já existe."
            
            query = text("INSERT INTO tb_usuarios (nome_exibicao, usuario, senha, projeto_migrador, ativo) VALUES (:n, :u, :p, false, true)")
            conn.execute(query, {"n": nome, "u": user, "p": senha})
            conn.commit()
            return True, "Cadastro realizado! Aguarde liberação."
    except Exception as e:
        return False, f"Erro ao cadastrar: {e}"

# --- INTERFACE PRINCIPAL ---
def main():
    # 1. TELA DE LOGIN
    if not st.session_state.autenticado:
        # Esconde a sidebar completamente na tela de login
        st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
        
        col_c, col_form, col_d = st.columns([1, 2, 1])
        with col_form:
            st.markdown("<h1 style='text-align: center;'>💠 V-Nexus System</h1>", unsafe_allow_html=True)
            st.write("")
            
            tab1, tab2 = st.tabs(["🔑 Acessar", "📝 Registrar"])
            
            with tab1:
                with st.form("login"):
                    u = st.text_input("Usuário")
                    p = st.text_input("Senha", type="password")
                    if st.form_submit_button("Entrar no Portal", use_container_width=True):
                        res = validar_login(u, p)
                        if res:
                            st.session_state.autenticado = True
                            st.session_state.nome = res[0]
                            st.session_state.p1 = res[1]
                            st.rerun()
                        else:
                            st.error("Acesso negado.")
            
            with tab2:
                with st.form("cadastro"):
                    n = st.text_input("Nome")
                    u = st.text_input("Usuário")
                    p = st.text_input("Senha", type="password")
                    if st.form_submit_button("Criar Conta"):
                        ok, msg = criar_usuario(n, u, p)
                        if ok: st.success(msg)
                        else: st.error(msg)

    # 2. DASHBOARD (PÓS-LOGIN)
    else:
        st.markdown("<h1 style='text-align: center;'>💠 V-Nexus Portal</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; color: gray;'>Olá, {st.session_state.nome}! Com o que vamos trabalhar hoje?</h3>", unsafe_allow_html=True)
        st.write("---")

        col1, col2, col3 = st.columns(3)

        with col1:
            with st.container(border=True):
                st.markdown("### 🧰 SQL Migrator")
                st.caption("v3.0 - Cloud Edition")
                st.write("Ferramenta de migração e backup.")
                st.write("")
                if st.session_state.p1:
                    st.page_link("pages/Script.py", label="🚀 Acessar Sistema", use_container_width=True)
                else:
                    st.button("🔒 Bloqueado", disabled=True, key="lok1")

        with col2:
            with st.container(border=True):
                st.markdown("### 📊 Analytics")
                st.caption("Em Breve")
                st.write("Dashboard de dados.")
                st.write("")
                st.button("🚧 Em Construção", disabled=True, key="lok2")

        with col3:
            with st.container(border=True):
                st.markdown("### 🛡️ Security")
                st.caption("Em Breve")
                st.write("Scanner de vulnerabilidades.")
                st.write("")
                st.button("🚧 Em Construção", disabled=True, key="lok3")

        # Sidebar Pós-Login
        st.sidebar.markdown(f"👤 **{st.session_state.nome}**")
        st.sidebar.divider()
        if st.sidebar.button("🚪 Sair", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
        
        st.markdown("---")
        st.caption("© 2026 V-Nexus System")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro: {e}")