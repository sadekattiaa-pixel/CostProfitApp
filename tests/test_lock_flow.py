import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.db import db
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow


class LockFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_lock_opens_login_window(self):
        temp_dir = tempfile.TemporaryDirectory(prefix="lock_flow_")
        db.connect(Path(temp_dir.name) / "test.db")
        window = MainWindow()
        window.show()

        window._on_lock()

        login_windows = [w for w in QApplication.topLevelWidgets() if isinstance(w, LoginWindow)]
        self.assertTrue(login_windows)
        self.assertFalse(window.isVisible())

        for w in list(QApplication.topLevelWidgets()):
            if isinstance(w, LoginWindow):
                w.close()
        window.close()
        db.close()
        temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
