#!/usr/bin/env bash
set -euo pipefail

APP_NAME="velocity-config-backup"
APP_DIR="/opt/${APP_NAME}"
SERVICE_NAME="${APP_NAME}.service"
ENV_DIR="/etc/${APP_NAME}"
ENV_FILE="${ENV_DIR}/${APP_NAME}.env"
PYTHON_BIN="${PYTHON_BIN:-python3}"
UVICORN_BIN="${APP_DIR}/.venv/bin/uvicorn"
DEFAULT_USER="${SUDO_USER:-${USER}}"
DEFAULT_GROUP="$(id -gn "${DEFAULT_USER}")"
BACKUP_ROOT_DEFAULT="/var/backups/network-configs"
APP_PORT="${APP_PORT:-8000}"
LOG_PREFIX="[installer]"

usage() {
  cat <<'USAGE'
Usage: ./installer.sh <command>

Commands:
  install    Install backend + frontend and enable the systemd service
  uninstall  Stop and remove service, app files, env files, and optional backup directory
  start      Start the backend service
  stop       Stop the backend service
  restart    Restart the backend service
  status     Show backend service status

Environment overrides:
  APP_DIR                 (default: /opt/velocity-config-backup)
  APP_PORT                (default: 8000)
  BACKUP_ROOT             (default: /var/backups/network-configs)
  FRONTEND_ORIGINS        (default: http://localhost:5173,http://127.0.0.1:5173)
  PYTHON_BIN              (default: python3)
  SKIP_FRONTEND_BUILD=1   (skip npm install/build)
  FORCE_KILL_PORT=1       (free APP_PORT by stopping/killing existing listeners)
  PURGE_BACKUPS=1         (remove BACKUP_ROOT during uninstall)
USAGE
}

log() {
  echo "${LOG_PREFIX} $*"
}

fail() {
  echo "${LOG_PREFIX} ERROR: $*" >&2
  exit 1
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    fail "This command must be run as root (use sudo)."
  fi
}

check_systemd() {
  command -v systemctl >/dev/null 2>&1 || fail "systemctl not found. This installer requires systemd."
}

ensure_package_manager() {
  if command -v apt-get >/dev/null 2>&1; then
    PACKAGE_MANAGER="apt"
    return
  fi
  if command -v dnf >/dev/null 2>&1; then
    PACKAGE_MANAGER="dnf"
    return
  fi
  if command -v yum >/dev/null 2>&1; then
    PACKAGE_MANAGER="yum"
    return
  fi
  fail "No supported package manager found (apt/dnf/yum)."
}

install_packages() {
  ensure_package_manager
  case "${PACKAGE_MANAGER}" in
    apt)
      export DEBIAN_FRONTEND=noninteractive
      log "Installing system dependencies with apt..."
      apt-get update -y
      apt-get install -y python3 python3-venv python3-pip curl rsync lsof iproute2 procps nodejs npm
      ;;
    dnf)
      log "Installing system dependencies with dnf..."
      dnf install -y python3 python3-pip python3-virtualenv curl rsync lsof iproute procps-ng nodejs npm
      ;;
    yum)
      log "Installing system dependencies with yum..."
      yum install -y python3 python3-pip python3-virtualenv curl rsync lsof iproute procps-ng nodejs npm
      ;;
  esac
}

list_port_pids() {
  ss -ltnp "sport = :${APP_PORT}" 2>/dev/null | awk -F 'pid=' 'NR>1 && NF>1 {split($2,a,","); print a[1]}' | tr -d ' ' | sort -u
}

stop_systemd_owner_if_any() {
  local pid="$1"
  local cgroup_file="/proc/${pid}/cgroup"
  [[ -f "${cgroup_file}" ]] || return 0

  local unit
  unit=$(grep -oE '[^/]+\.service' "${cgroup_file}" | head -n1 || true)
  if [[ -n "${unit}" && "${unit}" != "${SERVICE_NAME}" ]]; then
    log "Stopping conflicting systemd unit ${unit} (owns PID ${pid})."
    systemctl disable --now "${unit}" >/dev/null 2>&1 || true
  fi
}

ensure_port_available() {
  local pids
  pids="$(list_port_pids || true)"
  [[ -z "${pids}" ]] && return 0

  if [[ "${FORCE_KILL_PORT:-0}" != "1" ]]; then
    fail "Port ${APP_PORT} is already in use. Re-run with FORCE_KILL_PORT=1 to stop conflicting processes."
  fi

  log "Port ${APP_PORT} is occupied. Attempting cleanup."
  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue
    stop_systemd_owner_if_any "${pid}"
    log "Sending TERM to PID ${pid}."
    kill -TERM "${pid}" >/dev/null 2>&1 || true
  done <<<"${pids}"

  sleep 2
  pids="$(list_port_pids || true)"
  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue
    log "PID ${pid} still using port ${APP_PORT}; sending KILL."
    kill -KILL "${pid}" >/dev/null 2>&1 || true
  done <<<"${pids}"

  sleep 1
  pids="$(list_port_pids || true)"
  [[ -z "${pids}" ]] || fail "Unable to free port ${APP_PORT}."
}

