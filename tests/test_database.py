import tempfile
import unittest
from pathlib import Path

from src.database import DatabaseManager, DuplicateUserError


class DatabaseManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_access.db"
        self.database = DatabaseManager(self.db_path)
        self.database.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_user_and_read_it_back(self) -> None:
        user_id = self.database.create_user(
            staff_id="PF001",
            full_name="Ada Farmer",
            role="Farm Supervisor",
            password_hash="hash",
            password_salt="salt",
        )
        user = self.database.get_user_by_id(user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user["staff_id"], "PF001")
        self.assertEqual(user["full_name"], "Ada Farmer")

    def test_access_logs_include_joined_user_data(self) -> None:
        user_id = self.database.create_user(
            staff_id="PF002",
            full_name="Tomi Guard",
            role="Security Officer",
            password_hash="hash",
            password_salt="salt",
        )
        self.database.log_access(
            user_id=user_id,
            access_point="Password Entry Gate",
            method="PASSWORD",
            status="GRANTED",
            confidence=None,
            spoof_detected=False,
            message="Granted",
        )
        logs = self.database.get_recent_logs(limit=1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["full_name"], "Tomi Guard")
        self.assertEqual(logs[0]["status"], "GRANTED")

    def test_duplicate_staff_id_is_rejected(self) -> None:
        self.database.create_user(
            staff_id="PF003",
            full_name="Grace Keeper",
            role="Supervisor",
            password_hash="hash",
            password_salt="salt",
        )
        with self.assertRaises(DuplicateUserError):
            self.database.create_user(
                staff_id="pf003",
                full_name="Another Person",
                role="Supervisor",
                password_hash="hash",
                password_salt="salt",
            )

    def test_duplicate_full_name_is_rejected(self) -> None:
        self.database.create_user(
            staff_id="PF004",
            full_name="Ifeoma Ade",
            role="Veterinarian",
            password_hash="hash",
            password_salt="salt",
        )
        with self.assertRaises(DuplicateUserError):
            self.database.create_user(
                staff_id="PF005",
                full_name="ifeoma ade",
                role="Farm Staff",
                password_hash="hash",
                password_salt="salt",
            )


if __name__ == "__main__":
    unittest.main()
