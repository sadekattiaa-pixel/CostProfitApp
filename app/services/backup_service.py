"""Consistent manual and automatic snapshots of the live database and images."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import zipfile
import shutil
import sqlite3
import uuid
import os

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
        pending = target.with_suffix(".zip.pending")
        try:
            db.backup_to(snapshot)
            with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "data/app.db")
                images_dir = get_images_dir()
                if images_dir.exists():
                    for image in images_dir.rglob("*"):
                        if image.is_file():
                            archive.write(image, str(Path("Images") / image.relative_to(images_dir)))
            with zipfile.ZipFile(pending) as archive:
                if archive.testzip() is not None:
                    raise OSError("Incomplete backup archive")
            os.replace(pending, target)
        finally:
            snapshot.unlink(missing_ok=True)
            pending.unlink(missing_ok=True)
        self.prune(prefix=prefix, keep=keep)
        return target

    def restore_backup(self, backup_path: Path) -> None:
        from contextlib import nullcontext
        coordinator = getattr(db, "_save_coordinator", None)
        with coordinator.suspend() if coordinator is not None else nullcontext():
            self._restore_backup(backup_path)

    def _restore_backup(self, backup_path: Path) -> None:
        from app.services.settings_service import settings
        from app.storage_config import get_local_state_dir, remove_local_tree, make_local_tree_writable
        from app.db import schema_loader
        import os
        stage = get_local_state_dir() / "Restore" / uuid.uuid4().hex
        stage.mkdir(parents=True, exist_ok=True)
        cleanup = True
        try:
            with zipfile.ZipFile(backup_path) as archive:
                for member in archive.infolist():
                    destination = (stage / member.filename).resolve()
                    if stage.resolve() not in destination.parents:
                        raise ValueError("Invalid backup path")
                archive.extractall(stage)
            snapshot = stage / "data" / "app.db"
            connection = sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)
            reference = sqlite3.connect(":memory:")
            try:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Invalid backup database")
                reference.executescript(schema_loader.load_schema())
                # These columns have supported migrations for older application backups.
                optional = {"invoices": {"notes2", "archived_snapshot"},
                            "products": {"pattern"}, "invoice_items": {"pallet"}}
                for (table,) in reference.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
                    required = {row[1] for row in reference.execute(f'PRAGMA table_info("{table}")')} - optional.get(table, set())
                    actual = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
                    if not required <= actual:
                        raise ValueError("النسخة لا تحتوي قاعدة بيانات متوافقة مع البرنامج: " + table)
                if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                    raise ValueError("Invalid backup relationships")
            finally:
                reference.close()
                connection.close()
            incoming_images = stage / "incoming-images"
            if (stage / "Images").exists():
                shutil.copytree(stage / "Images", incoming_images)
            else:
                incoming_images.mkdir()
            make_local_tree_writable(incoming_images)
            self.create_backup(prefix="before-restore")
            previous = db.backup_to(stage / "previous.db")
            path, images = get_db_path(), get_images_dir()
            old_images = stage / "previous-images"
            images_moved = False
            incoming_installed = False
            database_installed = False
            db.close()
            try:
                for suffix in ("-wal", "-shm"):
                    path.with_name(path.name + suffix).unlink(missing_ok=True)
                if images.exists():
                    os.replace(images, old_images)
                    images_moved = True
                images.parent.mkdir(parents=True, exist_ok=True)
                os.replace(incoming_images, images)
                incoming_installed = True
                # Copy beside the live DB so replacement remains atomic across drives.
                replacement = path.with_name(path.name + ".restore-" + stage.name)
                try:
                    shutil.copy2(snapshot, replacement)
                    os.replace(replacement, path)
                    database_installed = True
                finally:
                    replacement.unlink(missing_ok=True)
                db.connect(path)
                settings.clear_cache()
            except Exception:
                db.close()
                try:
                    if database_installed:
                        for suffix in ("-wal", "-shm"):
                            path.with_name(path.name + suffix).unlink(missing_ok=True)
                        shutil.copy2(previous, path)
                    if incoming_installed:
                        remove_local_tree(images)
                    if images_moved:
                        os.replace(old_images, images)
                    db.connect(path)
                    settings.clear_cache()
                except Exception as rollback_error:
                    cleanup = False
                    raise RuntimeError(f"تعذرت استعادة الحالة السابقة؛ احتفظ بملفات الاستعادة في {stage}") from rollback_error
                raise
        finally:
            if cleanup:
                remove_local_tree(stage)

    def prune(self, prefix: str = "backup", keep: int = 30) -> None:
        backup_dir = get_auto_backups_dir()
        files = sorted(backup_dir.glob(f"{prefix}_*.zip"), reverse=True)
        for old_file in files[max(1, keep):]:
            old_file.unlink(missing_ok=True)


backup_service = BackupService()
