"""Sauvegarde automatique de la base SQLite."""

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from config import DATA_DIR, DATABASE_URL

BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 10
BACKUP_INTERVAL_HOURS = 24


def _sqlite_path() -> Path | None:
    if not DATABASE_URL.startswith("sqlite"):
        return None
    # sqlite:///./data/sgiq.db ou sqlite:///C:/path/db
    path_part = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
    p = Path(path_part)
    if not p.is_absolute():
        p = DATA_DIR / p.name if path_part.startswith("./") else Path(path_part)
    return p if p.exists() else DATA_DIR / "sgiq.db"


def create_backup() -> Path | None:
    db_path = _sqlite_path()
    if not db_path or not db_path.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"sgiq_backup_{stamp}.db"
    shutil.copy2(db_path, dest)
    _rotate_backups()
    return dest


def _rotate_backups():
    files = sorted(BACKUP_DIR.glob("sgiq_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[MAX_BACKUPS:]:
        old.unlink(missing_ok=True)


def should_run_auto_backup() -> bool:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    files = list(BACKUP_DIR.glob("sgiq_backup_*.db"))
    if not files:
        return True
    latest = max(files, key=lambda p: p.stat().st_mtime)
    age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
    return age > timedelta(hours=BACKUP_INTERVAL_HOURS)


def run_auto_backup_if_needed() -> Path | None:
    if should_run_auto_backup():
        return create_backup()
    return None


def list_backups() -> list[Path]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(BACKUP_DIR.glob("sgiq_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
