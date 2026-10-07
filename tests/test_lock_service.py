import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from app.paths import get_machine_id_file
from app.services.lock_service import LockService


class LockServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="lock_service_")
        self.lock_path = Path(self.temp_dir.name) / "app.lock"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_second_instance_on_same_machine_cannot_take_active_lock(self):
        first = LockService()
        second = LockService()
        first._lock_path = self.lock_path
        second._lock_path = self.lock_path

        with patch("app.services.lock_service.get_machine_id", return_value="machine-a"):
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()

    def test_simultaneous_free_lock_acquisition_has_one_winner(self):
        services = [LockService(), LockService()]
        for service in services:
            service._lock_path = self.lock_path
        barrier = Barrier(2)

        def check_free():
            barrier.wait()
            return "free", None

        with patch("app.services.lock_service.get_machine_id", return_value="machine-a"), patch.object(
            LockService, "check", side_effect=check_free,
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda service: service.acquire(), services))

        self.assertEqual(sorted(results), [False, True])
        services[results.index(True)].release()

    def test_previous_owner_does_not_remove_replacement_lock(self):
        machine = {"id": "machine-a"}
        first = LockService()
        first._lock_path = self.lock_path
        replacement = LockService()
        replacement._lock_path = self.lock_path

        with patch(
            "app.services.lock_service.get_machine_id",
            side_effect=lambda: machine["id"],
        ):
            self.assertTrue(first.acquire())
            machine["id"] = "machine-b"
            self.assertTrue(replacement.acquire(force=True))

            first.release()
            self.assertTrue(self.lock_path.exists())
            replacement.heartbeat()
            replacement.release()
            self.assertFalse(self.lock_path.exists())

    def test_machine_id_uses_local_app_data_on_windows(self):
        with tempfile.TemporaryDirectory(prefix="machine_id_") as local_data:
            with patch.dict(os.environ, {"LOCALAPPDATA": local_data}), patch(
                "app.paths.platform.system", return_value="Windows",
            ):
                self.assertEqual(
                    get_machine_id_file(),
                    Path(local_data) / "CostProfitApp" / "machine.id",
                )


if __name__ == "__main__":
    unittest.main()