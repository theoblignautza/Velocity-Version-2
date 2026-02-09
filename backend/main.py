from __future__ import annotations

import datetime
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok"}
