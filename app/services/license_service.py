"""Automatic offline binding of each application copy to its Windows device."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid


class LicenseError(Exception):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_byte))]


def _blob(data):
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def _device_crypt(data: bytes, *, decrypt=False) -> bytes:
    if os.name != "nt":
        raise LicenseError("Device activation requires Windows.")
    source, buffer = _blob(data)
    entropy, entropy_buffer = _blob(b"Invoice.device-binding.v1")
    output = _DataBlob()
    if decrypt:
        ok = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(source), None, ctypes.byref(entropy), None, None,
            1, ctypes.byref(output),
        )
    else:
        # LOCAL_MACHINE permits Windows users on this computer, not another PC.
        ok = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(source), "Invoice device binding", ctypes.byref(entropy),
            None, None, 5, ctypes.byref(output),
        )
    if not ok:
        raise LicenseError("تعذر التحقق من ربط هذه النسخة بالجهاز؛ قد تكون منقولة من كمبيوتر آخر أو تالفة.")
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free.restype = ctypes.c_void_p
        free(ctypes.cast(output.data, ctypes.c_void_p))


def get_device_fingerprint() -> str:
    if os.name != "nt":
        raise LicenseError("Device activation requires Windows.")
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Cryptography", 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            identity = winreg.QueryValueEx(key, "MachineGuid")[0]
    except OSError as exc:
        raise LicenseError("تعذر قراءة هوية الكمبيوتر. لم يتم إنشاء تفعيل بديل.") from exc
    if not str(identity).strip():
        raise LicenseError("The computer identity is empty.")
    return hashlib.sha256(("Invoice:" + str(identity).strip().lower()).encode()).hexdigest()


def get_binding_path() -> Path:
    if getattr(sys, "frozen", False):
        # Travels with the application copy when moved to another drive.
        return Path(sys.executable).resolve().parent / "License" / "device.dat"
    # Development never adds activation files to the source directory.
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "CostProfitApp" / "development-device.dat"


def read_device_binding(path: Path | None = None) -> dict:
    path = path or get_binding_path()
    try:
        payload = json.loads(_device_crypt(path.read_bytes(), decrypt=True))
        if payload.get("product") != "Invoice" or payload.get("schema") != 1:
            raise ValueError("Invalid device record")
        if payload.get("device_fingerprint") != get_device_fingerprint():
            raise LicenseError("هذه النسخة مرتبطة بكمبيوتر آخر ولا يمكن تشغيلها على هذا الجهاز.")
        if not payload.get("copy_id"):
            raise ValueError("Missing copy identity")
        return payload
    except LicenseError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise LicenseError("سجل التفعيل غير صالح. لن يُعاد ربط النسخة تلقائيًا.") from exc


def verify_device_license(path: Path | None = None) -> dict:
    path = path or get_binding_path()
    if path.exists():
        return read_device_binding(path)
    payload = dict(schema=1, product="Invoice", copy_id=str(uuid.uuid4()),
                   device_fingerprint=get_device_fingerprint(),
                   activated_at=datetime.now(timezone.utc).isoformat())
    protected = _device_crypt(json.dumps(payload, sort_keys=True).encode())
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as output:
            output.write(protected)
            output.flush()
            os.fsync(output.fileno())
    except FileExistsError:
        return read_device_binding(path)
    except OSError as exc:
        raise LicenseError("تعذر حفظ التفعيل. استخدم مجلدًا قابلًا للكتابة لهذه النسخة.") from exc
    return payload


def verify_portable_license() -> dict:
    """Compatibility entry point; installed and portable copies use device binding."""
    return verify_device_license()
