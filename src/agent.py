class Agent:
    """Agente básico para demonstração do Build Agent."""

    def __init__(self, name: str = "BuildAgent"):
        self.name = name

    def greet(self) -> str:
        return f"{self.name} está pronto."

    def run_task(self, task_name: str) -> dict:
        """Executa uma tarefa de demonstração e retorna um resultado simples."""
        # Implementação mínima que pode ser expandida posteriormente
        return {"task": task_name, "status": "completed", "agent": self.name}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Executar o agente de build minimal.")
    parser.add_argument("task", nargs="?", default="demo", help="Nome da tarefa para executar")
    args = parser.parse_args()

    ag = Agent()
    print(ag.greet())
    print(ag.run_task(args.task))
