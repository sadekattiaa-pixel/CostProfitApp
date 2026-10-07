import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.paths import get_backups_dir, get_db_path, get_images_dir
from app.services.license_service import LicenseError, verify_device_license
from app.storage_config import load_storage_config, update_storage_config, get_storage_config_path


class PortableStorageLicenseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="device_storage_")
        self.root = Path(self.temp.name)
        self.local = self.root / "Local"
        self.portable = self.root / "Portable"
        self.portable.mkdir()
        (self.portable / "portable-config.json").write_text(json.dumps({
            "portable": True, "data_dir": "Data", "backup_dir": "Backups/Auto",
        }), encoding="utf-8")
        self.env = patch.dict(os.environ, {
            "LOCALAPPDATA": str(self.local), "COSTPROFIT_PORTABLE_ROOT": str(self.portable),
            "COSTPROFIT_DATA_DIR": "",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_portable_data_and_local_backup_paths(self):
        self.assertEqual(get_db_path(), self.portable / "Data" / "app.db")
        self.assertEqual(get_images_dir(), self.portable / "Data" / "Images")
        self.assertEqual(get_backups_dir(), self.local / "CostProfitApp" / "Backups")
        chosen = self.root / "LocalBackups"
        update_storage_config(backup_dir=str(chosen))
        self.assertEqual(get_backups_dir(), chosen)
        self.assertEqual(get_db_path(), self.portable / "Data" / "app.db")
        self.assertEqual(get_storage_config_path(), self.local / "CostProfitApp" / "storage-config.json")

    def test_backups_cannot_be_saved_in_shared_data(self):
        update_storage_config(data_dir=str(self.root / "Shared"))
        with self.assertRaises(ValueError):
            update_storage_config(backup_dir=str(self.root / "Shared" / "Backups"))

    def test_backups_cannot_be_saved_inside_onedrive(self):
        with patch.dict(os.environ, {"OneDrive": str(self.root / "Cloud")}):
            with self.assertRaises(ValueError):
                update_storage_config(backup_dir=str(self.root / "Cloud" / "Backups"))

    def test_first_launch_binds_and_moving_on_same_device_preserves_binding(self):
        path = self.root / "device.dat"
        # Unit tests separate device-identity policy from Windows DPAPI itself.
        with patch("app.services.license_service.get_device_fingerprint", return_value="PC-A"), patch(
            "app.services.license_service._device_crypt", side_effect=lambda data, **kwargs: data,
        ):
            record = verify_device_license(path)
            moved = self.root / "AnotherDrive" / "device.dat"
            moved.parent.mkdir()
            path.rename(moved)
            self.assertEqual(verify_device_license(moved)["copy_id"], record["copy_id"])

    def test_copy_to_other_device_is_rejected_without_rebinding(self):
        path = self.root / "device.dat"
        with patch("app.services.license_service._device_crypt", side_effect=lambda data, **kwargs: data):
            with patch("app.services.license_service.get_device_fingerprint", return_value="PC-A"):
                verify_device_license(path)
            original = path.read_bytes()
            with patch("app.services.license_service.get_device_fingerprint", return_value="PC-B"):
                with self.assertRaises(LicenseError):
                    verify_device_license(path)
            self.assertEqual(path.read_bytes(), original)

    def test_damaged_binding_is_rejected_without_rebinding(self):
        path = self.root / "device.dat"
        path.write_bytes(b"damaged")
        with patch("app.services.license_service._device_crypt", side_effect=lambda data, **kwargs: data):
            with self.assertRaises(LicenseError):
                verify_device_license(path)
        self.assertEqual(path.read_bytes(), b"damaged")


if __name__ == "__main__":
    unittest.main()
