import argparse
from .agent import Agent


def main():
    parser = argparse.ArgumentParser(description="CLI wrapper para o Build Agent")
    parser.add_argument("task", nargs="?", default="demo", help="Nome da tarefa a executar")
    args = parser.parse_args()

    ag = Agent()
    print(ag.greet())
    print(ag.run_task(args.task))


if __name__ == "__main__":
    main()
