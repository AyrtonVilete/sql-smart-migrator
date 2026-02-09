import streamlit as st
import sys

# --- CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha) ---
st.set_page_config(page_title="V-Nexus | Suite", page_icon="💠", layout="centered")

# --- MODO DE DEBUG (Tenta rodar e mostra o erro se falhar) ---
try:
    from sqlalchemy import create_engine, text
    import psycopg2 # Verifica se a lib está instalada
except ImportError as e:
    st.error(f"❌ Erro Crítico: Biblioteca faltando! {e}")
    st.info("Verifique se 'sqlalchemy' e 'psycopg2-binary' estão no requirements.txt")
    st.stop()

# --- INICIALIZAÇÃO DO ESTADO ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

# --- FUNÇÕES (COM PROTEÇÃO EXTRA) ---
def conectar_banco():
    # Verifica se as secrets existem antes de tentar conectar
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
            return True, "Cadastro realizado!"
    except Exception as e:
        return False, f"Erro ao cadastrar: {e}"
    
#TESTE

# --- INTERFACE PRINCIPAL ---
def main():
    if not st.session_state.autenticado:
        # Esconde sidebar
        st.markdown("<h1 style='text-align: center;'>💠 V-Nexus System</h1>", unsafe_allow_html=True)
        
        st.title(f"💠 V-Nexus Dashboard")
        tab1, tab2 = st.tabs(["Login", "Cadastro"])
        
        with tab1:
            with st.form("login"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
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
                u = st.text_input("User")
                p = st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    ok, msg = criar_usuario(n, u, p)
                    if ok: st.success(msg)
                    else: st.error(msg)
    else:
        st.title(f"🚀 Olá, {st.session_state.nome}")
        st.sidebar.success(f"Logado: {st.session_state.nome}")
        
        # Link para o Migrador
        if st.session_state.p1:
            st.sidebar.page_link("pages/Script.py", label="Abrir Migrador SQL", icon="🧰")
        else:
            st.sidebar.warning("Sem acesso ao Migrador")
            
        if st.sidebar.button("Sair"):
            st.session_state.autenticado = False
            st.rerun()

# --- PONTO DE PARTIDA SEGURO ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error("❌ Ocorreu um erro inesperado na aplicação:")
        st.code(str(e))