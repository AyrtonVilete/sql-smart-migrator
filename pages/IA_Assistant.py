import streamlit as st
import google.generativeai as genai

# Configuração da API
def configurar_gemini():
    if "gemini" in st.secrets:
        chave = st.secrets["gemini"]["api_key"]
        genai.configure(api_key=chave)
        return True
    return False

def consultar_ia(pergunta):
    try:
        # Usa o modelo Gemini Pro (texto)
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(pergunta)
        return response.text
    except Exception as e:
        return f"Erro na IA: {e}"

# --- INTERFACE ---
st.set_page_config(page_title="IA SQL Helper", page_icon="🤖")

st.title("🤖 Assistente de QA com Gemini")

if configurar_gemini():
    texto_usuario = st.text_area("Cole seu código SQL ou Erro aqui:")
    
    if st.button("Analisar com IA"):
        if texto_usuario:
            with st.spinner("A IA está analisando..."):
                prompt = f"Você é um especialista em SQL e QA. Analise este código/erro e sugira correções de forma breve: {texto_usuario}"
                resposta = consultar_ia(prompt)
                st.markdown("### 🤖 Resposta:")
                st.write(resposta)
        else:
            st.warning("Digite algo primeiro.")
else:
    st.error("Configure a API Key do Gemini nas Secrets.")