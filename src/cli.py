import argparse
import sys
from agent import SqlAgent

def main():
    # Configura os argumentos da linha de comando
    parser = argparse.ArgumentParser(
        description="🛠️ V-Nexus SQL Smart Migrator CLI - Assistente via Terminal"
    )
    parser.add_argument(
        "task", 
        type=str, 
        nargs='?', 
        help="A tarefa de banco de dados ou instrução SQL para o Agent."
    )
    
    args = parser.parse_args()

    # Se o usuário não digitar nada, pede o input
    tarefa = args.task
    if not tarefa:
        tarefa = input("Digite a instrução para o Agent SQL: ")
        if not tarefa.strip():
            print("Nenhuma tarefa fornecida. Encerrando.")
            sys.exit(1)

    print(f"\n🤖 Agent processando: '{tarefa}'...\n")
    
    # Instancia o Agent e executa
    agent = SqlAgent()
    resposta = agent.execute_task(tarefa)
    
    print("=" * 50)
    print("📋 RESPOSTA DO AGENT:")
    print("-" * 50)
    print(resposta)
    print("=" * 50)

if __name__ == "__main__":
    main()