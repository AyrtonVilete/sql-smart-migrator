Aqui está uma sugestão de `README.md` completo e detalhado para o **SQL Smart Migrator**. Ele foi estruturado para guiar qualquer usuário, desde a preparação do ambiente até a utilização dos recursos mais avançados da ferramenta.

---

# 🔄 SQL Smart Migrator

O **SQL Smart Migrator** é uma ferramenta universal, intuitiva e poderosa desenvolvida em Python e Streamlit para facilitar a migração de dados entre diferentes sistemas de banco de dados (SQL Server, MySQL e PostgreSQL).

Com uma interface amigável, o sistema oferece desde migrações completas de tabelas até um **Modo Avançado** com suporte a queries personalizadas, detecção inteligente de chaves primárias e um Assistente de Inteligência Artificial para auxiliar na construção das suas consultas SQL.

## ✨ Principais Funcionalidades

* **Migrador Universal:** Suporte nativo para transferência de dados entre SQL Server, MySQL e PostgreSQL.
* **Modo Simples e Avançado:** Transfira tabelas inteiras facilmente ou utilize o Modo Avançado para rodar um `SELECT` personalizado e visualizar a amostra de dados antes da migração.
* **Inteligência de Dados:** Detecção automática de Chaves Primárias (PK) e tratamento de duplicatas (modo *Append* e filtragem).
* **Segurança e Backups:** Geração automática de backups locais e na nuvem antes e depois das operações críticas.
* **Assistente de IA Integrado:** Tire dúvidas e gere consultas SQL complexas diretamente na interface através do nosso assistente de Inteligência Artificial.

---

## 🚀 Como Começar

Siga os passos abaixo para configurar o projeto na sua máquina local.

### 1. Pré-requisitos

Certifique-se de ter o **Python 3.8 ou superior** instalado na sua máquina. Você pode baixar a versão mais recente no site oficial: [python.org](https://www.python.org/).

### 2. Clonando o Repositório

Primeiro, faça o clone do projeto para a sua máquina:

```bash
git clone https://github.com/seu-usuario/sql-smart-migrator.git
cd sql-smart-migrator

```

### 3. Criando um Ambiente Virtual (Recomendado)

O ambiente virtual isola as dependências deste projeto para não conflitar com outros projetos Python no seu computador.

**No Windows:**

```bash
python -m venv venv
venv\Scripts\activate

```

**No Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate

```

*(Dica: Quando o ambiente estiver ativado, você verá `(venv)` no início da linha de comando do seu terminal).*

### 4. Instalando as Dependências

Com o ambiente virtual ativado, instale as bibliotecas necessárias utilizando o arquivo `requirements.txt`:

```bash
pip install -r requirements.txt

```

*(Nota: O arquivo `requirements.txt` inclui pacotes essenciais como `streamlit`, bibliotecas de conexão de banco de dados como `psycopg2`, `pymysql`, `pyodbc`, além de `pandas` e `sqlalchemy`).*

---

## 💻 Como Usar a Aplicação

Após instalar as dependências, inicie a interface gráfica rodando o seguinte comando:

```bash
streamlit run Login.py

```

Uma nova aba será aberta automaticamente no seu navegador padrão (geralmente no endereço `http://localhost:8501`).

### Passo a Passo da Migração:

1. **Conexão:** Na barra lateral ou tela inicial, insira as credenciais do **Banco de Dados de Origem** e do **Banco de Dados de Destino**. Teste a conexão para garantir que está tudo certo.
2. **Escolha o Modo de Migração:**
* **Modo Simples:** Selecione a tabela de origem e a tabela de destino para uma cópia direta.
* **Modo Avançado:** Escreva uma query SQL (com a ajuda do Assistente de IA, se precisar) para filtrar colunas específicas, visualizar uma amostra dos dados e mapear as chaves primárias (PK).


3. **Configuração de Inserção:** Defina se a migração irá sobrescrever os dados, fazer um *Append* (adicionar novas linhas) e configure os filtros para evitar duplicidade de dados no destino.
4. **Backup (Opcional):** Acione o recurso de backup local ou em nuvem para garantir a segurança da base de destino antes de injetar os dados.
5. **Migrar:** Clique em "Iniciar Migração" e acompanhe a barra de progresso!

---

## 🛠️ Solução de Problemas (Troubleshooting)

* **Erro de conexão com o Banco:** Verifique se as portas dos bancos (ex: 5432 para Postgres, 3306 para MySQL, 1433 para SQL Server) estão liberadas no seu firewall e se o servidor de banco de dados está rodando.
* **Erro de Driver ODBC (SQL Server):** Caso o sistema apresente falha ao conectar no SQL Server, garanta que você possui o *ODBC Driver for SQL Server* instalado no seu sistema operacional.
* **Comando `streamlit` não reconhecido:** Certifique-se de que o seu ambiente virtual (`venv`) está ativado antes de rodar o comando.

---

## 🤝 Contribuindo

Contribuições são sempre bem-vindas! Sinta-se à vontade para abrir uma *Issue* relatando bugs, ou enviar um *Pull Request* com melhorias para o código ou para a interface.