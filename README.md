# Code Reviewer

## O que faz

Aplicação web que revisa trechos de código localmente ou, opcionalmente, usando OpenRouter ou Google Gemini.

## Pré-requisitos

- Docker Engine em execução
- Docker Compose v2 (`docker compose`)

## Como rodar

```bash
cp .env.example .env
# Preencha a chave do provedor de IA que deseja usar.
docker compose -p code-reviewer build
docker compose -p code-reviewer up -d
```

Abra <http://localhost:4200>.

## Variáveis de ambiente

- `OPENAI_API_KEY`: chave OpenRouter; opcional, necessária para usar esse provedor.
- `OPENAI_BASE_URL`: URL da API compatível com OpenAI; padrão `https://openrouter.ai/api/v1`.
- `OPENAI_MODEL`: modelo OpenRouter; padrão `openai/gpt-4.1`.
- `GEMINI_API_KEY`: chave Google Gemini; opcional, necessária para usar esse provedor.
- `GEMINI_MODEL`: modelo Gemini; padrão `gemini-2.5-flash`.
