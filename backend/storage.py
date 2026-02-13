from __future__ import annotations

from pathlib import Path


def build_backup_path(*, root: Path, device_type: str, device_ip: str, filename: str) -> Path:
    return root / device_type / device_ip / filename


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, content: str) -> None:
    path.write_text(content)


def resolve_backup_path(*, root: Path, relative_path: str) -> Path:
    candidate = (root / relative_path).resolve()
    resolved_root = root.resolve()
    if resolved_root not in candidate.parents and candidate != resolved_root:
        raise ValueError("Invalid backup path")
    return candidate


def list_backup_files(root: Path) -> list[dict[str, str]]:
    if not root.exists():
        return []
    items: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.txt")):
        if not path.is_file():
            continue
        items.append(
            {
                "path": str(path.relative_to(root)),
                "name": path.name,
                "modified": str(int(path.stat().st_mtime)),
            }
        )
    return items
