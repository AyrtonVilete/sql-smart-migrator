import google.generativeai as genai
import os

# 1. Configuração da API Key
# É recomendável usar variáveis de ambiente para segurança
api_key = "AIzaSyAZgkf-g0nHfVbBDqLbk84SeZoZpm5yDWQ" 
genai.configure(api_key=api_key)

# 2. Configuração do Modelo
# Usamos o 'gemini-2.0-flash' para velocidade ou 'gemini-1.5-pro' para análises profundas
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction="""
    Você é um especialista em engenharia de confiabilidade de sites (SRE) e desenvolvedor sênior.
    Sua tarefa é analisar logs de erro, identificar a causa raiz e propor soluções em código.
    Seja conciso e use blocos de código markdown para as correções.
    """
)

def analisar_erro(log_text):
    prompt = f"Analise o seguinte log de erro e sugira uma correção:\n\n{log_text}"
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro ao chamar a API: {e}"

# Exemplo de uso com um log real
meu_log = """
Traceback (most recent call last):
  File "app.py", line 15, in <module>
    result = database.connect()
  File "db.py", line 42, in connect
    raise ConnectionError("Timeout: Could not reach host 10.0.0.5")
ConnectionError: Timeout: Could not reach host 10.0.0.5
"""

analise = analisar_erro(meu_log)
print("--- ANÁLISE DO GEMINI ---")
print(analise)