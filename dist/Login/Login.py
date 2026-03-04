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

# --- ESTADO PADRÃO (SIMULANDO ACESSO LIBERADO) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = True
    st.session_state.nome = "Administrador" # Nome que vai aparecer na tela
    st.session_state.p1 = True              # Destrava o Migrador
    st.session_state.p_ia = True            # Destrava a IA

# --- APP PRINCIPAL ---
def main():
    # DASHBOARD PREMIUM
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
            st.markdown("<p>Inteligência Artificial (Gemini 1.5) para análise de logs, detecção de vulnerabilidades, auxilio com comandos SQL e chat técnico.</p>", unsafe_allow_html=True)
            
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
    
    st.markdown("---")
    st.markdown("<p style='text-align: center; font-size: 0.8em;'>© 2026 Vilete Tech Solutions</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Erro: {e}")