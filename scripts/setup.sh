#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m venv .venv
.venv/bin/python -m pip install -r ai-service/requirements.txt
npm --prefix frontend install
dotnet restore backend/CodeReviewer.Api/CodeReviewer.Api.csproj

printf '\nPreparação concluída. Inicie a aplicação com ./scripts/dev.sh\n'
