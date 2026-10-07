import logging
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import error_logging


class ErrorLoggingTests(unittest.TestCase):
    def setUp(self):
        self.log_path = Path(__file__).with_name("_error_logging_test.log")
        self.logger = logging.getLogger("costprofit")
        self._close_handlers()

    def tearDown(self):
        self._close_handlers()
        for path in self.log_path.parent.glob(self.log_path.name + "*"):
            path.unlink()

    def _close_handlers(self):
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

    def test_sensitive_values_are_redacted_from_message_and_traceback(self):
        with patch.object(error_logging, "get_session_log", return_value=self.log_path):
            logger = error_logging.configure_error_logging()
            logger.error("password=secret-value security_answer:tripoli")
            try:
                raise ValueError("password=traceback-secret")
            except ValueError:
                logger.exception("Import failed")
            for handler in logger.handlers:
                handler.flush()

        content = self.log_path.read_text(encoding="utf-8")
        self.assertNotIn("secret-value", content)
        self.assertNotIn("tripoli", content)
        self.assertNotIn("traceback-secret", content)
        self.assertGreaterEqual(content.count("[REDACTED]"), 3)

    def test_log_uses_bounded_rotating_file_handler(self):
        with patch.object(error_logging, "get_session_log", return_value=self.log_path):
            logger = error_logging.configure_error_logging()
        handler = logger.handlers[0]
        self.assertEqual(handler.maxBytes, 1_000_000)
        self.assertEqual(handler.backupCount, 3)


if __name__ == "__main__":
    unittest.main()
