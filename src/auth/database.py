"""Lightweight SQLite user store for the login / signup feature.

Kept dependency-free (uses Python's built-in sqlite3) so the rest of the
project's requirements don't need to change just to support authentication.

Roles
-----
Every account belongs to one of three roles (see src/config.py:ROLES):

* ``user``       — public/citizen view: personal alert, risk map, alerts
* ``department`` — full operational dashboard (all information pages)
* ``admin``      — everything the department sees, plus the database/admin
                   panel where roles can be managed.

The role is a column on the existing ``users`` table (no parallel auth
system). Existing databases are migrated on startup by adding the column
with a default of ``user``.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.auth.security import hash_password, verify_password
from src.config import AUTH_DB_FILE, DEFAULT_ROLE, ROLES


def _get_connection() -> sqlite3.Connection:
    AUTH_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUTH_DB_FILE)
    connection.row_factory = sqlite3.Row
    return connection


def init_user_db() -> None:
    """Create the users table (with its role column) if it doesn't already
    exist, and migrate legacy databases that predate roles."""
    with _get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL
            )
            """
        )
        columns = [row[1] for row in connection.execute("PRAGMA table_info(users)")]
        if "role" not in columns:
            connection.execute(
                "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"
            )

    seed_demo_accounts()


def _validate_role(role: str) -> str:
    return role if role in ROLES else DEFAULT_ROLE


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with _get_connection() as connection:
        cursor = connection.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        )
        return cursor.fetchone()


def get_user_role(email: str) -> str:
    """Return the role for an email address (defaults to 'user')."""
    user = get_user_by_email(email)
    return user["role"] if user is not None else DEFAULT_ROLE


def create_user(
    full_name: str, email: str, password: str, role: str = DEFAULT_ROLE
) -> tuple[bool, str]:
    """Create a new user. Returns (success, message)."""
    email = email.strip().lower()

    if get_user_by_email(email) is not None:
        return False, "An account with this email already exists."

    password_hash = hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()

    with _get_connection() as connection:
        connection.execute(
            "INSERT INTO users (full_name, email, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (full_name.strip(), email, password_hash, _validate_role(role), created_at),
        )

    return True, "Account created successfully."


def authenticate_user(email: str, password: str) -> tuple[bool, str]:
    """Verify credentials. Returns (success, message)."""
    user = get_user_by_email(email)

    if user is None:
        return False, "No account found with this email."

    if not verify_password(password, user["password_hash"]):
        return False, "Incorrect password."

    return True, "Login successful."


def list_users() -> list[dict]:
    """All users (id, full_name, email, role, created_at) for the admin panel."""
    with _get_connection() as connection:
        rows = connection.execute(
            "SELECT id, full_name, email, role, created_at "
            "FROM users ORDER BY created_at"
        ).fetchall()
    return [dict(row) for row in rows]


def update_user_role(user_id: int, role: str) -> tuple[bool, str]:
    """Change a user's role. Returns (success, message).

    Refuses to demote the last remaining admin so the system can never be
    locked out of admin access.
    """
    role = _validate_role(role)

    with _get_connection() as connection:
        target = connection.execute(
            "SELECT id, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if target is None:
            return False, "No user found with that id."

        if target["role"] == "admin" and role != "admin":
            admin_count = connection.execute(
                "SELECT COUNT(*) AS n FROM users WHERE role = 'admin'"
            ).fetchone()["n"]
            if admin_count <= 1:
                return False, (
                    "Cannot change the last admin's role — the system would "
                    "have no administrators left."
                )

        connection.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))

    return True, "Role updated."


DEMO_ACCOUNTS = [
    ("Demo Admin", "admin@pahadguard.com", "admin123", "admin"),
    ("Demo Department Officer", "department@pahadguard.com", "dept123", "department"),
    ("Demo Citizen", "user@pahadguard.com", "user123", "user"),
]


def seed_demo_accounts() -> None:
    """Seed one demo account per role when no admin account exists yet.

    This keeps the three-role demo ready to log in for evaluations while
    never touching an existing user base — if a real admin already exists,
    nothing is created.
    """
    with _get_connection() as connection:
        admin_count = connection.execute(
            "SELECT COUNT(*) AS n FROM users WHERE role = 'admin'"
        ).fetchone()["n"]

    if admin_count > 0:
        return

    for full_name, email, password, role in DEMO_ACCOUNTS:
        create_user(full_name, email, password, role=role)


# Ensure the schema (and migration) exists as soon as the module is imported;
# this also keeps tests that call create_user() directly working without an
# explicit init_user_db() call.
init_user_db()
