# Build Agent (Minimal)

Estrutura mínima criada para um agente de build simples e a ferramenta de migração.

Como usar

- Instalar dependências:

```bash
pip install -r requirements.txt
```

- Rodar o app Streamlit (interface disponível em `Script.py`):

```bash
streamlit run Script.py
```

- Executar o agente de demonstração:

```bash
python -m src.cli demo
```

# Build Agent & Migrador Seguro SQL

Este repositório contém duas partes principais:

- Um agente mínimo de demonstração (classe `Agent`) com wrapper CLI.
- Um app Streamlit para migração/backup SQL com cofre seguro e upload ao Google Drive.

**Novas implementações e funcionalidades**

- **Migrador Seguro (GUI)**: implementado em [Script.py](Script.py)
	- Interface Streamlit com configuração de origem/destino (driver, host, banco, usuário, senha).
	- Suporte a múltiplos drivers SQL Server: ODBC Driver 17/18, SQL Server nativo ou customizado.
	- Teste de conexão via SQLAlchemy (`testar_conexao`) com feedback em tempo real.
	- **Exporta dados para CSV com backup automático**: extrai dados da tabela de origem e cria backup local.
	- **Upload seguro para Google Drive** usando `InstalledAppFlow` OAuth 2.0:
		- Autenticação automática com refresh de token.
		- Gerenciamento seguro de credenciais (arquivo `token.json`).
		- Remove o arquivo local de backup após upload bem-sucedido por segurança.
		
	- **Três modos de transferência de dados**:
		- **Modo Inteligente**: filtra duplicados analisando a Primary Key do destino, inserindo apenas registros novos.
		- **Modo Append**: adiciona todos os registros do backup à tabela destino.
		- **Modo Replace**: substitui completamente a tabela destino pelos dados da origem.
	- Campo obrigatório de `Primary Key` para o Modo Inteligente (evita inserções duplicadas).
	- **Processamento em chunks**: inserção em lotes de 1000 registros para otimizar performance.
	- Interface com status em tempo real, mostrando cada etapa do processo (conexão, leitura, backup, upload, transferência).
	- Tratamento robusto de erros com mensagens descritivas.
	- Suporte a `TrustServerCertificate` e `Encrypt` para conexões seguras.

- **Agente & CLI**:
	- `src/agent.py`: classe `Agent` com `greet()` e `run_task(task_name)` retornando um dicionário de status.
	- `src/cli.py`: wrapper de linha de comando para executar tarefas do agente: `python -m src.cli <task>`.

- **Testes**: testes unitários básicos em [tests/test_agent.py](tests/test_agent.py) (use `pytest`).

**Instalação**

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

**Gerar o arquivo `credentials.lock` (exemplo)**

O app espera um arquivo `credentials.lock` contendo o JSON de credenciais do service account criptografado com a mesma derivação de chave usada no `Script.py` (salt: `salt_seguro_fixo_projeto_sql`, PBKDF2HMAC, 100000 iterações). Um exemplo mínimo para gerar esse arquivo:

```python
from cryptography.fernet import Fernet
import base64, json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

salt = b'salt_seguro_fixo_projeto_sql'
def gerar_chave(senha: str):
		kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
		return base64.urlsafe_b64encode(kdf.derive(senha.encode()))

senha = "SUA_SENHA_DO_COFRE"
key = gerar_chave(senha)
fernet = Fernet(key)

# `service_account_info` é o dicionário JSON com as credenciais do service account
service_account_info = { /* seu JSON de credenciais aqui */ }
dados = json.dumps(service_account_info).encode()
dados_cript = fernet.encrypt(dados)
with open("credentials.lock", "wb") as f:
		f.write(dados_cript)
```

Observação: guarde a senha em local seguro; o mesmo salt e esquema de KDF devem ser usados para descriptografar no app.

**Executar testes**

```bash
pytest -q
```

**Arquivos relevantes**

- [Script.py](Script.py): app Streamlit (migrador e cofre seguro).
- [src/agent.py](src/agent.py): classe `Agent` com métodos de demonstração.
- [src/cli.py](src/cli.py): wrapper CLI para executar o agente.
- [tests/test_agent.py](tests/test_agent.py): testes unitários.

---

## 🔄 Testes Automatizados (Em Breve)

A configuração de **testes automatizados** será implementada em breve, incluindo:
- Testes unitários expandidos para o migrador SQL
- Testes de integração para fluxos de Google Drive
- Validação de modos de transferência (Inteligente, Append, Replace)
- CI/CD pipeline para validação automática

Fique atento às atualizações! 👀
