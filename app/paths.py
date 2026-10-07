"""Paths management."""
import os
import platform
import uuid
from pathlib import Path

from app.storage_config import get_configured_backup_dir, get_configured_data_dir, get_runtime_data_dir, get_local_state_dir


def get_app_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _find_cloud_drive() -> Path | None:
    home = Path.home()
    candidates = [
        Path(os.environ["OneDriveCommercial"]) if os.environ.get("OneDriveCommercial") else None,
        Path(os.environ["OneDriveConsumer"]) if os.environ.get("OneDriveConsumer") else None,
        Path(os.environ["OneDrive"]) if os.environ.get("OneDrive") else None,
        home / "OneDrive",
        home / "Google Drive",
        home / "My Drive",
    ]
    if platform.system() == "Windows":
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            candidates.extend([
                Path(user_profile) / "OneDrive",
                Path(user_profile) / "Google Drive",
            ])
    for c in candidates:
        if c is not None and c.exists() and c.is_dir():
            return c
    return None


def get_default_data_dir() -> Path:
    configured = os.environ.get("COSTPROFIT_DATA_DIR", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    selected_dir = get_configured_data_dir()
    if selected_dir is not None:
        return selected_dir
    cloud_drive = _find_cloud_drive()
    if cloud_drive:
        return cloud_drive / "CostProfitApp"
    return Path.home() / "CostProfitApp"


def get_machine_id_file() -> Path:
    if platform.system() == "Windows":
        base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base_dir = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base_dir / "CostProfitApp" / "machine.id"


def get_machine_id() -> str:
    file = get_machine_id_file()
    file.parent.mkdir(parents=True, exist_ok=True)
    if file.exists():
        return file.read_text().strip()
    machine_id = str(uuid.uuid4())
    file.write_text(machine_id)
    return machine_id


def get_machine_name() -> str:
    return platform.node() or "Unknown-PC"


def get_shared_db_path() -> Path:
    selected_dir = get_configured_data_dir()
    if selected_dir is not None:
        legacy_path = selected_dir / "data" / "app.db"
        if not (selected_dir / "app.db").exists() and legacy_path.exists():
            return legacy_path
        return selected_dir / "app.db"
    return get_default_data_dir() / "data" / "app.db"


def get_shared_images_dir() -> Path:
    data_dir = get_default_data_dir()
    legacy_dir = data_dir / "images"
    if not (data_dir / "Images").exists() and legacy_dir.exists():
        return legacy_dir
    return data_dir / "Images"


def get_db_path() -> Path:
    runtime = get_runtime_data_dir()
    return runtime / "app.db" if runtime else get_shared_db_path()


def get_images_dir() -> Path:
    runtime = get_runtime_data_dir()
    return runtime / "Images" if runtime else get_shared_images_dir()


def get_products_images_dir() -> Path:
    return get_images_dir() / "products"


def get_company_dir() -> Path:
    return get_images_dir() / "company"


def get_backups_dir() -> Path:
    selected_dir = get_configured_backup_dir()
    if selected_dir is not None:
        return selected_dir
    return get_default_data_dir() / "backups"


def get_auto_backups_dir() -> Path:
    return get_backups_dir()


def get_lock_file() -> Path:
    return get_shared_db_path().parent / "app.lock"


def get_session_log() -> Path:
    return get_local_state_dir() / "session.log"
