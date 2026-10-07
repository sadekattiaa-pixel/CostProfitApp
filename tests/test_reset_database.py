import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.db.database import Database


class ResetDatabaseTests(unittest.TestCase):
    def test_reset_removes_db_and_wal_sidecars(self):
        db = Database()
        temp_dir = Path(tempfile.mkdtemp(prefix="reset_db_"))
        db_path = temp_dir / "test_app.db"

        db.connect(db_path)
        db.execute("CREATE TABLE IF NOT EXISTS reset_table (id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO reset_table (value) VALUES (?)", ("data",))
        db._conn.commit()

        wal_path = db_path.with_name(db_path.name + "-wal")
        shm_path = db_path.with_name(db_path.name + "-shm")

        if wal_path.exists() or shm_path.exists():
            pass

        db.reset(db_path)

        self.assertFalse(db_path.exists())
        self.assertFalse(wal_path.exists())
        self.assertFalse(shm_path.exists())
        self.assertIsNone(db._conn)

        db.connect(db_path)
        db.close()

    def test_reset_surfaces_delete_errors_and_reopens_database(self):
        db = Database()
        temp_dir = tempfile.TemporaryDirectory(prefix="reset_db_error_")
        db_path = Path(temp_dir.name) / "test_app.db"

        db.connect(db_path)
        db.execute("CREATE TABLE reset_table (id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO reset_table (value) VALUES (?)", ("data",))
        db._conn.commit()

        with patch.object(Path, "unlink", side_effect=PermissionError("file is locked")):
            with self.assertRaises(PermissionError):
                db.reset(db_path)

        self.assertIsNotNone(db._conn)
        self.assertEqual(db.query_one("SELECT value FROM reset_table")["value"], "data")
        db.close()
        temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
