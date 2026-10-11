import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.paths import get_backups_dir, get_db_path, get_images_dir
from app.storage_config import update_storage_config, get_storage_config_path


class PortableStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="portable_storage_")
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

if __name__ == "__main__":
    unittest.main()
