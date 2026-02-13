# Backend/Frontend Responsibilities Overview

## Big picture: what the backend is

Think of the backend as a secure middleman that:

- Receives credentials and device info from the dashboard.
- Uses an SSH library to connect to a Cisco device.
- Runs commands (for example, `show running-config`).
- Collects the output.
- Saves it on the server (local host).
- Sends status/results back to the frontend.

The frontend never talks to the switch directly.

```
[ Browser Dashboard ]
        |
        | HTTPS (JSON)
        v
[ Backend API Server ]
        |
        | SSH
        v
[ Cisco Switch / Router ]
```

## Frontend role (what the dashboard does)

The frontend is intentionally thin. It only:

- Collects inputs.
- Sends a request.
- Displays results.

### Example fields in the dashboard

- Device IP / hostname
- SSH username
- SSH password (or key reference)
- Device type (IOS / IOS-XE / NX-OS)
- Button: **Backup Config**

### What it sends to the backend

```json
{
  "device_ip": "10.0.0.5",
  "username": "admin",
  "password": "secret",
  "device_type": "cisco_ios"
}
```

### Important rule

The frontend:

- Does **not** store credentials.
- Does **not** open SSH.
- Does **not** save config files.

## Backend role (where the work happens)

The backend is a service (Python, Node, Go—Python is most common for network automation).

### 1. API endpoint

Example:

```
POST /api/backup-config
```

The backend:

- Receives JSON.
- Validates inputs.
- Logs the request (without passwords).

### 2. SSH connection layer

The backend uses an SSH library:

- Netmiko (most common for Cisco)
- Paramiko (lower-level)
- NAPALM (more structured, multi-vendor)

For Cisco, Netmiko is the sweet spot.

Conceptually:

```
connect_to_device()
send_command("show running-config")
get_output()
disconnect()
```

### 3. Command execution

The backend runs:

```
show running-config
```

The output comes back as plain text.

Example:

```
hostname SW1
interface GigabitEthernet1/0/1
 switchport access vlan 10
...
```

This is a big string in memory.

### 4. File handling (saving locally)

The backend decides:

- Where to store configs.
- How to name them.

Example naming strategy:

```
/backups/
  └── cisco/
      └── 10.0.0.5/
          └── running-config_2026-02-09.txt
```

The backend:

- Creates folders if missing.
- Writes the file.
- Sets permissions.

This happens on the server, not the user’s PC.

### 5. Response back to frontend

The backend sends something like:

```json
{
  "status": "success",
  "device": "10.0.0.5",
  "file": "running-config_2026-02-09.txt"
}
```

Frontend just shows:

- ✅ Backup successful
- 📁 File saved on server

## Setup (Ubuntu/Linux)

### 1. Install system prerequisites

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run the API server

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Optional: set a custom backup root directory (defaults to `./backups`):

```bash
export BACKUP_ROOT=/var/backups/network-configs
```

### 4. Call the API

```bash
curl -X POST http://localhost:8000/api/backup-config \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "10.0.0.5",
    "username": "admin",
    "password": "secret",
    "device_type": "cisco_ios"
  }'
```

### Notes

- `device_type` must match a Netmiko platform string (examples: `cisco_ios`, `cisco_xe`, `cisco_nxos`). See Netmiko docs for the full list.
- You must have network reachability from the server to the device (or a lab like CML/GNS3/EVE-NG).

## Installer (systemd service)

The `installer.sh` script installs the backend API as a persistent systemd service on Linux. It also builds the Vite frontend so the UI is served at `http://<host>:8000/`. If `npm` is missing and no prebuilt UI exists, the installer will stop and prompt you to install Node/npm or explicitly skip the UI build.

```bash
sudo ./installer.sh install
```

### Lifecycle commands

```bash
sudo ./installer.sh start
sudo ./installer.sh stop
sudo ./installer.sh restart
sudo ./installer.sh status
sudo ./installer.sh uninstall
```

### Configuration overrides

You can override defaults using environment variables:

```bash
sudo BACKUP_ROOT=/var/backups/network-configs \
  FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173 \
  ./installer.sh install
```

If you want to skip the frontend build (or you do not have Node/npm on the server):

```bash
sudo SKIP_FRONTEND_BUILD=1 ./installer.sh install
```

## New capabilities

- **Discover Switches**: Use `POST /api/discover-switches` with subnet CIDR to discover hosts exposing SSH/Telnet.
- **Live logs**: Connect to `ws://<host>:8000/ws/logs` for real-time progress events.
- **Backup catalog**: `GET /api/backups` lists backed-up config files.
- **Config content view**: `GET /api/backups/content?path=<relative-path>` returns file content.
- **Restore**: `POST /api/restore-config` restores a selected backup over SSH or Telnet.

## Security hardening

- Backup file access is constrained to `BACKUP_ROOT` via canonical path validation.
- Subnet input for discovery is validated as IPv4 CIDR and capped to 4096 addresses.
- Protocol selection is restricted to `ssh`/`telnet` through strict schema validation.
- Frontend default API target is same-origin to avoid external-LAN localhost mismatches.

## API examples

### Discover devices

```bash
curl -X POST http://192.168.50.249:8000/api/discover-switches \
  -H "Content-Type: application/json" \
  -d '{"subnet": "192.168.50.0/24"}'
```

### List backups

```bash
curl http://192.168.50.249:8000/api/backups
```

### Restore backup

```bash
curl -X POST http://192.168.50.249:8000/api/restore-config \
  -H "Content-Type: application/json" \
  -d '{
    "device_ip": "192.168.50.20",
    "username": "admin",
    "password": "secret",
    "device_type": "cisco_ios",
    "protocol": "ssh",
    "backup_file": "cisco_ios/192.168.50.20/running-config_2026-02-09.txt"
  }'
```
