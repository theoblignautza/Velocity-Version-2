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

usage() {
  cat <<'USAGE'
Usage: ./installer.sh <command>

Commands:
  install    Install the backend service and enable it
  uninstall  Stop and remove the backend service and files
  start      Start the backend service
  stop       Stop the backend service
  restart    Restart the backend service
  status     Show backend service status

Environment overrides:
  APP_DIR            (default: /opt/velocity-config-backup)
  BACKUP_ROOT        (default: /var/backups/network-configs)
  FRONTEND_ORIGINS   (default: http://localhost:5173,http://127.0.0.1:5173)
  PYTHON_BIN         (default: python3)
  SKIP_FRONTEND_BUILD=1 (skip npm install/build if set)
USAGE
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "This command must be run as root (use sudo)." >&2
    exit 1
  fi
}

check_systemd() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl not found. This installer requires systemd." >&2
    exit 1
  fi
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
}

setup_venv() {
  "${PYTHON_BIN}" -m venv "${APP_DIR}/.venv"
  "${APP_DIR}/.venv/bin/pip" install --upgrade pip
  "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
}

build_frontend() {
  if [[ "${SKIP_FRONTEND_BUILD:-}" == "1" ]]; then
    echo "Skipping frontend build (SKIP_FRONTEND_BUILD=1)."
    return
  fi
  if [[ -f "${APP_DIR}/frontend/dist/index.html" ]]; then
    echo "Frontend build already present. Skipping build."
    return
  fi
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found and no frontend build present." >&2
    echo "Install Node/npm or re-run with SKIP_FRONTEND_BUILD=1 to proceed without the UI." >&2
    exit 1
  fi
  if [[ ! -f "${APP_DIR}/frontend/package.json" ]]; then
    echo "frontend package.json not found; cannot build UI." >&2
    exit 1
  fi
  echo "Building frontend..."
  pushd "${APP_DIR}/frontend" >/dev/null
  VITE_API_BASE_URL="" npm install
  VITE_API_BASE_URL="" npm run build
  popd >/dev/null
  if [[ ! -f "${APP_DIR}/frontend/dist/index.html" ]]; then
    echo "Frontend build did not produce dist/index.html; aborting." >&2
    exit 1
  fi
}

write_env_file() {
  mkdir -p "${ENV_DIR}"
  local backup_root="${BACKUP_ROOT:-${BACKUP_ROOT_DEFAULT}}"
  local frontend_origins="${FRONTEND_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173}"
  cat >"${ENV_FILE}" <<EOF
BACKUP_ROOT=${backup_root}
FRONTEND_ORIGINS=${frontend_origins}
EOF
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
ExecStart=${UVICORN_BIN} backend.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
}

install_service() {
  require_root
  check_systemd
  copy_sources
  setup_venv
  build_frontend
  write_env_file
  write_service_file
  systemctl daemon-reload
  systemctl enable --now "${SERVICE_NAME}"
  echo "Installed and started ${SERVICE_NAME}."
}

uninstall_service() {
  require_root
  check_systemd
  systemctl disable --now "${SERVICE_NAME}" >/dev/null 2>&1 || true
  rm -f "/etc/systemd/system/${SERVICE_NAME}"
  systemctl daemon-reload
  rm -rf "${ENV_DIR}" "${APP_DIR}"
  echo "Uninstalled ${SERVICE_NAME}."
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
