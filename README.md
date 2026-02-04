# 💾 Migrador SQL + Build Agent

Projeto Python que combina uma ferramenta GUI Streamlit para migração segura de dados SQL Server com um agente de demonstração configurável.

## Sobre o Projeto

Este repositório contém:

### 1. **Migrador SQL Server (GUI com Streamlit)**
- Interface web interativa para migração/backup de dados entre servidores SQL Server
- Suporte para SQL Server 2015-2026 (Express, Standard, Enterprise)
- Configuração inteligente de drivers ODBC (17, 18, 13 e legado)
- Tratamento de erros SSL/TLS para SQL Server 2022+
- Leitura de tabelas origem em memória com DataFrame (Pandas)
- Export para CSV local com download
- Cópia de dados entre servidores SQL Server (replace mode)

### 2. **Build Agent + CLI**
- Agente mínimo para demonstração com classe `Agent`
- Wrapper CLI para execução de tarefas via linha de comando
- Testes unitários com pytest

## Como Usar

### Instalação de Dependências
```bash
pip install -r requirements.txt
```

### Rodar a Interface Streamlit (Migrador SQL)
```bash
streamlit run Script.py
```
A aplicação será aberta em `http://localhost:8501`

### Executar o Agente via CLI
```bash
python -m src.cli demo
```
Ou com um nome de tarefa customizado:
```bash
python -m src.cli sua_tarefa
```

### Rodar Testes
```bash
pytest
```

## 📁 Estrutura do Projeto
```
.
├── Script.py              # Aplicação Streamlit (Migrador SQL)
├── requirements.txt       # Dependências Python
├── README.md             # Este arquivo
├── src/
│   ├── __init__.py
│   ├── agent.py          # Classe Agent para agente de build
│   └── cli.py            # Interface CLI
├── tests/
│   ├── __init__.py
│   └── test_agent.py     # Testes unitários
└── agents/
    └── __init__.py
```

## ⚙️ Dependências Principais

- **streamlit**: Framework para interface web
- **pandas**: Manipulação de dados e CSV
- **SQLAlchemy**: ORM para SQL Server
- **pyodbc**: Driver ODBC para conexão SQL Server
- **google-api-python-client**: Upload para Google Drive
- **google-auth-oauthlib**: Autenticação Google
- **pytest**: Framework de testes

## 💡 Dicas para SQL Server Express

1. **Nome do Host**
   - `localhost\SQLEXPRESS`
   - `.\SQLEXPRESS`
   - `SEU_NOME_DE_PC\SQLEXPRESS`

2. **Erro de SSL/TLS**
   - Para SQL Server 2022 com Driver 18, marque "Ignorar Erro de Certificado SSL"

3. **TCP/IP**
   - SQL Express vem com TCP/IP desativado
   - Configure via SQL Configuration Manager

## 📝 Instalação

- Crie e ative seu ambiente virtual (opcional, recomendado).
- Instale dependências:

```bash
pip install -r requirements.txt
```

**Modo de uso**

- Interface gráfica (Streamlit):

	1. Inicie a interface:

	```bash
	streamlit run Script.py
	```

	2. Na barra lateral, digite a senha do cofre para desbloquear `credentials.lock` (arquivo com as credenciais do service account criptografadas). Ao desbloquear com sucesso será solicitado o `ID da Pasta Drive` para onde os backups serão enviados.
	3. Configure origem e destino (driver, host, banco, user, senha, Trust Cert) e informe a `Tabela` e `Primary Key`.
	4. Escolha o `Modo` (Inteligente / Append / Replace) e clique em **EXECUTAR**.

- Linha de comando (agente minimal):

```bash
python -m src.cli demo
# ou executar tarefa específica
python -m src.cli minha_tarefa
```

**Executar testes**

```bash
pytest -q
```

**Arquivos relevantes**

- [Script.py](Script.py): app Streamlit (migrador e cofre seguro).
- [src/agent.py](src/agent.py): classe `Agent` com métodos de demonstração.
- [src/cli.py](src/cli.py): wrapper CLI para executar o agente.
- [tests/test_agent.py](tests/test_agent.py): testes unitários.

UPDATE Disponibilizado em Release
V2 - Disponibilizada. 

