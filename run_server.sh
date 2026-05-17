#!/usr/bin/env bash
# Run the API with the macOS CLT Python that has project deps (user site-packages).
# If `python3 -m src.web_server` fails with "No module named 'fastapi'", your PATH
# is picking Homebrew Python without those packages — use this script instead.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT"
exec /usr/bin/python3 -m src.web_server "$@"
