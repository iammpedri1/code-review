# Code Reviewer

Aplicação local para revisar trechos de código e apontar problemas com linha, evidência e sugestões de correção.

## Como funciona

O projeto tem três serviços:

1. **Frontend Angular** — editor, seleção de linguagem, botão de análise e exibição dos resultados.
2. **API ASP.NET Core** — valida a requisição e encaminha o trecho ao serviço de análise.
3. **Serviço FastAPI** — faz a análise local ou chama a OpenRouter quando a revisão por IA é ativada.

Na análise local, regras simples procuram padrões conhecidos e o código fica na máquina. Na revisão com IA, o serviço Python envia o trecho e a linguagem para a OpenRouter e valida se as linhas e evidências retornadas existem no código. A IA também pode propor o trecho corrigido. O programa **não executa** o código analisado nem aplica a correção automaticamente.

## Executar na sua máquina

### Requisitos

- Docker Desktop (Windows ou macOS) ou Docker Engine (Linux), iniciado.
- Docker Compose v2 (`docker compose`).
- Uma chave OpenRouter somente se quiser usar a revisão por IA. A análise local não precisa de chave.

### 1. Baixar o projeto

Clone o repositório e entre na pasta:

```bash
git clone https://github.com/iammpedri1/code-review.git
cd code-review
```

### 2. Configurar a OpenRouter (opcional)

Na raiz, crie o arquivo local `.env` a partir do exemplo e edite `OPENROUTER_API_KEY` com sua chave:

**Linux/macOS**

```bash
cp .env.example .env
chmod 600 .env
```

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
notepad .env
```

Não cole uma chave real em `.env.example`, no código, no frontend ou em mensagens. O arquivo `.env` é ignorado pelo Git e pelos contextos de build Docker. A chave é entregue ao serviço Python em tempo de execução e não é incluída na imagem.

### 3. Iniciar os serviços

Na raiz do projeto, execute:

```bash
docker compose -p code-reviewer build
docker compose -p code-reviewer up -d
```

Na primeira execução, o Docker baixa as imagens necessárias e compila o frontend, a API e o serviço Python. Quando os containers estiverem iniciados, abra <http://localhost:4200>.

Comandos úteis:

```bash
docker compose -p code-reviewer ps
docker compose -p code-reviewer logs -f
docker compose -p code-reviewer down
```

### Manter a chave fora da pasta do projeto (Linux/macOS)

Como alternativa a `.env`, guarde uma cópia do exemplo em uma pasta privada e preencha a chave:

```bash
mkdir -p "$HOME/.config/code-reviewer"
cp .env.example "$HOME/.config/code-reviewer/openrouter.env"
chmod 600 "$HOME/.config/code-reviewer/openrouter.env"
# Edite openrouter.env: informe sua chave e, se quiser, escolha o modelo.
```

Inicie o Compose passando o arquivo privado:

```bash
docker compose --env-file "$HOME/.config/code-reviewer/openrouter.env" -p code-reviewer build
docker compose --env-file "$HOME/.config/code-reviewer/openrouter.env" -p code-reviewer up -d
```

## Usar o aplicativo

1. Abra <http://localhost:4200>.
2. Escolha a linguagem e cole ou edite o trecho.
3. Deixe **Revisão profunda com OpenRouter** desmarcada para análise local, ou marque para enviar o código à OpenRouter.
4. Clique em **Analisar código**.
5. Confira severidade, linha, evidência e sugestão. Se houver uma proposta de código corrigido, revise-a, aplique manualmente e rode seus testes.

O modo local funciona sem configurar `.env` e sem conexão com um provedor de IA. Na revisão com OpenRouter, os dados enviados são o trecho fornecido e a linguagem; não envie código confidencial ou proprietário se não estiver autorizado a compartilhá-lo com o provedor.

## Modelo e variáveis

| Variável | Finalidade | Padrão |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | Chave da OpenRouter para habilitar revisão por IA. | Sem valor |
| `OPENROUTER_MODEL` | Modelo solicitado à OpenRouter. | `anthropic/claude-sonnet-4.5` |

Modelos alternativos podem ser selecionados em `OPENROUTER_MODEL`, por exemplo `qwen/qwen3-coder-flash` (orientado a código e baixa latência), `openai/gpt-4.1-mini` (rápido/econômico) ou `anthropic/claude-opus-4.6` (revisão mais cuidadosa e geralmente mais lenta/cara). O roteamento pede prioridade de menor latência e permite fallback quando disponível; o desempenho, custo e disponibilidade variam. Consulte o catálogo e os preços atuais da OpenRouter.

## Segurança

- A análise local não envia o código para a OpenRouter.
- A análise com IA envia o trecho ao provedor selecionado; a chave permanece no serviço backend.
- O conteúdo analisado é tratado como dado e nunca é executado pelo app.
- Os containers rodam sem root, descartam capabilities e impedem elevação de privilégios.
- A resposta da IA pode estar errada. Valide qualquer alteração com revisão humana e testes antes de incorporá-la.
- Nunca publique arquivos `.env`, segredos, dumps ou logs com dados sensíveis. Se uma chave for exposta, revogue-a e gere outra.

## Testes e builds

```bash
./.venv/bin/python -m pytest -q
dotnet build backend/CodeReviewer.Api/CodeReviewer.Api.csproj
npm --prefix frontend run build
docker compose -p code-reviewer build
```
