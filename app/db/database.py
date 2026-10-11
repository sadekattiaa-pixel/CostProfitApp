"""Database access layer."""
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from app.paths import get_db_path
from app.db import schema_loader
from app.services.error_logging import log_failures


class Database:
    _instance = None
    _conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @log_failures("open the database")
    def connect(self, db_path: Path | None = None) -> None:
        if self._conn is not None:
            return
        path = db_path or get_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = FULL")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        schema = schema_loader.load_schema()
        self._conn.executescript(schema)
        invoice_columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(invoices)")}
        for name in ("notes2", "archived_snapshot"):
            if name not in invoice_columns:
                self._conn.execute(f"ALTER TABLE invoices ADD COLUMN {name} TEXT")
        product_columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(products)")}
        if "pattern" not in product_columns:
            self._conn.execute("ALTER TABLE products ADD COLUMN pattern TEXT")
        item_columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(invoice_items)")
        }
        if "pallet" not in item_columns:
            self._conn.execute("ALTER TABLE invoice_items ADD COLUMN pallet INTEGER")
        self._conn.commit()
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        cur = self._conn.execute("SELECT COUNT(*) FROM expense_templates")
        if cur.fetchone()[0] == 0:
            from app.config import DEFAULT_EXPENSE_ITEMS
            for i, label in enumerate(DEFAULT_EXPENSE_ITEMS):
                self._conn.execute(
                    "INSERT INTO expense_templates (label, is_default, sort_order) VALUES (?, 1, ?)",
                    (label, i),
                )
            self._conn.commit()

    @contextmanager
    def cursor(self):
        with self.transaction():
            cur = self._conn.cursor()
            try:
                yield cur
            finally:
                cur.close()

    def after_commit(self, action):
        frames = getattr(self, "_commit_actions", [])
        if not frames:
            raise RuntimeError("A managed transaction is required.")
        frames[-1].append(action)

    @contextmanager
    def transaction(self, immediate: bool = False):
        """Commit nested service operations only with their owning transaction."""
        if self._conn is None:
            raise RuntimeError("Database is not connected.")
        frames = getattr(self, "_commit_actions", None)
        if frames is None:
            frames = self._commit_actions = []
        nested = self._conn.in_transaction
        savepoint = "sp_" + uuid.uuid4().hex
        if nested:
            self._conn.execute(f"SAVEPOINT {savepoint}")
        else:
            self._conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
        actions = []
        frames.append(actions)
        try:
            yield
            if nested:
                self._conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            else:
                self._conn.commit()
        except BaseException:
            if nested:
                self._conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                self._conn.execute(f"RELEASE SAVEPOINT {savepoint}")
            else:
                self._conn.rollback()
            raise
        finally:
            frames.pop()
        if nested and frames:
            frames[-1].extend(actions)
        elif not nested:
            for action in actions:
                coordinator = getattr(self, "_save_coordinator", None)
                if coordinator is not None:
                    coordinator.defer_cleanup(action)
                else:
                    action()
        # An unmanaged outer transaction cannot safely schedule file deletion.

    def execute(self, sql: str, params: Iterable = ()):
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, seq: Iterable):
        return self._conn.executemany(sql, seq)

    def query_one(self, sql: str, params: Iterable = ()) -> dict | None:
        cur = self._conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def query_all(self, sql: str, params: Iterable = ()) -> list[dict]:
        cur = self._conn.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]

    @log_failures("create a database backup")
    def backup_to(self, target_path: str | Path) -> Path:
        if self._conn is None:
            raise RuntimeError("Database is not connected.")

        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        self._conn.execute("PRAGMA wal_checkpoint(FULL)")
        backup_conn = sqlite3.connect(str(target))
        try:
            self._conn.backup(backup_conn)
            backup_conn.execute("PRAGMA journal_mode = DELETE")
        finally:
            backup_conn.close()

        return target

    @log_failures("reset the database")
    def reset(self, db_path: Path | None = None) -> None:
        from contextlib import nullcontext
        coordinator = getattr(self, "_save_coordinator", None)
        with coordinator.suspend() if coordinator is not None else nullcontext():
            self._reset(db_path)

    def _reset(self, db_path: Path | None = None) -> None:
        path = db_path or get_db_path()
        path = Path(path)
        was_connected = self._conn is not None
        if self._conn is not None:
            try:
                self._conn.execute("PRAGMA wal_checkpoint(FULL)")
                self._conn.commit()
            except sqlite3.Error:
                pass
            self.close()

        for candidate in (
            path,
            path.with_name(path.name + "-wal"),
            path.with_name(path.name + "-shm"),
        ):
            try:
                if candidate.exists():
                    candidate.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                if was_connected:
                    try:
                        self.connect(path)
                    except (OSError, sqlite3.Error):
                        pass
                raise

        if was_connected:
            from app.services.settings_service import settings
            settings.clear_cache()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            Database._instance = None


db = Database()
