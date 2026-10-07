"""Lock service for sequential multi-device use."""
import getpass
import os
import sys
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from app.config import STALE_LOCK_THRESHOLD_MINUTES, APP_VERSION
from app.paths import get_lock_file, get_machine_id, get_machine_name


class LockInfo:
    def __init__(self, data: dict):
        self.machine_name = data.get("machine_name", "?")
        self.machine_id = data.get("machine_id", "")
        self.owner_id = data.get("owner_id", "")
        self.process_id = data.get("process_id")
        self.user = data.get("user", "")
        self.opened_at = data.get("opened_at", "")
        self.last_heartbeat = data.get("last_heartbeat", "")
        self.app_version = data.get("app_version", "")

    @property
    def is_stale(self) -> bool:
        try:
            last = datetime.fromisoformat(self.last_heartbeat)
        except (ValueError, TypeError):
            return True
        return datetime.now() - last > timedelta(minutes=STALE_LOCK_THRESHOLD_MINUTES)

    @property
    def is_same_machine(self) -> bool:
        return self.machine_id == get_machine_id()


def _same_machine_process_running(info) -> bool | None:
    """None means a legacy record or an unavailable process check."""
    if not info or not isinstance(info.process_id, int) or info.process_id <= 0:
        return None
    if info.process_id == os.getpid():
        return True
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x00100000, False, info.process_id)
    if not handle:
        return False if ctypes.get_last_error() == 87 else None
    try:
        status = kernel.WaitForSingleObject(handle, 0)
        return False if status == 0 else True if status == 258 else None
    finally:
        kernel.CloseHandle(handle)


class LockService:

    def __init__(self):
        self._lock_path: Path = get_lock_file()
        self._held: bool = False
        self._owner_id = secrets.token_hex(16)

    def read_lock(self) -> LockInfo | None:
        if not self._lock_path.exists():
            return None
        try:
            data = json.loads(self._lock_path.read_text(encoding="utf-8"))
            return LockInfo(data)
        except (json.JSONDecodeError, OSError):
            return None

    def check(self):
        info = self.read_lock()
        if info is None:
            return ("invalid", None) if self._lock_path.exists() else ("free", None)
        if info.is_stale:
            return "stale", info
        if info.is_same_machine:
            return "same_machine", info
        return "other_machine", info

    def acquire(self, force: bool = False) -> bool:
        if self._held:
            info = self.read_lock()
            return bool(info and info.owner_id == self._owner_id)

        status, info = self.check()
        if status == "free":
            try:
                self._write_lock(exclusive=True)
            except FileExistsError:
                return False
            self._held = True
            return True
        if force and status in ("stale", "other_machine", "invalid", "same_machine"):
            self._write_lock()
            self._held = True
            return True
        return False

    def heartbeat(self) -> None:
        if not self._held:
            return
        try:
            data = json.loads(self._lock_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._held = False
            return
        if data.get("owner_id") != self._owner_id:
            self._held = False
            return
        data["last_heartbeat"] = datetime.now().isoformat(timespec="seconds")
        try:
            self._lock_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    def release(self) -> None:
        if not self._held:
            return
        try:
            info = self.read_lock()
            if info and info.owner_id == self._owner_id:
                self._lock_path.unlink()
        except OSError:
            pass
        self._held = False

    def _write_lock(self, exclusive: bool = False) -> None:
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            user = getpass.getuser()
        except Exception:
            user = "user"
        data = {
            "machine_name": get_machine_name(),
            "machine_id": get_machine_id(),
            "owner_id": self._owner_id,
            "process_id": os.getpid(),
            "user": user,
            "opened_at": datetime.now().isoformat(timespec="seconds"),
            "last_heartbeat": datetime.now().isoformat(timespec="seconds"),
            "app_version": APP_VERSION,
        }
        lock_data = json.dumps(data, ensure_ascii=False, indent=2)
        if exclusive:
            with self._lock_path.open("x", encoding="utf-8") as lock_file:
                lock_file.write(lock_data)
        else:
            self._lock_path.write_text(lock_data, encoding="utf-8")


lock = LockService()

def acquire_manual_session(parent=None) -> bool:
    """No automatic expiry: recovery requires an explicit manual decision."""
    from PySide6.QtWidgets import QMessageBox
    lock._lock_path = get_lock_file()
    status, info = lock.check()
    if status == "free":
        return lock.acquire()
    same_local = bool(info and info.is_same_machine)
    if status == "other_machine" or (same_local and _same_machine_process_running(info) is True):
        QMessageBox.warning(parent, "Invoice", "البرنامج مفتوح بالفعل. أغلقه على الجهاز السابق وانتظر اكتمال مزامنة OneDrive.")
        return False
    owner = info.machine_name if info else "غير معروف"
    reply = QMessageBox.question(
        parent, "استعادة جلسة متوقفة",
        f"يوجد قفل جلسة قديمة أو غير مكتملة من الجهاز: {owner}.\n"
        "إذا أوقفت البرنامج بـ Ctrl+C، فتأكد أن النسخة السابقة مغلقة قبل المتابعة.\n"
        "لا تحرر القفل إلا بعد التأكد من توقف الجهاز السابق واكتمال المزامنة. "
        "التغييرات التي لم تُرفع على ذلك الجهاز لن تظهر هنا.\nهل تريد تحرير القفل وبدء جلسة؟",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes and lock.acquire(force=True)
