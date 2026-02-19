import streamlit as st
import requests
import google.generativeai as genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Agente Auditor IA", page_icon="🤖", layout="wide")

# --- OPÇÃO 2: TESTE DO AMBIENTE FANTASMA ---
# Isso vai exibir no topo da sua tela qual versão o servidor realmente está usando
st.warning(f"🔍 DEBUG: A versão atual da biblioteca google-generativeai carregada pelo servidor é a: {genai.__version__}")

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

# --- INICIALIZAÇÃO DO HISTÓRICO DE CHAT ---
if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []

# --- OPÇÃO 1: CONSULTA DIRETA VIA API REST (PLANO NUCLEAR) ---
def consultar_ia_direto(prompt_usuario, historico):
    try:
        if "gemini" not in st.secrets:
            return "⚠️ API Key do Gemini não configurada nas Secrets."
            
        api_key = st.secrets["gemini"]["api_key"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        headers = {'Content-Type': 'application/json'}
        
        # Monta o histórico de conversa no formato exato que a API REST exige
        conteudos = []
        for msg in historico:
            role = "model" if msg["role"] == "assistant" else "user"
            conteudos.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        # Adiciona a pergunta atual do usuário no final do array
        conteudos.append({"role": "user", "parts": [{"text": prompt_usuario}]})
        
        # Monta o corpo da requisição com a instrução de sistema
        payload = {
            "systemInstruction": {
                "parts": [{"text": "Você é um Especialista Sênior em QA e Segurança de Software. Analise os códigos, logs ou arquiteturas fornecidas com foco em vulnerabilidades (SQL Injection, XSS, etc) e boas práticas."}]
            },
            "contents": conteudos
        }
        
        # Dispara a requisição HTTP direta
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            dados = response.json()
            return dados['candidates'][0]['content']['parts'][0]['text']
        else:
            return f"🚨 Erro na API do Google: Status {response.status_code}\nDetalhes: {response.text}"
            
    except Exception as e:
        return f"🚨 Erro Crítico no Código: {e}"

# --- INTERFACE ---
st.title("🤖 Agente Auditor V-Nexus (Modo REST API)")
st.caption("Chat interativo à prova de falhas de biblioteca - Powered by Gemini 1.5")

if st.button("⬅️ Voltar ao Dashboard"):
    st.switch_page("Login.py")

st.divider()

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
    # Exibe o histórico de mensagens na tela
    for msg in st.session_state.mensagens_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Campo de entrada de texto
    if prompt := st.chat_input("Cole seu log, código ou faça uma pergunta técnica..."):
        
        # Exibe a mensagem do usuário
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Spinner enquanto aguarda a resposta da API REST
        with st.chat_message("assistant"):
            with st.spinner("Acessando diretamente os servidores da IA..."):
                resposta_texto = consultar_ia_direto(prompt, st.session_state.mensagens_chat)
                st.markdown(resposta_texto)
        
        # Salva as duas mensagens no histórico da sessão
        st.session_state.mensagens_chat.append({"role": "user", "content": prompt})
        st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_texto})