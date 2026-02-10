import streamlit as st
import sys

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="V-Nexus | Suite", page_icon="💠", layout="wide")

# --- CSS PREMIUM (Animações e Layout Fixo) ---
st.markdown("""
    <style>
        /* Esconde navegação automática */
        [data-testid="stSidebarNav"] {display: none !important;}
        
        /* 1. ESTILO DOS CARDS (Caixas) */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 12px;
            background-color: #1E1E1E; /* Cor de fundo escura suave */
            border: 1px solid #333;
            transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s;
            height: 320px !important; /* ALTURA FIXA PARA TODOS OS CARDS */
            display: flex;
            flex-direction: column;
            justify-content: space-between; /* Empurra o botão para baixo */
        }
        
        /* 2. EFEITO DE HOVER (Mouse em cima) */
        div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-5px); /* Levanta levemente */
            box-shadow: 0 10px 20px rgba(0,0,0,0.4);
            border-color: #FF4B4B; /* Cor de destaque (vermelho do Streamlit) */
        }

        /* 3. CONTEÚDO DENTRO DO CARD */
        .card-content {
            flex-grow: 1; /* Ocupa o espaço disponível */
        }

        /* 4. BOTÕES */
        .stButton button {
            width: 100%;
            border-radius: 8px;
            font-weight: bold;
            transition: all 0.2s;
        }
        
        /* Centraliza Títulos */
        h3 {text-align: center; margin-bottom: 0px;}
        p {text-align: center; font-size: 0.9em; color: #BBB;}
    </style>
""", unsafe_allow_html=True)

# --- DEBUG ---
try:
    from sqlalchemy import create_engine, text
    import psycopg2 
except ImportError as e:
    st.error(f"❌ Erro Crítico: Biblioteca faltando! {e}")
    st.stop()

# --- ESTADO ---
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
            query = text("""
                SELECT nome_exibicao, projeto_migrador, projeto_ia 
                FROM tb_usuarios 
                WHERE usuario = :u AND senha = :p AND ativo = true
            """)
            return conn.execute(query, {"u": usuario, "p": senha}).fetchone()
    except Exception as e:
        st.error(f"⚠️ Erro de Conexão: {e}")
        return None

def criar_usuario(nome, user, senha):
    try:
        engine = conectar_banco()
        with engine.connect() as conn:
            check = conn.execute(text("SELECT id FROM tb_usuarios WHERE usuario = :u"), {"u": user}).fetchone()
            if check: return False, "Usuário já existe."
            
            query = text("""
                INSERT INTO tb_usuarios (nome_exibicao, usuario, senha, projeto_migrador, projeto_ia, ativo) 
                VALUES (:n, :u, :p, false, false, true)
            """)
            conn.execute(query, {"n": nome, "u": user, "p": senha})
            conn.commit()
            return True, "Cadastro realizado! Aguarde liberação."
    except Exception as e:
        return False, f"Erro ao cadastrar: {e}"

# --- APP PRINCIPAL ---
def main():
    # 1. TELA LOGIN
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
                            st.session_state.p1 = res[1]
                            st.session_state.p_ia = res[2]
                            st.rerun()
                        else: st.error("Acesso negado.")
            with tab_cadastro:
                with st.form("cad_form"):
                    n, u, p = st.text_input("Nome"), st.text_input("User"), st.text_input("Senha", type="password")
                    if st.form_submit_button("Criar Conta", use_container_width=True):
                        ok, msg = criar_usuario(n, u, p)
                        if ok: st.success(msg)
                        else: st.error(msg)

    # 2. DASHBOARD PREMIUM
    else:
        st.markdown("<h1 style='text-align: center; margin-bottom: 5px;'>💠 V-Nexus Portal</h1>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: gray; margin-top: 0;'>Bem-vindo, {st.session_state.nome} | Selecione um sistema</p>", unsafe_allow_html=True)
        st.write("---")

        c1, c2, c3 = st.columns(3)

        # --- CARD 1: MIGRADOR ---
        with c1:
            with st.container(border=True):
                # Conteúdo Superior
                st.markdown("### 🧰 SQL Migrator")
                st.markdown("<p>Solução completa para migração entre bancos (SQL Server, MySQL, Postgres) e backup automatizado em nuvem.</p>", unsafe_allow_html=True)
                
                # Espaço flexível (empurra botão pra baixo)
                st.write("") 
                
                # Botão Inferior
                if st.session_state.p1:
                    st.page_link("pages/SQL_Migrator.py", label="🚀 Acessar Sistema", use_container_width=True)
                else:
                    st.button("🔒 Bloqueado", disabled=True, use_container_width=True, key="lok1")

        # --- CARD 2: AGENTE IA ---
        with c2:
            with st.container(border=True):
                st.markdown("### 🤖 Agente Auditor")
                st.markdown("<p>Inteligência Artificial (Gemini 1.5) para análise de logs, detecção de vulnerabilidades e chat técnico de QA.</p>", unsafe_allow_html=True)
                
                st.write("") 
                
                if st.session_state.get('p_ia', False):
                    st.page_link("pages/IA_Assistant.py", label="🤖 Acessar IA", use_container_width=True)
                else:
                    st.button("🔒 Bloqueado", disabled=True, use_container_width=True, key="lok2")

        # --- CARD 3: ANALYTICS ---
        with c3:
            with st.container(border=True):
                st.markdown("### 📊 Analytics Hub")
                st.markdown("<p>Dashboard executivo para monitoramento de KPIs, performance de sistemas e relatórios gerenciais.</p>", unsafe_allow_html=True)
                
                st.write("") 
                
                st.button("🚧 Em Construção", disabled=True, use_container_width=True, key="lok3")

        # Sidebar
        st.sidebar.markdown(f"👤 **{st.session_state.nome}**")
        st.sidebar.divider()
        if st.sidebar.button("🚪 Sair", use_container_width=True):
            st.session_state.autenticado = False
            st.rerun()
        st.markdown("---")
        st.markdown("<p style='text-align: center; font-size: 0.8em;'>© 2026 Vilete Tech Solutions</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro: {e}")