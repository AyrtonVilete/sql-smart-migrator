import streamlit as st
import requests

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Agente Auditor IA", page_icon="🤖", layout="wide")

# --- CSS PARA ESCONDER MENU LATERAL AUTOMÁTICO ---
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO DO HISTÓRICO DE CHAT ---
if "mensagens_chat" not in st.session_state:
    st.session_state.mensagens_chat = []

# --- CONSULTA VIA API RENDER ---
def consultar_ia_render(prompt_usuario, historico):
    try:
        # URL da sua API no Render
        url_api = "https://api-sql-migrator.onrender.com/chat"
        
        texto_historico = ""
        for msg in historico[-4:]: 
            papel = "Usuário" if msg["role"] == "user" else "IA"
            texto_historico += f"{papel}: {msg['content']}\n"

        prompt_final = prompt_usuario
        if texto_historico:
            prompt_final = f"Contexto da conversa recente:\n{texto_historico}\n\nNova instrução/pergunta: {prompt_usuario}"

        payload = {
            "mensagem_usuario": prompt_final
        }
        
        response = requests.post(url_api, json=payload)
        
        if response.status_code == 200:
            dados = response.json()
            return dados['resposta']
        else:
            return f"🚨 Erro na API do Render: Status {response.status_code}\nDetalhes: {response.text}"
            
    except Exception as e:
        return f"🚨 Erro Crítico de Comunicação com a API: {e}"

# --- INTERFACE ---
st.title("🤖 Agente Auditor V-Nexus (Via Nuvem)")
st.caption("Chat interativo conectado ao Backend no Render")

if st.button("⬅️ Voltar ao Portal"):
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
    for msg in st.session_state.mensagens_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Cole seu log, código ou faça uma pergunta técnica..."):
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Processando no servidor da nuvem..."):
                resposta_texto = consultar_ia_render(prompt, st.session_state.mensagens_chat)
                st.markdown(resposta_texto)
        
        st.session_state.mensagens_chat.append({"role": "user", "content": prompt})
        st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_texto})