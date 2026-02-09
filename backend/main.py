from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.ssh_client import fetch_running_config
from backend.storage import build_backup_path, ensure_parent, write_text

logger = logging.getLogger("backend")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Config Backup API")


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

if _FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets")


class BackupRequest(BaseModel):
    device_ip: str = Field(..., min_length=1, description="Device IP or hostname")
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    device_type: str = Field(..., min_length=1)


class BackupResponse(BaseModel):
    status: str
    device: str
    file: str


def _backup_root() -> Path:
    return Path(os.environ.get("BACKUP_ROOT", "backups"))


def _frontend_index() -> Path | None:
    index_path = _FRONTEND_DIST / "index.html"
    if index_path.exists():
        return index_path
    return None


@app.post("/api/backup-config", response_model=BackupResponse)
async def backup_config(payload: BackupRequest) -> BackupResponse:
    logger.info(
        "backup request received",
        extra={
            "device_ip": payload.device_ip,
            "username": payload.username,
            "device_type": payload.device_type,
        },
    )

    try:
        running_config = fetch_running_config(
            device_ip=payload.device_ip,
            username=payload.username,
            password=payload.password,
            device_type=payload.device_type,
        )
    except RuntimeError as exc:
        logger.error("backup failed", extra={"device_ip": payload.device_ip, "error": str(exc)})
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

    return BackupResponse(status="success", device=payload.device_ip, file=backup_path.name)


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
    return {"status": "ok"}
