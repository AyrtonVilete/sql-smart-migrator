import os
import sys
import streamlit.web.cli as stcli

def main():
    # Descobre o caminho absoluto do seu script Streamlit
    diretorio_atual = os.path.dirname(__file__)
    script_path = os.path.join(diretorio_atual, "Login.py")

    # Simula o comando "streamlit run" no terminal
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()