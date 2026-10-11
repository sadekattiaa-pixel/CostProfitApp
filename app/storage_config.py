"""Bootstrap storage configuration used before the database is opened."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import stat
import uuid
import zipfile
import os
import sys
from pathlib import Path


DEFAULT_CONFIG = {
    "portable": False,
    "data_dir": "Data",
    "backup_dir": "",
}

RESTART_EXIT_CODE = 100


def get_executable_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def find_portable_root() -> Path | None:
    override = os.environ.get("COSTPROFIT_PORTABLE_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    executable_dir = get_executable_dir()
    for candidate in (executable_dir, executable_dir.parent):
        if (candidate / "portable-config.json").is_file():
            return candidate
    return None


def get_portable_config_path() -> Path | None:
    root = find_portable_root()
    return root / "portable-config.json" if root else None


def get_installed_config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "CostProfitApp" / "storage-config.json"


def get_storage_config_path() -> Path:
    return get_installed_config_path()


def _valid_storage_config(data) -> bool:
    return (isinstance(data, dict)
            and all(isinstance(data.get(key, ""), str) for key in ("data_dir", "backup_dir"))
            and isinstance(data.get("portable", False), bool))


def is_storage_configured() -> bool:
    if os.environ.get("COSTPROFIT_DATA_DIR", "").strip():
        return True
    path = get_storage_config_path()
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return _valid_storage_config(data) and bool(data.get("data_dir", "").strip())


def load_storage_config() -> dict:
    path = get_storage_config_path()
    if not path.is_file():
        path = get_portable_config_path()
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {**DEFAULT_CONFIG, **data} if _valid_storage_config(data) else {}


def _resolve_config_path(value: str, default: str) -> Path:
    root = find_portable_root() if not get_installed_config_path().exists() else None
    configured = Path(str(value or default)).expanduser()
    if configured.is_absolute():
        return configured.resolve()
    base = root if root is not None else get_storage_config_path().parent
    return (base / configured).resolve()


def get_portable_data_dir() -> Path | None:
    if find_portable_root() is None:
        return None
    config = load_storage_config()
    if not config or not config.get("portable", True):
        return None
    return _resolve_config_path(config.get("data_dir", "Data"), "Data")


def get_portable_backup_dir() -> Path | None:
    if find_portable_root() is None:
        return None
    config = load_storage_config()
    if not config or not config.get("portable", True):
        return None
    return get_configured_backup_dir()


def get_configured_data_dir() -> Path | None:
    override = os.environ.get("COSTPROFIT_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    config = load_storage_config()
    value = str(config.get("data_dir", "")).strip()
    return _resolve_config_path(value, "Data") if value else None


def get_local_state_dir() -> Path:
    return get_installed_config_path().parent


def is_cloud_path(path: Path) -> bool:
    path = path.expanduser().resolve()
    roots = [Path(value) for key in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")
             if (value := os.environ.get(key))]
    roots.extend([Path.home() / "OneDrive", Path.home() / "Google Drive", Path.home() / "My Drive"])
    roots.extend(Path.home().glob("OneDrive - *"))
    return any(path == root.resolve() or root.resolve() in path.parents for root in roots)


def validate_backup_dir(path: Path) -> None:
    path = path.expanduser().resolve()
    data_dir = get_configured_data_dir()
    if is_cloud_path(path) or (data_dir and (path == data_dir or data_dir in path.parents)):
        raise ValueError("النسخ الاحتياطية يجب أن تكون في مجلد محلي خارج OneDrive ومجلد البيانات المشترك.")


def get_configured_backup_dir() -> Path:
    config = load_storage_config()
    value = str(config.get("backup_dir", "")).strip()
    if value and Path(value).is_absolute():
        candidate = Path(value).expanduser().resolve()
        try:
            validate_backup_dir(candidate)
            return candidate
        except ValueError:
            pass
    return get_local_state_dir() / "Backups"


def update_storage_config(*, data_dir: str | None = None, backup_dir: str | None = None) -> Path:
    path = get_storage_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    config = load_storage_config()
    config = {**DEFAULT_CONFIG, **config}
    config["portable"] = find_portable_root() is not None
    if data_dir is not None:
        config["data_dir"] = str(Path(data_dir).expanduser().resolve())
    elif config.get("data_dir") and not Path(config["data_dir"]).is_absolute():
        config["data_dir"] = str(_resolve_config_path(config["data_dir"], "Data"))
    if backup_dir is not None:
        validate_backup_dir(Path(backup_dir))
        config["backup_dir"] = str(Path(backup_dir).expanduser().resolve())
    pending = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".pending")
    try:
        with pending.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(config, ensure_ascii=False, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)
    return path


def ensure_storage_is_writable() -> None:
    data_dir = get_configured_data_dir()
    if data_dir is None:
        raise RuntimeError("A data storage folder has not been selected.")
    data_dir.mkdir(parents=True, exist_ok=True)
    probe = data_dir / ".write-test"
    try:
        probe.write_text("ok", encoding="ascii")
    finally:
        probe.unlink(missing_ok=True)


_runtime_data_dir: Path | None = None


def get_runtime_data_dir() -> Path | None:
    return _runtime_data_dir


def _file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checked_local_tree(path: Path) -> Path:
    path = path.resolve()
    base = get_local_state_dir().resolve()
    if path == base or base not in path.parents:
        raise ValueError("Refusing to change a folder outside local application storage.")
    return path


def make_local_tree_writable(path: Path) -> None:
    """Cloud metadata must not make the application's own image cache read-only."""
    path = _checked_local_tree(path)
    for candidate in [path, *path.rglob("*")]:
        if path != candidate.resolve() and path not in candidate.resolve().parents:
            raise ValueError("Local cache contains a path outside its directory.")
        info = candidate.stat()
        if getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_READONLY:
            candidate.chmod(info.st_mode | stat.S_IWRITE)


