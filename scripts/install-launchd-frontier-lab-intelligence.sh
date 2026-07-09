#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_SCRIPT="${ROOT_DIR}/scripts/run-local-production.sh"

LABEL="com.${USER}.frontier-lab-intelligence"
HOST="127.0.0.1"
PORT="8797"
BUILD_NOW=1
INSTALL_DEPS=0
UNINSTALL=0
STATUS_ONLY=0
LOG_LINES=0
HEALTH_WAIT_SECONDS=30
NPM_BIN="${NPM_BIN:-npm}"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-${ROOT_DIR}/.venv/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

usage() {
  cat <<USAGE
Usage: $(basename "$0") [options]

Install/update the Mac mini launchd service for Frontier Lab Intelligence.

Options:
  --label <value>       LaunchAgent label (default: com.<user>.frontier-lab-intelligence)
  --host <host>         Bind host (default: 127.0.0.1)
  --port <n>            Bind port (default: 8797)
  --python <path>       Python binary path (default: .venv/bin/python, then python3)
  --npm <path>          npm binary path (default: npm)
  --install-deps        Run npm ci in frontend before building
  --skip-build-now      Skip one-time frontend build during install
  --uninstall           Unload and remove LaunchAgent plist
  --status              Print launchctl status and local health
  --logs [n]            Tail launchd logs (default lines: 80)
  -h, --help            Show help
USAGE
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

is_int() {
  [[ "${1:-}" =~ ^[0-9]+$ ]]
}

xml_escape() {
  local value="$1"
  value="${value//&/&amp;}"
  value="${value//</&lt;}"
  value="${value//>/&gt;}"
  printf '%s' "$value"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --label)
      LABEL="${2:-}"
      shift 2
      ;;
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:-}"
      shift 2
      ;;
    --npm)
      NPM_BIN="${2:-}"
      shift 2
      ;;
    --install-deps)
      INSTALL_DEPS=1
      shift
      ;;
    --skip-build-now)
      BUILD_NOW=0
      shift
      ;;
    --uninstall)
      UNINSTALL=1
      shift
      ;;
    --status)
      STATUS_ONLY=1
      shift
      ;;
    --logs)
      if [[ -n "${2:-}" && "${2:-}" != --* ]]; then
        LOG_LINES="$2"
        shift 2
      else
        LOG_LINES=80
        shift
      fi
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "$LABEL" ]] || die "missing --label"
[[ -n "$HOST" ]] || die "missing --host"
is_int "$PORT" || die "invalid --port: $PORT"
is_int "$LOG_LINES" || die "invalid --logs value: $LOG_LINES"
command -v "$NPM_BIN" >/dev/null 2>&1 || [[ -x "$NPM_BIN" ]] || die "missing npm binary: $NPM_BIN"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || [[ -x "$PYTHON_BIN" ]] || die "missing python binary: $PYTHON_BIN"
[[ -x "$RUN_SCRIPT" ]] || die "missing run script: $RUN_SCRIPT"

PLIST_PATH="${HOME}/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="${HOME}/.local/state/frontier-lab-intelligence/log"
OUT_LOG="${LOG_DIR}/frontier-lab-intelligence.out.log"
ERR_LOG="${LOG_DIR}/frontier-lab-intelligence.err.log"
DOMAIN="gui/$(id -u)"
LOCAL_HEALTH_URL="http://${HOST}:${PORT}/api/status"

print_status() {
  if ! launchctl list "${LABEL}" 2>/dev/null; then
    echo "LaunchAgent not loaded: ${LABEL}"
  fi

  if curl -fsS "${LOCAL_HEALTH_URL}" >/dev/null 2>&1; then
    echo "Local health: ok"
  else
    echo "Local health: unavailable"
  fi
  echo "Local URL: http://${HOST}:${PORT}/"
  echo "Health URL: ${LOCAL_HEALTH_URL}"
}

wait_for_health() {
  local timeout_seconds="${1:-30}"
  local started_at
  local now
  started_at="$(date +%s)"

  while true; do
    if curl -fsS "${LOCAL_HEALTH_URL}" >/dev/null 2>&1; then
      return 0
    fi

    now="$(date +%s)"
    if (( now - started_at >= timeout_seconds )); then
      return 1
    fi

    sleep 0.5
  done
}

render_plist() {
  cat <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>$(xml_escape "$LABEL")</string>
    <key>ProgramArguments</key>
    <array>
      <string>$(xml_escape "$RUN_SCRIPT")</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(xml_escape "$ROOT_DIR")</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>60</integer>
    <key>StandardOutPath</key>
    <string>$(xml_escape "$OUT_LOG")</string>
    <key>StandardErrorPath</key>
    <string>$(xml_escape "$ERR_LOG")</string>
    <key>EnvironmentVariables</key>
    <dict>
      <key>PATH</key>
      <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
      <key>HOME</key>
      <string>$(xml_escape "$HOME")</string>
      <key>PYTHONPATH</key>
      <string>$(xml_escape "${ROOT_DIR}/src")</string>
      <key>FLI_HOST</key>
      <string>$(xml_escape "$HOST")</string>
      <key>FLI_PORT</key>
      <string>$(xml_escape "$PORT")</string>
      <key>PYTHON_BIN</key>
      <string>$(xml_escape "$PYTHON_BIN")</string>
      <key>NPM_BIN</key>
      <string>$(xml_escape "$NPM_BIN")</string>
    </dict>
  </dict>
</plist>
PLIST
}

if [[ "${STATUS_ONLY}" -eq 1 ]]; then
  print_status
  exit 0
fi

if [[ "${LOG_LINES}" -gt 0 ]]; then
  echo "[logs] stdout: ${OUT_LOG}"
  tail -n "${LOG_LINES}" "${OUT_LOG}" 2>/dev/null || true
  echo "[logs] stderr: ${ERR_LOG}"
  tail -n "${LOG_LINES}" "${ERR_LOG}" 2>/dev/null || true
  exit 0
fi

if [[ "${UNINSTALL}" -eq 1 ]]; then
  launchctl bootout "${DOMAIN}" "${PLIST_PATH}" >/dev/null 2>&1 || true
  rm -f "${PLIST_PATH}"
  echo "Uninstalled ${LABEL}"
  echo "Plist removed: ${PLIST_PATH}"
  exit 0
fi

if [[ "${BUILD_NOW}" -eq 1 ]]; then
  cd "${ROOT_DIR}"
  if [[ "${INSTALL_DEPS}" -eq 1 || ! -d frontend/node_modules ]]; then
    "${NPM_BIN}" --prefix frontend ci
  fi
  "${NPM_BIN}" --prefix frontend run build
fi

mkdir -p "$(dirname "${PLIST_PATH}")" "${LOG_DIR}"
render_plist >"${PLIST_PATH}"
chmod 0644 "${PLIST_PATH}"

launchctl bootout "${DOMAIN}" "${PLIST_PATH}" >/dev/null 2>&1 || true
launchctl bootstrap "${DOMAIN}" "${PLIST_PATH}"
launchctl kickstart -k "${DOMAIN}/${LABEL}" >/dev/null 2>&1 || true

echo "Loaded ${LABEL} from ${PLIST_PATH}"
echo "Logs:"
echo "  ${OUT_LOG}"
echo "  ${ERR_LOG}"
if ! wait_for_health "${HEALTH_WAIT_SECONDS}"; then
  echo "WARNING: local health did not become ready within ${HEALTH_WAIT_SECONDS}s" >&2
fi
print_status
