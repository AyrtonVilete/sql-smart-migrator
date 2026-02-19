import streamlit as st
import google.generativeai as genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Agente Auditor IA", page_icon="🤖", layout="wide")

# --- TRAVA DE SEGURANÇA ---
if not st.session_state.get('autenticado'):
    st.error("🚫 Acesso negado! Faça login no Portal.")
    st.stop()

if not st.session_state.get('p_ia', False):
    st.warning("⚠️ Seu usuário não tem permissão para acessar o Agente IA.")
    st.stop()

# --- CSS PARA ESCONDER MENU LATERAL AUTOMÁTICO ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURAÇÃO DA IA ---
def configurar_gemini():
    if "gemini" in st.secrets:
        chave = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=chave)
        return True
    return False

def inicializar_modelo():
    # Usando System Instruction nativo (requer google-generativeai >= 0.7.2)
    instrucao_sistema = """
    Você é um Especialista Sênior em QA e Segurança de Software. 
    Analise os códigos, logs ou arquiteturas fornecidas. 
    Seu foco principal é identificar vulnerabilidades críticas (como SQL Injection, Cross-Site Scripting - XSS, vazamento de dados), validar boas práticas de engenharia e propor soluções robustas para erros sistêmicos ou de banco de dados.
    """
    
    # Inicia o modelo Flash (mais rápido para interações de chat)
    try:
        return genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=instrucao_sistema
        )
    except Exception as e:
        st.error(f"Erro ao carregar o modelo: {e}")
        return None

# --- INICIALIZAÇÃO DO HISTÓRICO DE CHAT ---
if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []

# --- INTERFACE ---
st.title("🤖 Agente Auditor V-Nexus")
st.caption("Chat interativo com memória - Powered by Gemini 1.5")

if st.button("⬅️ Voltar ao Dashboard"):
    st.switch_page("Login.py")

st.divider()

if configurar_gemini():
    modelo = inicializar_modelo()
    
    if modelo:
        col_chat, col_info = st.columns([2, 1])

        with col_info:
            with st.container(border=True):
                st.info("ℹ️ **Dicas de Uso**")
                st.markdown("""
                - Cole logs de erro complexos.
                - Peça para caçar vulnerabilidades de segurança em trechos de código.
                - O Agente lembra do contexto da conversa atual!
                """)
                if st.button("🗑️ Limpar Conversa"):
                    st.session_state.mensagens_chat = []
                    st.rerun()

        with col_chat:
            # Exibe o histórico de mensagens
            for msg in st.session_state.mensagens_chat:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            # Campo de entrada de texto nativo de chat do Streamlit
            if prompt := st.chat_input("Cole seu log, código ou faça uma pergunta técnica..."):
                
                # Exibe a mensagem do usuário
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Salva a mensagem do usuário no histórico
                st.session_state.mensagens_chat.append({"role": "user", "content": prompt})

                # Cria o histórico no formato que a API do Gemini exige
                historico_gemini = [
                    {"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} 
                    for m in st.session_state.mensagens_chat[:-1] # Pega tudo menos a última mensagem
                ]
                
                # Inicia a sessão de chat na API
                chat = modelo.start_chat(history=historico_gemini)

                # Gera a resposta com efeito máquina de escrever (Streaming)
                with st.chat_message("assistant"):
                    resposta_placeholder = st.empty()
                    resposta_completa = ""
                    
                    with st.spinner("Analisando..."):
                        try:
                            response = chat.send_message(prompt, stream=True)
                            for pedaco in response:
                                resposta_completa += pedaco.text
                                resposta_placeholder.markdown(resposta_completa + "▌")
                            
                            # Atualiza sem o cursor no final
                            resposta_placeholder.markdown(resposta_completa)
                            
                            # Salva a resposta da IA no estado da sessão
                            st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_completa})
                        
                        except Exception as e:
                            st.error(f"Erro na comunicação com a IA: {e}")

else:
    st.error("⚠️ API Key do Gemini não configurada nas Secrets.")