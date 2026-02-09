from __future__ import annotations

from pathlib import Path


def build_backup_path(*, root: Path, device_type: str, device_ip: str, filename: str) -> Path:
    return root / device_type / device_ip / filename


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content)
