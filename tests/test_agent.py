import sys
import os
import pytest
from unittest.mock import patch, Mock

# --- O TRUQUE DE PATH ---
# Força o Python a olhar para a pasta raiz do projeto antes de importar
caminho_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, caminho_src)

# Importa o módulo local
from agent import SqlAgent

def test_agent_initialization():
    """Testa se o agente inicia com a URL correta por padrão."""
    agent = SqlAgent()
    assert agent.api_url == "https://api-sql-migrator.onrender.com/chat"

@patch('agent.requests.post')
def test_agent_execute_task_sucesso(mock_post):
    """Testa a execução de uma tarefa com retorno 200 (Sucesso) simulado."""
    # Configura o comportamento do request "falso"
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"resposta": "SELECT * FROM usuarios;"}
    mock_post.return_value = mock_response

    # Executa a ação
    agent = SqlAgent()
    resultado = agent.execute_task("Me dê um select de usuários")

    # Verifica se o resultado é o esperado e se a API foi chamada
    assert resultado == "SELECT * FROM usuarios;"
    mock_post.assert_called_once()

@patch('agent.requests.post')
def test_agent_execute_task_erro_api(mock_post):
    """Testa como o agente lida com um erro 500 do servidor."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_post.return_value = mock_response

    agent = SqlAgent()
    resultado = agent.execute_task("Gere um erro")

    assert "Erro na API do Render: Status 500" in resultado