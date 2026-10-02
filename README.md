# Code Reviewer

Aplicação web para revisar código, localizar riscos e receber uma proposta de correção com referências a linhas e evidências do próprio trecho.

## Recursos

- Interface Angular, API ASP.NET Core e serviço de análise FastAPI.
- Revisão local sem enviar o código para terceiros.
- Revisão aprofundada opcional via OpenRouter, com achados ancorados em evidências literais e sugestão de código corrigido.
- Execução isolada em containers Docker; o código analisado não é executado.

## Pré-requisitos

- Docker Engine em execução.
- Docker Compose v2 (`docker compose`).

## Configuração

Copie `.env.example` para `.env`, restrinja o acesso ao arquivo e preencha `OPENROUTER_API_KEY` com uma chave da OpenRouter. No Linux, use `chmod 600 .env`. O arquivo `.env` é ignorado pelo Git e pelos contextos de build do Docker.

Para manter a chave fora da pasta do projeto:

```bash
mkdir -p ~/.config/code-reviewer
cp .env.example ~/.config/code-reviewer/secrets.env
chmod 600 ~/.config/code-reviewer/secrets.env
# Edite secrets.env e informe a chave OpenRouter.
```

## Executar com Docker

Com `.env` na raiz:

```bash
docker compose -p code-reviewer build
docker compose -p code-reviewer up -d
```

Com o arquivo privado fora do projeto:

```bash
docker compose --env-file "$HOME/.config/code-reviewer/secrets.env" -p code-reviewer build
docker compose --env-file "$HOME/.config/code-reviewer/secrets.env" -p code-reviewer up -d
```

Abra <http://localhost:4200>. Para acompanhar os serviços, use `docker compose -p code-reviewer logs -f`; para parar, use `docker compose -p code-reviewer down`.

## Variáveis de ambiente

| Variável | Uso | Padrão |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | Chave da OpenRouter; necessária somente para revisão por IA. | — |
| `OPENROUTER_MODEL` | Modelo selecionado na OpenRouter. | `anthropic/claude-sonnet-4.5` |

Modelos para ajustar em `OPENROUTER_MODEL`:

- `anthropic/claude-sonnet-4.5`: recomendado para revisão profunda e correções.
- `qwen/qwen3-coder-flash`: alternativa voltada a código e baixa latência.
- `openai/gpt-4.1-mini`: alternativa rápida e econômica.
- `anthropic/claude-opus-4.6`: revisão mais cuidadosa, normalmente com maior custo e latência.

O serviço solicita roteamento por menor latência e fallback entre provedores disponíveis para o modelo. Disponibilidade, velocidade e preço variam conforme a OpenRouter e podem mudar; confira o catálogo e os custos antes de usar.

## Segurança e privacidade

- A chave fica no serviço Python e é enviada à OpenRouter no header de autorização; nunca configure credenciais no frontend.
- Quando a revisão por IA é habilitada, o trecho de código é enviado à OpenRouter. Desative essa opção para análise local.
- `.env`, chaves privadas, dependências e artefatos estão excluídos do Git ou dos contextos Docker; confira antes de publicar.
- Os containers executam como usuários sem privilégios, descartam capabilities e impedem elevação de privilégios.
- A resposta corrigida é uma sugestão gerada por IA: revise e teste antes de aplicar. A análise não substitui testes, ferramentas estáticas ou revisão profissional.
- Como chaves foram compartilhadas anteriormente, revogue-as e crie novas antes de reutilizá-las.

## Testes e builds

```bash
./.venv/bin/python -m pytest -q
dotnet build backend/CodeReviewer.Api/CodeReviewer.Api.csproj
npm --prefix frontend run build
docker compose -p code-reviewer build
```
