"""Settings service."""
import json
from typing import Any

from app.db import db


DEFAULTS = {
    "language": "en",
    "theme": "dark",
    "date_format": "YYYY-MM-DD",
    "decimal_places": 2,
    "lyd_symbol": "د.ل",
    # Retained as a persistence compatibility key for existing installations.
    "dzd_symbol": "د.ل",
    "usd_symbol": "$",
    "company_name": "",
    "company_address": "",
    "company_phone": "",
    "company_email": "",
    "company_logo": "",
    "auto_lock_minutes": 10,
    "auto_save_seconds": 30,
    "invoice_prefix": "INV-",
    "next_invoice_number": 1,
    "password_hash": "",
    "password_salt": "",
    "security_question": "",
    "security_answer_hash": "",
    "security_answer_salt": "",
    "login_failed_attempts": 0,
    "login_lock_until": 0,
    "show_close_warning": True,
    "safety_copy_on_open": True,
    "auto_backup_minutes": 30,
    "backup_keep_count": 30,
}


class SettingsService:

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        transactional = db._conn is not None and db._conn.in_transaction
        if not transactional and key in self._cache:
            return self._cache[key]
        row = db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        if row:
            value = row["value"]
        elif key in DEFAULTS:
            value = DEFAULTS[key]
        else:
            value = default
        if not transactional:
            self._cache[key] = value
        return value

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(self.get(key, default))
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("1", "true", "yes", "on")

    def set(self, key: str, value: Any) -> None:
        self.set_many({key: value})

    def set_many(self, values: dict[str, Any]) -> None:
        serialized = {}
        for key, value in values.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif isinstance(value, bool):
                value = "1" if value else "0"
            else:
                value = str(value)
            serialized[key] = value
        with db.transaction():
            for key, value in serialized.items():
                db.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )
        for key in serialized:
            self._cache.pop(key, None)

    def clear_cache(self) -> None:
        self._cache.clear()


settings = SettingsService()
