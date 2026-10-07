"""Consistent manual and automatic snapshots of the live database and images."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import zipfile
import shutil
import sqlite3
import uuid

from app.db import db
from app.paths import get_auto_backups_dir, get_default_data_dir, get_images_dir, get_db_path
from app.services.error_logging import log_failures


class BackupService:
    @log_failures("create an automatic backup")
    def create_backup(self, prefix: str = "backup", keep: int = 30) -> Path:
        backup_dir = get_auto_backups_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S_%f")
        target = backup_dir / f"{prefix}_{timestamp}.zip"
        snapshot = backup_dir / f".snapshot_{timestamp}.db"
        db.backup_to(snapshot)
        try:
            with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "data/app.db")
                images_dir = get_images_dir()
                if images_dir.exists():
                    for image in images_dir.rglob("*"):
                        if image.is_file():
                            archive.write(image, str(Path("Images") / image.relative_to(images_dir)))
        finally:
            snapshot.unlink(missing_ok=True)
        self.prune(prefix=prefix, keep=keep)
        return target

    def restore_backup(self, backup_path: Path) -> None:
        from app.services.settings_service import settings
        from app.storage_config import get_local_state_dir, remove_local_tree, make_local_tree_writable
        stage = get_local_state_dir() / "Restore" / uuid.uuid4().hex
        stage.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(backup_path) as archive:
                for member in archive.infolist():
                    destination = (stage / member.filename).resolve()
                    if stage.resolve() not in destination.parents:
                        raise ValueError("Invalid backup path")
                archive.extractall(stage)
            snapshot = stage / "data" / "app.db"
            connection = sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)
            try:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Invalid backup database")
            finally:
                connection.close()
            self.create_backup(prefix="before-restore")
            path = get_db_path()
            images = get_images_dir()
            db.close()
            for suffix in ("-wal", "-shm"):
                path.with_name(path.name + suffix).unlink(missing_ok=True)
            shutil.copy2(snapshot, path)
            if images.exists():
                remove_local_tree(images)
            if (stage / "Images").exists():
                shutil.copytree(stage / "Images", images)
            else:
                images.mkdir(parents=True, exist_ok=True)
            make_local_tree_writable(images)
            db.connect(path)
            settings.clear_cache()
        finally:
            remove_local_tree(stage)

    def prune(self, prefix: str = "backup", keep: int = 30) -> None:
        backup_dir = get_auto_backups_dir()
        files = sorted(backup_dir.glob(f"{prefix}_*.zip"), reverse=True)
        for old_file in files[max(1, keep):]:
            old_file.unlink(missing_ok=True)


backup_service = BackupService()
