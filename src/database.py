from contextlib import contextmanager
import sqlite3
from pathlib import Path
from typing import Any


class DuplicateUserError(ValueError):
    """Raised when registration attempts to create a duplicate user."""


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _session(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    face_samples INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    access_point TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL,
                    spoof_detected INTEGER NOT NULL DEFAULT 0,
                    message TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_staff_id ON users(staff_id)"
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_access_logs_created_at
                ON access_logs(created_at DESC)
                """
            )

    def create_user(
        self,
        staff_id: str,
        full_name: str,
        role: str,
        password_hash: str,
        password_salt: str,
    ) -> int:
        duplicate = self.find_duplicate_user(staff_id, full_name)
        if duplicate:
            duplicate_staff = duplicate["staff_id"].strip().casefold() == staff_id.strip().casefold()
            duplicate_name = duplicate["full_name"].strip().casefold() == full_name.strip().casefold()

            if duplicate_staff and duplicate_name:
                raise DuplicateUserError(
                    "A user with the same staff ID and full name already exists."
                )
            if duplicate_staff:
                raise DuplicateUserError("That staff ID is already registered.")
            if duplicate_name:
                raise DuplicateUserError("That full name is already registered.")

        with self._session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (staff_id, full_name, role, password_hash, password_salt)
                VALUES (?, ?, ?, ?, ?)
                """,
                (staff_id, full_name, role, password_hash, password_salt),
            )
            return int(cursor.lastrowid)

    def get_user_by_staff_id(self, staff_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE staff_id = ?",
                (staff_id,),
            ).fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def find_duplicate_user(self, staff_id: str, full_name: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM users
                WHERE LOWER(TRIM(staff_id)) = LOWER(TRIM(?))
                   OR LOWER(TRIM(full_name)) = LOWER(TRIM(?))
                LIMIT 1
                """,
                (staff_id, full_name),
            ).fetchone()
        return dict(row) if row else None

    def list_users(self) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM users ORDER BY full_name COLLATE NOCASE ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def count_users(self) -> int:
        with self._session() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM users").fetchone()
        return int(row["total"])

    def count_enrolled_users(self) -> int:
        with self._session() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM users WHERE face_samples > 0"
            ).fetchone()
        return int(row["total"])

    def count_logs(self) -> int:
        with self._session() as connection:
            row = connection.execute("SELECT COUNT(*) AS total FROM access_logs").fetchone()
        return int(row["total"])

    def update_face_samples(self, user_id: int, sample_count: int) -> None:
        with self._session() as connection:
            connection.execute(
                """
                UPDATE users
                SET face_samples = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (sample_count, user_id),
            )

    def log_access(
        self,
        user_id: int | None,
        access_point: str,
        method: str,
        status: str,
        confidence: float | None,
        spoof_detected: bool,
        message: str,
    ) -> None:
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO access_logs (
                    user_id, access_point, method, status, confidence, spoof_detected, message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    access_point,
                    method,
                    status,
                    confidence,
                    int(spoof_detected),
                    message,
                ),
            )

    def get_recent_logs(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT
                    access_logs.id,
                    access_logs.created_at,
                    access_logs.access_point,
                    access_logs.method,
                    access_logs.status,
                    access_logs.confidence,
                    access_logs.spoof_detected,
                    access_logs.message,
                    users.staff_id,
                    users.full_name
                FROM access_logs
                LEFT JOIN users ON users.id = access_logs.user_id
                ORDER BY access_logs.created_at DESC, access_logs.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
