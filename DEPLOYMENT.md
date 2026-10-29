# Configuração e publicação

## Variáveis de ambiente

Configure no ambiente de hospedagem:

- `FLASK_SECRET_KEY`: valor aleatório forte usado para assinar sessões. A aplicação não inicia sem essa variável.
- `GEMINI_API_KEY`: chave da API do Gemini, necessária para gerar materiais.
- `MISTRAL_API_KEY`: opcional; usada como provedor alternativo.
- `DEVELOPER_EMAIL` e `DEVELOPER_PASSWORD`: configure as duas juntas para criar ou provisionar a conta desenvolvedora. A senha deve ter pelo menos 12 caracteres. Ela é aplicada à conta em cada inicialização.
- `DEVELOPER_NAME` e `DEVELOPER_SCHOOL`: opcionais; personalizam os dados da conta desenvolvedora.

Gere uma chave de sessão com:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Nunca use a chave gerada como senha da conta e nunca a envie ao Git.

## Banco de dados

O app cria e migra o SQLite em `database.db`. Em hospedagens com sistema de arquivos efêmero, configure um disco persistente ou substitua o SQLite por um banco gerenciado antes de depender da permanência dos dados.

Os arquivos SQLite que já foram commitados continuam no histórico do Git mesmo depois de adicionados ao `.gitignore`. Se contiverem dados reais, remova-os do repositório e do histórico com um procedimento de migração planejado, preserve os dados necessários em armazenamento seguro e troque senhas ou credenciais que possam ter sido expostas.
