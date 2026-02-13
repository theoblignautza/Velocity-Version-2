from __future__ import annotations

import asyncio
import datetime
import logging
import os
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.discovery import scan_network, validate_subnet
from backend.log_stream import LogStream
from backend.ssh_client import fetch_running_config, restore_running_config
from backend.storage import (
    build_backup_path,
    ensure_parent,
    list_backup_files,
    resolve_backup_path,
    write_text,
)

logger = logging.getLogger("backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Config Backup API")
log_stream = LogStream()


def _cors_origins() -> list[str]:
    raw_origins = os.environ.get("FRONTEND_ORIGINS", "")
    if not raw_origins:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists() and (_FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")


def _cors_origins() -> list[str]:
    raw_origins = os.environ.get("FRONTEND_ORIGINS", "")
    if not raw_origins:
        return ["http://localhost:5173", "http://127.0.0.1:5173"]
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BackupRequest(BaseModel):
    device_ip: str = Field(..., min_length=1, description="Device IP or hostname")
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    device_type: str = Field(..., min_length=1)
    protocol: Literal["ssh", "telnet"] = "ssh"


class BackupResponse(BaseModel):
    status: str
    device: str
    file: str


class DiscoverRequest(BaseModel):
    subnet: str = Field(..., description="IPv4 subnet CIDR, e.g. 192.168.1.0/24")


class RestoreRequest(BaseModel):
    device_ip: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    device_type: str = Field(..., min_length=1)
    protocol: Literal["ssh", "telnet"] = "ssh"
    backup_file: str = Field(..., min_length=1)


def _backup_root() -> Path:
    return Path(os.environ.get("BACKUP_ROOT", "backups"))


def _frontend_index() -> Path | None:
    index_path = _FRONTEND_DIST / "index.html"
    if index_path.exists():
        return index_path
    return None


@app.post("/api/backup-config", response_model=BackupResponse)
async def backup_config(payload: BackupRequest) -> BackupResponse:
    await log_stream.publish(f"Backup requested for {payload.device_ip} via {payload.protocol}")

    try:
        running_config = await asyncio.to_thread(
            fetch_running_config,
            device_ip=payload.device_ip,
            username=payload.username,
            password=payload.password,
            device_type=payload.device_type,
            protocol=payload.protocol,
        )
    except RuntimeError as exc:
        await log_stream.publish(f"Backup failed for {payload.device_ip}: {exc}", level="error")
        raise HTTPException(status_code=500, detail="Backup failed") from exc

    timestamp = datetime.date.today().isoformat()
    backup_path = build_backup_path(
        root=_backup_root(),
        device_type=payload.device_type,
        device_ip=payload.device_ip,
        filename=f"running-config_{timestamp}.txt",
    )
    ensure_parent(backup_path)
    write_text(backup_path, running_config)
    await log_stream.publish(f"Backup complete for {payload.device_ip}: {backup_path.name}")

    return BackupResponse(status="success", device=payload.device_ip, file=str(backup_path.relative_to(_backup_root())))


@app.get("/api/backups")
async def backups_list() -> dict[str, Any]:
    files = list_backup_files(_backup_root())
    return {"files": files}


@app.get("/api/backups/content")
async def backup_content(path: str = Query(..., min_length=1)) -> dict[str, str]:
    try:
        target = resolve_backup_path(root=_backup_root(), relative_path=path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Backup file not found")
    return {"path": path, "content": target.read_text()}


@app.post("/api/restore-config")
async def restore_config(payload: RestoreRequest) -> dict[str, str]:
    try:
        source = resolve_backup_path(root=_backup_root(), relative_path=payload.backup_file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not source.exists() or not source.is_file():
        raise HTTPException(status_code=404, detail="Backup file not found")

    await log_stream.publish(
        f"Restore requested for {payload.device_ip} using {payload.backup_file} via {payload.protocol}"
    )
    config_text = source.read_text()

    try:
        await asyncio.to_thread(
            restore_running_config,
            device_ip=payload.device_ip,
            username=payload.username,
            password=payload.password,
            device_type=payload.device_type,
            protocol=payload.protocol,
            config_text=config_text,
        )
    except RuntimeError as exc:
        await log_stream.publish(f"Restore failed for {payload.device_ip}: {exc}", level="error")
        raise HTTPException(status_code=500, detail="Restore failed") from exc

    await log_stream.publish(f"Restore completed for {payload.device_ip}")
    return {"status": "success", "device": payload.device_ip, "file": payload.backup_file}


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"timestamp": datetime.datetime.utcnow().isoformat(), "level": "info", "message": "Connected to live logs"})
    try:
        async for event in log_stream.subscribe():
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return


@app.get("/")
async def frontend() -> FileResponse:
    index_path = _frontend_index()
    if not index_path:
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_path)


@app.get("/{full_path:path}")
async def frontend_fallback(full_path: str) -> FileResponse:
    if full_path.startswith("api") or full_path.startswith("health") or full_path.startswith("ws"):
        raise HTTPException(status_code=404, detail="Not Found")
    asset_path = _FRONTEND_DIST / full_path
    if asset_path.exists() and asset_path.is_file():
        return FileResponse(asset_path)
    index_path = _frontend_index()
    if not index_path:
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_path)


@app.get("/")
async def frontend() -> FileResponse:
    index_path = _frontend_index()
    if not index_path:
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_path)


@app.get("/{full_path:path}")
async def frontend_fallback(full_path: str) -> FileResponse:
    if full_path.startswith("api") or full_path.startswith("health"):
        raise HTTPException(status_code=404, detail="Not Found")
    asset_path = _FRONTEND_DIST / full_path
    if asset_path.exists() and asset_path.is_file():
        return FileResponse(asset_path)
    index_path = _frontend_index()
    if not index_path:
        raise HTTPException(status_code=404, detail="Frontend build not found")
    return FileResponse(index_path)


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "host": "0.0.0.0"}
