import time
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from app.config import MAX_LOGIN_ATTEMPTS, LOGIN_LOCKOUT_SECONDS
from app.services.auth_service import auth
from app.services.settings_service import settings
from app.db import db
from app.ui.login_window import LoginWindow


class LoginLockoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="login_lockout_")
        db.connect(Path(self.temp_dir.name) / "test.db")
        settings.clear_cache()
        auth.set_password("StrongPass123")
        self.window = LoginWindow()

    def tearDown(self):
        self.window.close()
        db.close()
        settings.clear_cache()
        self.temp_dir.cleanup()

    def test_failed_attempts_lock_the_login_for_lockout_period(self):
        for _ in range(MAX_LOGIN_ATTEMPTS):
            self.window.password_input.setText("wrong")
            self.window._on_unlock()

        self.assertFalse(self.window.unlock_btn.isEnabled())
        self.assertFalse(self.window.password_input.isEnabled())
        self.assertGreaterEqual(self.window._lock_until, time.time())
        self.assertLessEqual(self.window._lock_until - time.time(), LOGIN_LOCKOUT_SECONDS)

    def test_security_answer_survives_password_changes_and_resets(self):
        auth.set_security_question("Recovery question?", "recovery answer", "recovery answer")

        auth.change_password("StrongPass123", "NewStrongPass123", "NewStrongPass123")
        self.assertTrue(auth.verify_security_answer("recovery answer"))

        auth.reset_password_via_security(
            "recovery answer", "ResetStrongPass123", "ResetStrongPass123",
        )
        self.assertTrue(auth.verify_security_answer("recovery answer"))
        self.assertTrue(auth.verify_password("ResetStrongPass123"))

    def test_legacy_security_answer_salt_is_migrated_before_password_change(self):
        from app.services.auth_service import _hash

        legacy_salt = settings.get("password_salt")
        settings.set("security_question", "Legacy question?")
        settings.set("security_answer_hash", _hash("legacy answer", legacy_salt))
        settings.set("security_answer_salt", "")

        auth.set_password("UpdatedStrongPass123")

        self.assertTrue(auth.verify_security_answer("legacy answer"))


if __name__ == "__main__":
    unittest.main()
