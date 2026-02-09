import streamlit as st
import sys

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="V-Nexus | Suite", page_icon="💠", layout="wide")

# --- CSS: ESCONDE A NAVEGAÇÃO PADRÃO (Mantém o app limpo) ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- DEBUG DE BIBLIOTECAS ---
try:
    from sqlalchemy import create_engine, text
    import psycopg2 
except ImportError as e:
    st.error(f"❌ Erro Crítico: Biblioteca faltando! {e}")
    st.stop()

# --- ESTADO INICIAL ---
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
            # Busca permissões do Migrador e da IA
            query = text("""
                SELECT nome_exibicao, projeto_migrador, projeto_ia 
                FROM tb_usuarios 
                WHERE usuario = :u AND senha = :p AND ativo = true
            """)
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
            
            # Cria usuário (padrão: sem acesso aos sistemas sensíveis)
            query = text("""
                INSERT INTO tb_usuarios (nome_exibicao, usuario, senha, projeto_migrador, projeto_ia, ativo) 
                VALUES (:n, :u, :p, false, false, true)
            """)
            conn.execute(query, {"n": nome, "u": user, "p": senha})
            conn.commit()
            return True, "Cadastro realizado! Aguarde liberação do admin."
    except Exception as e:
        return False, f"Erro ao cadastrar: {e}"

# --- INTERFACE PRINCIPAL ---
def main():
    # 1. TELA DE LOGIN (Sem Sidebar)
    if not st.session_state.autenticado:
        st.markdown("<style>section[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
        
        col_esq, col_centro, col_dir = st.columns([1, 2, 1])
        with col_centro:
            st.markdown("<h1 style='text-align: center;'>💠 V-Nexus System</h1>", unsafe_allow_html=True)
            st.write("")
            
            tab_login, tab_cadastro = st.tabs(["🔑 Acessar", "📝 Registrar"])
            
            with tab_login:
                with st.form("login_form"):
                    u = st.text_input("Usuário")
                    p = st.text_input("Senha", type="password")
                    if st.form_submit_button("Entrar no Portal", use_container_width=True):
                        res = validar_login(u, p)
                        if res:
                            st.session_state.autenticado = True
                            st.session_state.nome = res[0]
                            st.session_state.p1 = res[1]   # Permissão Migrador
                            st.session_state.p_ia = res[2] # Permissão IA
                            st.rerun()
                        else:
                            st.error("Credenciais inválidas ou acesso negado.")
            
            with tab_cadastro:
                with st.form("cadastro_form"):
                    n = st.text_input("Nome Completo")
                    u = st.text_input("Usuário")
                    p = st.text_input("Senha", type="password")
                    if st.form_submit_button("Criar Conta", use_container_width=True):
                        ok, msg = criar_usuario(n, u, p)
                        if ok: st.success(msg)
                        else: st.error(msg)

    # 2. DASHBOARD (Visual de Cards Restaurado)
    else:
        st.markdown("<h1 style='text-align: center;'>💠 V-Nexus Portal</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; color: gray;'>Olá, {st.session_state.nome}! Com o que vamos trabalhar hoje?</h3>", unsafe_allow_html=True)
        st.divider()

        # Layout de 3 Colunas para os Cards
        c1, c2, c3 = st.columns(3)

        # --- CARD 1: MIGRADOR SQL ---
        with c1:
            with st.container(border=True):
                st.markdown("### 🧰 SQL Migrator")
                st.caption("v3.0 - Cloud Edition")
                st.markdown("Migração de bancos, backup em nuvem e gestão de dados.")
                st.write("") # Espaçamento
                
                # Botão Largo (Padrão que você gostou)
                if st.session_state.p1:
                    st.page_link("pages/Script.py", label="🚀 Acessar Migrador", use_container_width=True)
                else:
                    st.button("🔒 Acesso Bloqueado", disabled=True, use_container_width=True)

        # --- CARD 2: AGENTE AUDITOR IA ---
        with c2:
            with st.container(border=True):
                st.markdown("### 🤖 Agente Auditor")
                st.caption("Powered by Gemini 1.5")
                st.markdown("IA para análise de logs, erros de SQL e validação de segurança.")
                st.write("") # Espaçamento
                
                # Botão Largo
                if st.session_state.get('p_ia', False):
                    st.page_link("pages/IA_Assistant.py", label="🤖 Acessar IA", use_container_width=True)
                else:
                    st.button("🔒 Acesso Bloqueado", disabled=True, use_container_width=True)

        # --- CARD 3: ANALYTICS (FUTURO) ---
        with c3:
            with st.container(border=True):
                st.markdown("### 📊 Analytics Hub")
                st.caption("Em Breve")
                st.markdown("Dashboards de performance e relatórios gerenciais.")
                st.write("") # Espaçamento
                
                st.button("🚧 Em Construção", disabled=True, use_container_width=True)

        # --- SIDEBAR PÓS-LOGIN (Apenas Infos e Sair) ---
        st.sidebar.markdown(f"👤 **{st.session_state.nome}**")
        st.sidebar.divider()
        if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
        
        st.markdown("---")
        st.caption("© 2026 V-Nexus System - Vilete Tech Solutions")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro inesperado: {e}")