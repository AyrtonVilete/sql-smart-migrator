import requests

class SqlAgent:
    """Agente mínimo para processamento de tarefas via IA."""
    
    def __init__(self, api_url="https://api-sql-migrator.onrender.com/chat"):
        self.api_url = api_url

    def execute_task(self, prompt, history=None):
        """Executa uma tarefa ou responde a um prompt do usuário."""
        history = history or []
        texto_historico = ""
        
        for msg in history[-4:]: 
            papel = "Usuário" if msg["role"] == "user" else "IA"
            texto_historico += f"{papel}: {msg['content']}\n"
            
        prompt_final = prompt
        if texto_historico:
            prompt_final = f"Contexto da conversa recente:\n{texto_historico}\n\nNova instrução: {prompt}"

        try:
            response = requests.post(self.api_url, json={"mensagem_usuario": prompt_final})
            if response.status_code == 200:
                return response.json().get('resposta', 'Resposta vazia da IA.')
            else:
                return f"🚨 Erro na API do Render: Status {response.status_code}"
        except Exception as e:
            return f"🚨 Erro Crítico de Comunicação: {e}"