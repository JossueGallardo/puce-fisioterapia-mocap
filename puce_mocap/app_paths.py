"""Rutas locales de datos que nunca dependen del directorio de instalación."""

from __future__ import annotations

import os
from pathlib import Path


def data_dir() -> Path:
    override = os.environ.get("PUCE_MOCAP_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "PUCE MoCap Fisioterapia"


def reports_dir() -> Path:
    path = data_dir() / "reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def profiles_dir() -> Path:
    """Directorio local para perfiles editables, siempre fuera del repositorio."""
    path = data_dir() / "perfiles"
    path.mkdir(parents=True, exist_ok=True)
    return path