def remove_local_tree(path: Path) -> None:
    """Retry read-only cache cleanup without masking ACL or other real failures."""
    path = _checked_local_tree(path)

    def retry_readonly(operation, failed_path, error):
        candidate = Path(failed_path).resolve()
        if candidate != path and path not in candidate.parents:
            raise error
        if not isinstance(error, PermissionError):
            raise error
        info = candidate.stat()
        if not getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_READONLY:
            raise error
        candidate.chmod(info.st_mode | stat.S_IWRITE)
        operation(failed_path)

    shutil.rmtree(path, onexc=retry_readonly)


class RecoveryRequired(RuntimeError):
    pass


class LocalDataSession:
    """Use a durable local copy; publish a closed snapshot for manual cloud sync."""
    def __init__(self, shared_db: Path, shared_images: Path):
        self.shared_db = shared_db.resolve()
        self.shared_images = shared_images.resolve()
        key = hashlib.sha256(str(self.shared_db).casefold().encode()).hexdigest()[:24]
        self.directory = get_local_state_dir() / "Sessions" / key
        self.local_db = self.directory / "app.db"
        self.images = self.directory / "Images"
        self.metadata_path = self.directory / "session.json"
        self.metadata = {}

    def _read_metadata(self):
        if not self.metadata_path.exists():
            return {}
        try:
            data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Invalid session")
            return data
        except (OSError, ValueError) as exc:
            raise RecoveryRequired(f"تعذر قراءة سجل الجلسة المحلية. احتفظ بمحتويات: {self.directory}") from exc

    def _write_metadata(self):
        temporary = self.metadata_path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as output:
            json.dump(self.metadata, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, self.metadata_path)

    def prepare(self, *, recover=False) -> Path:
        global _runtime_data_dir
        self.directory.mkdir(parents=True, exist_ok=True)
        self.metadata = self._read_metadata()
        current = _file_hash(self.shared_db)
        pending = self.metadata.get("state") == "active"
        if pending and self.metadata.get("publication_hash") == current and current is not None:
            # A successful publication does not prove that later local work was saved.
            self.metadata["baseline_hash"] = current
        if pending:
            if not recover:
                raise RecoveryRequired(f"توجد جلسة لم يكتمل نشرها في: {self.directory}")
            if current != self.metadata.get("baseline_hash"):
                raise RecoveryRequired(
                    f"تغيرت البيانات المشتركة بعد الجلسة السابقة. لن يتم استبدالها. "
                    f"احتفظ بنسخة العمل المحلية للاستعادة والمراجعة: {self.directory}"
                )
            if not self.local_db.is_file():
                raise RecoveryRequired("قاعدة الجلسة المحلية مفقودة. لن تُستبدل البيانات المشتركة.")
        else:
            wal = self.shared_db.with_name(self.shared_db.name + "-wal")
            if wal.exists() and wal.stat().st_size > 0:
                raise RecoveryRequired("توجد معاملات WAL في المجلد المشترك. أغلق النسخة السابقة وتأكد من اكتمال مزامنتها أولًا.")
            # Only replace the local cache after a complete, valid new snapshot.
            stage = self.directory / "incoming.db"
            if self.shared_db.exists():
                source = sqlite3.connect(self.shared_db.as_uri() + "?mode=ro", uri=True)
                target = sqlite3.connect(stage)
                try:
                    if source.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                        raise RuntimeError("قاعدة البيانات المشتركة غير سليمة. استخدم نسخة احتياطية.")
                    source.backup(target)
                    target.execute("PRAGMA journal_mode=DELETE")
                finally:
                    target.close()
                    source.close()
                if current != _file_hash(self.shared_db):
                    raise RecoveryRequired("تغيرت البيانات أثناء تحميل الجلسة. انتظر اكتمال المزامنة ثم أعد المحاولة.")
            else:
                stage.unlink(missing_ok=True)
            for suffix in ("-wal", "-shm"):
                self.local_db.with_name(self.local_db.name + suffix).unlink(missing_ok=True)
            if stage.exists():
                os.replace(stage, self.local_db)
            else:
                self.local_db.unlink(missing_ok=True)
            if self.images.exists():
                remove_local_tree(self.images)
            if self.shared_images.exists():
                shutil.copytree(self.shared_images, self.images)
            else:
                self.images.mkdir(parents=True, exist_ok=True)
            make_local_tree_writable(self.images)
            self.metadata = dict(baseline_hash=current, shared_db=str(self.shared_db))
        make_local_tree_writable(self.images)
        self.metadata.update(state="active", publication_hash=None)
        self._write_metadata()
        _runtime_data_dir = self.directory
        return self.local_db

    def archive_pending(self) -> Path:
        """Preserve unfinished local work before an explicit fresh-cloud choice."""
        metadata = self._read_metadata()
        if metadata.get("state") != "active" or not self.local_db.is_file():
            raise RecoveryRequired("لا توجد جلسة محلية قابلة للحفظ والاستعادة.")
        backup_dir = get_configured_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        archive_path = backup_dir / ("unfinished-local-" + uuid.uuid4().hex + ".zip")
        pending = archive_path.with_suffix(".zip.pending")
        snapshot = self.directory / "recovery-snapshot.db"
        try:
            source = sqlite3.connect(self.local_db.as_uri() + "?mode=ro", uri=True)
            target = sqlite3.connect(snapshot)
            try:
                if source.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RecoveryRequired("قاعدة العمل المحلية غير سليمة؛ احتفظ بالمجلد للاستعادة اليدوية.")
                source.backup(target)
                target.execute("PRAGMA journal_mode=DELETE")
            finally:
                target.close()
                source.close()
            with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.write(snapshot, "data/app.db")
                for image in self.images.rglob("*"):
                    if image.is_file():
                        archive.write(image, str(Path("Images") / image.relative_to(self.images)))
            with zipfile.ZipFile(pending) as archive:
                if archive.testzip() is not None:
                    raise OSError("Incomplete recovery archive")
            os.replace(pending, archive_path)
            self.metadata = metadata
            self.metadata.update(state="archived", recovery_archive=str(archive_path))
            self._write_metadata()
            return archive_path
        finally:
            snapshot.unlink(missing_ok=True)
            pending.unlink(missing_ok=True)

    def publish(self, database, session_lock, *, keep_open=False):
        info = session_lock.read_lock()
        if not session_lock._held or not info or info.owner_id != session_lock._owner_id:
            raise RuntimeError("تغير مالك الجلسة. تم الاحتفاظ ببياناتك محليًا دون استبدال البيانات المشتركة.")
        if _file_hash(self.shared_db) != self.metadata.get("baseline_hash"):
            raise RuntimeError(f"تغيرت قاعدة البيانات المشتركة. احتُفظ بتغييراتك في {self.directory} ولم يتم استبدالها.")
        wal = self.shared_db.with_name(self.shared_db.name + "-wal")
        if wal.exists() and wal.stat().st_size > 0:
            raise RuntimeError("قاعدة البيانات المشتركة قيد الاستخدام أو لم تكتمل مزامنتها.")
        self.shared_db.parent.mkdir(parents=True, exist_ok=True)
        stage = self.shared_db.parent / (".invoice-publish-" + uuid.uuid4().hex + ".db")
        image_stages = []
        installed = []
        published = False
        try:
            database.backup_to(stage)
            # Images are separate files; all must finish syncing before handoff.
            self.shared_images.mkdir(parents=True, exist_ok=True)
            desired = set()
            for source in self.images.rglob("*"):
                if not source.is_file():
                    continue
                relative = source.relative_to(self.images)
                desired.add(relative)
                target = self.shared_images / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if _file_hash(source) != _file_hash(target):
                    image_stage = target.with_name("." + target.name + "." + uuid.uuid4().hex + ".pending")
                    image_stages.append((image_stage, target))
                    shutil.copy2(source, image_stage)
            # Check again after staging; never knowingly overwrite a newer database.
            info = session_lock.read_lock()
            if not info or info.owner_id != session_lock._owner_id or _file_hash(self.shared_db) != self.metadata.get("baseline_hash"):
                raise RuntimeError("تغيرت الجلسة أثناء الحفظ. تم الاحتفاظ بنسخة العمل المحلية.")
            self.metadata["publication_hash"] = _file_hash(stage)
            self._write_metadata()
            for incoming, target in image_stages:
                previous = target.with_name("." + target.name + "." + uuid.uuid4().hex + ".previous") if target.exists() else None
                if previous is not None:
                    shutil.copy2(target, previous)
                installed.append((target, previous))
                os.replace(incoming, target)
            os.replace(stage, self.shared_db)
            published = True
            self.metadata["state"] = "active" if keep_open else "closed"
            if keep_open:
                self.metadata["baseline_hash"] = self.metadata["publication_hash"]
                self.metadata["publication_hash"] = None
            self._write_metadata()
            # Old images are removed only after the new database is in place.
            for target in self.shared_images.rglob("*"):
                if target.is_file() and target.relative_to(self.shared_images) not in desired:
                    if self.shared_images.resolve() not in target.resolve().parents:
                        raise RuntimeError("Invalid shared image path")
                    target.unlink()
        finally:
            for target, previous in reversed(installed):
                if not published:
                    if previous is None:
                        target.unlink(missing_ok=True)
                    else:
                        os.replace(previous, target)
                if previous is not None:
                    previous.unlink(missing_ok=True)
            for incoming, _ in image_stages:
                incoming.unlink(missing_ok=True)
            stage.unlink(missing_ok=True)

    def finish(self):
        global _runtime_data_dir
        _runtime_data_dir = None


