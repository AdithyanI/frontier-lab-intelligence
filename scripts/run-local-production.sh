#!/usr/bin/env bash
set -euo pipefail

# launchd entrypoint for the Frontier Lab Intelligence local production UI.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${FLI_HOST:-127.0.0.1}"
PORT="${FLI_PORT:-8797}"
FRONTEND_DIR="${ROOT_DIR}/frontend"
DIST_INDEX="${ROOT_DIR}/src/fli/web/dist/index.html"
NPM_BIN="${NPM_BIN:-npm}"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

cd "${ROOT_DIR}"

if [[ ! -f "${DIST_INDEX}" ]]; then
  echo "Built web UI missing at ${DIST_INDEX}; building..." >&2
  if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
    "${NPM_BIN}" --prefix "${FRONTEND_DIR}" ci
  fi
  "${NPM_BIN}" --prefix "${FRONTEND_DIR}" run build
fi

if [[ ! -f "data/fli.db" ]]; then
  echo "Missing data/fli.db; load graph data before serving production UI." >&2
  exit 1
fi

export PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
export FLI_HOST="${HOST}"
export FLI_PORT="${PORT}"

exec "${PYTHON_BIN}" -m fli.cli web --host "${HOST}" --port "${PORT}"
