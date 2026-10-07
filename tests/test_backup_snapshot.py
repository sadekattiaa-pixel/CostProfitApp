import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.db.database import Database


class BackupSnapshotTests(unittest.TestCase):
    def test_backup_captures_live_database_state(self):
        db = Database()
        temp_dir = Path(tempfile.mkdtemp(prefix="backup_test_"))
        db_path = temp_dir / "test_app.db"

        db.connect(db_path)
        db.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO test_table (value) VALUES (?)", ("alive",))
        db._conn.commit()

        backup_path = temp_dir / "snapshot.db"
        db.backup_to(backup_path)

        journal_mode = db._conn.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(journal_mode.lower(), "wal")

        self.assertTrue(backup_path.exists())

        with sqlite3.connect(str(backup_path)) as conn:
            row = conn.execute("SELECT value FROM test_table WHERE id = 1").fetchone()
            self.assertEqual(row[0], "alive")

        db.close()


if __name__ == "__main__":
    unittest.main()