class _ReadOnlySnapshot:
    """A worker-owned SQLite connection; the UI connection never crosses threads."""
    def __init__(self, path):
        self.path = path

    def backup_to(self, target_path):
        source = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        target = None
        try:
            target = sqlite3.connect(str(target_path))
            source.backup(target)
            target.execute("PRAGMA journal_mode=DELETE")
        finally:
            if target is not None:
                target.close()
            source.close()


class SessionSaveCoordinator:
    """Publish in one worker; use notifications and a periodic image fallback."""
    def __init__(self, session, database, owner, parent=None):
        from PySide6.QtCore import QTimer, QFileSystemWatcher
        from concurrent.futures import ThreadPoolExecutor
        import time
        self.session, self.database, self.owner = session, database, owner
        self.state, self.error = "saving", ""
        self.on_state_changed = None
        self.saved_fingerprint = None
        self.busy = False
        self.dirty = True
        self._generation = 0
        self._future = None
        self._stopped = False
        self._deferred_cleanup = []
        self._next_image_check = time.monotonic() + 30
        self._retry_at = 0
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="invoice-save")
        self.watcher = QFileSystemWatcher(parent)
        if session.images.is_dir():
            self.watcher.addPath(str(session.images))
        self.watcher.directoryChanged.connect(self._images_changed)
        self.timer = QTimer(parent)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        database._conn.set_trace_callback(self._trace)
        database._save_coordinator = self

    def _images_changed(self, *_):
        self._generation += 1
        self.dirty = True
        self._set_state("saving")

    def _trace(self, sql):
        word = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
        if word in ("INSERT", "UPDATE", "DELETE", "REPLACE", "CREATE", "DROP", "ALTER"):
            self._generation += 1
            self.dirty = True
            self._set_state("saving")

    def _image_fingerprint(self):
        result, directories = [], [str(self.session.images)]
        for path in self.session.images.rglob("*"):
            try:
                info = path.stat()
            except FileNotFoundError:
                continue
            if stat.S_ISREG(info.st_mode):
                result.append((str(path.relative_to(self.session.images)), info.st_size, info.st_mtime_ns))
            elif stat.S_ISDIR(info.st_mode):
                directories.append(str(path))
        return tuple(sorted(result)), directories

    def _fingerprint(self):
        images, _ = self._image_fingerprint()
        return (id(self.database._conn), self.database._conn.total_changes, images)

    def _set_state(self, state, error=""):
        self.state, self.error = state, error
        if self.on_state_changed:
            self.on_state_changed(state, error)

    def _publish_worker(self, path, signature, previous, forced):
        before, directories = self._image_fingerprint()
        fingerprint = (*signature, before)
        if forced or fingerprint != previous:
            self.session.publish(_ReadOnlySnapshot(path), self.owner, keep_open=True)
            after, directories = self._image_fingerprint()
            return fingerprint, before != after, directories
        return fingerprint, False, directories

    def _complete(self):
        future = self._future
        self._future = None
        try:
            fingerprint, images_changed, directories = future.result()
            self.saved_fingerprint = fingerprint
            self.dirty = (images_changed or self._generation != self._submitted_generation
                          or self.database._conn is None
                          or (id(self.database._conn), self.database._conn.total_changes) != self._submitted_signature)
            watched = set(self.watcher.directories())
            incoming = set(directories)
            if watched - incoming:
                self.watcher.removePaths(list(watched - incoming))
            if incoming - watched:
                self.watcher.addPaths(list(incoming - watched))
            self._set_state("saving" if self.dirty else "saved")
        except Exception as error:
            import time
            self.dirty = True
            self._retry_at = time.monotonic() + 5
            self._set_state("failed", str(error))
        finally:
            self.busy = False
            actions, self._deferred_cleanup = self._deferred_cleanup, []
            for action in actions:
                try:
                    action()
                except OSError:
                    pass  # A retained unused image is safe; never lose committed data.
            if actions:
                self._images_changed()

    def defer_cleanup(self, action):
        if self.busy:
            self._deferred_cleanup.append(action)
        else:
            action()

    def tick(self):
        import time
        if self._stopped:
            return
        if self._future is not None:
            if self._future.done():
                self._complete()
            return
        if self.database._conn is None or time.monotonic() < self._retry_at:
            return
        if self.database._conn.in_transaction:
            if self.dirty:
                self._set_state("saving")
            return
        due = time.monotonic() >= self._next_image_check
        signature = (id(self.database._conn), self.database._conn.total_changes)
        if not self.dirty and not due and self.saved_fingerprint is not None and signature == self.saved_fingerprint[:2]:
            return
        row = self.database._conn.execute("PRAGMA database_list").fetchone()
        path = Path(row[2]).resolve()
        self._submitted_signature = signature
        self._submitted_generation = self._generation
        self._next_image_check = time.monotonic() + 30
        self.busy = True
        self._set_state("saving")
        self._future = self._executor.submit(self._publish_worker, path, signature, self.saved_fingerprint, self.dirty)

    def suspend(self):
        """Serialize restore/reset with publication, then reattach the new connection."""
        from contextlib import contextmanager
        @contextmanager
        def paused():
            self.timer.stop()
            if self._future is not None:
                self._complete()  # Wait for the worker before replacing any live paths.
            try:
                yield
            finally:
                if not self._stopped and self.database._conn is not None:
                    self.database._conn.set_trace_callback(self._trace)
                    self._images_changed()
                    self.timer.start(1000)
        return paused()

    def stop(self):
        if self._stopped:
            return
        self.timer.stop()
        if self._future is not None:
            self._complete()
        self._stopped = True
        self._executor.shutdown(wait=True)
        watched = self.watcher.directories()
        if watched:
            self.watcher.removePaths(watched)
        if self.database._conn:
            self.database._conn.set_trace_callback(None)
        if getattr(self.database, "_save_coordinator", None) is self:
            self.database._save_coordinator = None
