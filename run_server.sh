#!/usr/bin/env bash
# Run the SelfSmart API via uvicorn (src.api.main).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload "$@"
