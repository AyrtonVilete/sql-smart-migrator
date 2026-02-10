import streamlit as st
import google.generativeai as genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Agente Auditor IA", page_icon="🤖", layout="wide")

# --- TRAVA DE SEGURANÇA (Igual ao Migrador) ---
if not st.session_state.get('autenticado'):
    st.error("🚫 Acesso negado! Faça login no Portal.")
    st.stop()

# Verifica permissão específica de IA
if not st.session_state.get('p_ia', False):
    st.warning("⚠️ Seu usuário não tem permissão para acessar o Agente IA.")
    st.stop()

# --- CSS PARA ESCONDER MENU LATERAL AUTOMÁTICO ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def configurar_gemini():
    if "gemini" in st.secrets:
        chave = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=chave)
        return True
    return False

def consultar_ia(pergunta):
    try:
        # TENTATIVA 1: Modelo Flash (Mais rápido e novo)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(pergunta)
        return response.text
    except Exception as e:
        # TENTATIVA 2 (Fallback): Tenta o Gemini Pro antigo se o Flash falhar
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(pergunta)
            return response.text
        except Exception as e2:
            # Se ambos falharem, mostra o erro original
            return f"Erro Crítico na IA: {e}"

# --- INTERFACE ---
st.title("🤖 Agente Auditor V-Nexus")
st.caption("Powered by Gemini 1.5 Flash")

# Botão de Voltar
if st.button("⬅️ Voltar ao Dashboard"):
    st.switch_page("Login.py")

st.divider()

if configurar_gemini():
    # Layout de duas colunas
    col_chat, col_info = st.columns([2, 1])

    with col_chat:
        st.subheader("💬 Chat de Auditoria")
        texto_usuario = st.text_area("Cole o log de erro, trecho de código ou dúvida de auditoria:", height=150)
        
        if st.button("🔍 Analisar com IA", type="primary"):
            if texto_usuario:
                with st.spinner("O Agente está analisando os dados..."):
                    # Prompt Engenheirado para QA
                    prompt_sistema = f"""
                    Você é um Auditor Sênior de QA e Segurança. 
                    Analise o seguinte conteúdo técnico com foco em vulnerabilidades, boas práticas e correção de erros.
                    Se for um erro de banco de dados, explique a causa raiz e a solução SQL.
                    
                    Conteúdo: {texto_usuario}
                    """
                    resposta = consultar_ia(prompt_sistema)
                    
                    st.success("Análise Concluída!")
                    st.markdown("### 📝 Relatório do Agente:")
                    st.write(resposta)
            else:
                st.warning("Por favor, insira algum conteúdo para análise.")

    with col_info:
        with st.container(border=True):
            st.info("ℹ️ **Dicas de Uso**")
            st.markdown("""
            - Cole logs de erro do Migrador SQL.
            - Peça validação de segurança em scripts.
            - Solicite explicações de erros complexos.
            """)

else:
    st.error("⚠️ API Key do Gemini não configurada nas Secrets.")