# 🧰 V-Nexus SQL Smart Migrator (v4 Cloud + IA)

O **SQL Smart Migrator** é uma ferramenta robusta desenvolvida com Python e Streamlit para facilitar a migração e o tratamento de dados entre diferentes bancos de dados relacionais (SQL Server, MySQL e PostgreSQL). 

Nesta versão v4, o sistema conta com um Assistente de IA integrado para tirar dúvidas de SQL e uma comunicação **direta** com a API do Google Drive para backups em nuvem de forma rápida e segura, eliminando a necessidade de servidores intermediários.

## ✨ Principais Funcionalidades

* **Migração Universal:** Suporte para SQL Server, MySQL e PostgreSQL.
* **Modos de Operação:**
    * *Básico:* Migração de tabelas inteiras com interface simplificada.
    * *Avançado:* Extração via Queries SQL (SELECT) customizadas com validação em tempo real.
* **Limpeza e Tratamento de Dados:** * Remoção ou preenchimento de valores nulos.
    * Remoção de linhas duplicadas.
    * Mascaramento de colunas sensíveis (LGPD) ocultando partes do texto com `***`.
* **Estratégias de Carga:** Append (Adicionar), Replace (Substituir) e Inteligente (Filtra registros já existentes via Primary Key).
* **Backups:** * Download de backup local em CSV.
    * Upload direto para o Google Drive via OAuth 2.0.
* **Assistente de IA (V-Nexus Cloud):** Chatbot integrado na barra lateral (conectado via API Render) para auxiliar na criação de scripts e análises de banco de dados.

---

## 🚀 Como Executar o Projeto Localmente

### 1. Pré-requisitos
* **Python 3.9+** instalado.
* **Drivers ODBC** (ex: *ODBC Driver 17 for SQL Server*) instalados na máquina caso vá utilizar o SQL Server.

### 2. Clonando o Repositório e Criando o Ambiente Virtual (.venv)
O uso de um ambiente virtual (`.venv`) é essencial para isolar as dependências do projeto e não causar conflitos no seu computador.

Abra o terminal, navegue até a pasta onde deseja salvar o projeto e execute:

```bash
# 1. Clone o repositório
git clone [https://github.com/AyrtonVilete/sql-smart-migrator.git](https://github.com/AyrtonVilete/sql-smart-migrator.git)
cd sql-smart-migrator

# 2. Crie o ambiente virtual chamado ".venv"
python -m venv .venv

# 3. Ative o ambiente virtual
# No Windows:
.venv\Scripts\activate
# No Linux/Mac:
source .venv/bin/activate

# 4. Instale as dependências necessárias
pip install streamlit pandas sqlalchemy pyodbc pymysql psycopg2-binary google-api-python-client google-auth-httplib2 google-auth-oauthlib requests