copy_sources() {
  mkdir -p "${APP_DIR}"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --exclude ".git" \
      --exclude "backups" \
      --exclude "node_modules" \
      --exclude ".venv" \
      ./backend ./frontend ./requirements.txt ./README.md "${APP_DIR}/"
  else
    rm -rf "${APP_DIR}/backend" "${APP_DIR}/frontend"
    cp -a ./backend ./frontend ./requirements.txt ./README.md "${APP_DIR}/"
  fi
  chown -R "${DEFAULT_USER}:${DEFAULT_GROUP}" "${APP_DIR}"
}

setup_venv() {
  "${PYTHON_BIN}" -m venv "${APP_DIR}/.venv"
  "${APP_DIR}/.venv/bin/pip" install --upgrade pip
  "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
}

build_frontend() {
  if [[ "${SKIP_FRONTEND_BUILD:-}" == "1" ]]; then
    log "Skipping frontend build (SKIP_FRONTEND_BUILD=1)."
    return
  fi

  command -v npm >/dev/null 2>&1 || fail "npm is required for frontend build; dependency installation failed."
  [[ -f "${APP_DIR}/frontend/package.json" ]] || fail "frontend/package.json not found; cannot build UI."

  log "Installing frontend dependencies..."
  pushd "${APP_DIR}/frontend" >/dev/null
  VITE_API_BASE_URL="" npm install
  log "Building frontend assets..."
  VITE_API_BASE_URL="" npm run build
  popd >/dev/null

  [[ -f "${APP_DIR}/frontend/dist/index.html" ]] || fail "Frontend build did not produce dist/index.html."
}

write_env_file() {
  mkdir -p "${ENV_DIR}"
  local backup_root="${BACKUP_ROOT:-${BACKUP_ROOT_DEFAULT}}"
  local frontend_origins="${FRONTEND_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173}"
  cat >"${ENV_FILE}" <<EOF
BACKUP_ROOT=${backup_root}
FRONTEND_ORIGINS=${frontend_origins}
EOF
  chmod 640 "${ENV_FILE}"
}

write_service_file() {
  cat >/etc/systemd/system/${SERVICE_NAME} <<EOF
[Unit]
Description=Velocity Config Backup API
After=network.target

[Service]
Type=simple
User=${DEFAULT_USER}
Group=${DEFAULT_GROUP}
WorkingDirectory=${APP_DIR}
EnvironmentFile=-${ENV_FILE}
ExecStart=${UVICORN_BIN} backend.main:app --host 0.0.0.0 --port ${APP_PORT}
Restart=on-failure
RestartSec=5
KillMode=control-group

[Install]
WantedBy=multi-user.target
EOF
}

verify_service() {
  systemctl is-active --quiet "${SERVICE_NAME}" || fail "Service failed to start. Check: journalctl -u ${SERVICE_NAME}"
  local health_url="http://127.0.0.1:${APP_PORT}/health"
  if ! curl --fail --silent --show-error --max-time 10 "${health_url}" >/dev/null; then
    fail "Service started but health check failed at ${health_url}"
  fi
}

install_service() {
  require_root
  check_systemd
  install_packages
  ensure_port_available
  copy_sources
  setup_venv
  build_frontend
  write_env_file
  write_service_file
  systemctl daemon-reload
  systemctl enable --now "${SERVICE_NAME}"
  verify_service
  log "Installed and started ${SERVICE_NAME} on port ${APP_PORT}."
}

uninstall_service() {
  require_root
  check_systemd
  systemctl disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/${SERVICE_NAME}"
  systemctl daemon-reload
  systemctl reset-failed >/dev/null 2>&1 || true

  local backup_root="${BACKUP_ROOT:-${BACKUP_ROOT_DEFAULT}}"
  if [[ "${PURGE_BACKUPS:-0}" == "1" ]]; then
    log "Purging backup directory ${backup_root}."
    rm -rf "${backup_root}"
  fi

  rm -rf "${ENV_DIR}" "${APP_DIR}"
  log "Uninstalled ${SERVICE_NAME}."
}

service_cmd() {
  require_root
  check_systemd
  systemctl "$1" "${SERVICE_NAME}"
}

case "${1:-}" in
  install)
    install_service
    ;;
  uninstall)
    uninstall_service
    ;;
  start|stop|restart|status)
    service_cmd "${1}"
    ;;
  *)
    usage
    exit 1
    ;;
esac
