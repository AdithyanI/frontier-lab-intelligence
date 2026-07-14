#!/usr/bin/env bash
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
GITHUB_ROOT="$(cd "${ROOT_DIR}/.." && pwd)"
SHARED_SCRIPTS_ROOT="${KEYVAULT_SHARED_SCRIPTS_ROOT:-${GITHUB_ROOT}/scripts}"
SHARED_SYNC_PY="${SHARED_SCRIPTS_ROOT}/sync/sync_keyvault_to_repo_env.py"
MAPPING_FILE="${ROOT_DIR}/scripts/local/secrets/keyvault_env_map.env"
OUTPUT_FILE="${ROOT_DIR}/.env"
VAULT_NAME="kv-shared-repos"
PASS_THROUGH_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault-name)
      VAULT_NAME="${2:-}"
      shift 2
      ;;
    --allow-missing|--replace)
      PASS_THROUGH_ARGS+=("$1")
      shift
      ;;
    -h|--help)
      echo "Usage: $(basename "$0") [--vault-name NAME] [--allow-missing] [--replace]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$SHARED_SYNC_PY" ]]; then
  echo "Missing shared secret sync: $SHARED_SYNC_PY" >&2
  exit 2
fi

python3 "$SHARED_SYNC_PY" \
  --vault-name "$VAULT_NAME" \
  --mapping-file "$MAPPING_FILE" \
  --output-file "$OUTPUT_FILE" \
  --apply \
  "${PASS_THROUGH_ARGS[@]}"
