#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x .venv/bin/python || ! -x frontend/node_modules/.bin/ng ]]; then
  printf 'Dependências não encontradas. Execute ./scripts/setup.sh primeiro.\n' >&2
  exit 1
fi

for ENV_FILE in "$ROOT_DIR/.env" "$HOME/.config/code-reviewer/secrets.env"; do
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # Environment files are trusted, user-managed shell files.
    source "$ENV_FILE"
    set +a
  fi
done

"$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app --app-dir "$ROOT_DIR/ai-service" --host 127.0.0.1 --port 8001 &
PYTHON_PID=$!
dotnet run --project "$ROOT_DIR/backend/CodeReviewer.Api/CodeReviewer.Api.csproj" --urls http://localhost:5000 &
API_PID=$!
npm --prefix "$ROOT_DIR/frontend" start &
FRONTEND_PID=$!

cleanup() {
  trap - EXIT INT TERM
  kill "$FRONTEND_PID" "$API_PID" "$PYTHON_PID" 2>/dev/null || true
  wait "$FRONTEND_PID" "$API_PID" "$PYTHON_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

printf 'Aplicação iniciando. Interface: http://localhost:4200\n'
wait -n "$PYTHON_PID" "$API_PID" "$FRONTEND_PID"
