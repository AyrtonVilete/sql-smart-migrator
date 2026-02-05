# CHANGELOG

Todas as mudanças notáveis deste projeto.

Seguindo o formato **Keep a Changelog** e versionamento semântico.

## [Unreleased]

### Added
- Botões para validar a API, a conexão com o banco de dados e as funções do sistema.
- Botão para validar o acesso ao banco de dados.
- Botão para listar os bancos de dados dentro de uma instância SQL.
- Configuração de novos bancos de dados para realizar migração de dados entre bancos.
- Validação "inteligente": caso não exista chave primária, a rotina retorna erro informando a necessidade de uma chave primária.

### Changed
- Modularização do sistema para facilitar manutenção e testes.
- Ajuste no diretório do drive: a pasta de drive agora é criada/definida como oculta.

### Fixed
- Rotina de validação de credenciais em `credencials/`: valida `client_secret.json` e `token.json`; cria novos arquivos válidos caso os existentes estejam inválidos.

## [0.1.0] - 2026-02-05
- Primeira versão pública com as mudanças acima.

---

### Notas de implantação 🔧
- Verificar permissões de acesso na pasta `credencials/`.
- Após atualizar, reinicie o serviço ou aplicação se necessário.
- Para listar bancos em instância SQL, configure porta TCP estática 1433 no SQL Server Configuration Manager:
  1. Abra *SQL Server Configuration Manager* → *SQL Server Network Configuration* → *Protocols for <instância>*.
  2. Clique com o botão direito em **TCP/IP** → **Propriedades** → aba **Endereços IP**.
  3. Role até **IPAll**: apague qualquer valor em **Portas Dinâmicas TCP** (deixe em branco) e defina **Porta TCP** como `1433`.
- Verifique se o firewall permite conexões na porta `1433` para a instância SQL.
