"""
database.py
-----------
Handles all SQLite database operations for the Password Vault.
Responsible for creating tables, and CRUD operations on credentials.
"""

import sqlite3
import os
from typing import Optional


class Database:
    """
    Manages the SQLite database connection and all credential operations.
    Uses OOP design to encapsulate all DB logic.
    """

    DB_FILE = "vault.db"

    def __init__(self):
        """Initialize the database, creating the file and tables if needed."""
        self.connection: Optional[sqlite3.Connection] = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establish connection to the SQLite database file."""
        self.connection = sqlite3.connect(self.DB_FILE)
        self.connection.row_factory = sqlite3.Row  # Access columns by name
        self.connection.execute("PRAGMA journal_mode=WAL")  # Better concurrency

    def _create_tables(self):
        """Create required tables if they do not already exist."""
        cursor = self.connection.cursor()

        # Master password table (stores hashed master password + salt + vault key)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master (
                id      INTEGER PRIMARY KEY CHECK (id = 1),
                salt    BLOB    NOT NULL,
                key     BLOB    NOT NULL
            )
        """)

        # Credentials table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credentials (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                site         TEXT    NOT NULL,
                username     TEXT    NOT NULL,
                password     BLOB    NOT NULL,
                notes        TEXT    DEFAULT '',
                created_at   TEXT    DEFAULT (datetime('now')),
                updated_at   TEXT    DEFAULT (datetime('now'))
            )
        """)

        self.connection.commit()

    # ------------------------------------------------------------------ #
    #  Master password methods                                             #
    # ------------------------------------------------------------------ #

    def master_exists(self) -> bool:
        """Return True if a master password has already been set."""
        row = self.connection.execute(
            "SELECT id FROM master WHERE id = 1"
        ).fetchone()
        return row is not None

    def save_master(self, salt: bytes, encrypted_key: bytes):
        """Persist the salt and the encrypted vault key."""
        self.connection.execute(
            "INSERT OR REPLACE INTO master (id, salt, key) VALUES (1, ?, ?)",
            (salt, encrypted_key),
        )
        self.connection.commit()

    def get_master(self) -> Optional[sqlite3.Row]:
        """Retrieve the master row (salt + key)."""
        return self.connection.execute(
            "SELECT salt, key FROM master WHERE id = 1"
        ).fetchone()

    # ------------------------------------------------------------------ #
    #  Credential CRUD methods                                             #
    # ------------------------------------------------------------------ #

    def add_credential(
        self,
        site: str,
        username: str,
        encrypted_password: bytes,
        notes: str = "",
    ) -> int:
        """
        Insert a new credential record.

        Parameters
        ----------
        site                : Website / application name
        username            : Username or email
        encrypted_password  : Fernet-encrypted password bytes
        notes               : Optional free-text notes

        Returns
        -------
        int : Row ID of the newly inserted record
        """
        cursor = self.connection.execute(
            """
            INSERT INTO credentials (site, username, password, notes)
            VALUES (?, ?, ?, ?)
            """,
            (site.strip(), username.strip(), encrypted_password, notes.strip()),
        )
        self.connection.commit()
        return cursor.lastrowid

    def get_all_credentials(self) -> list:
        """Return all credential rows ordered by site name."""
        return self.connection.execute(
            "SELECT id, site, username, password, notes, created_at, updated_at "
            "FROM credentials ORDER BY site COLLATE NOCASE"
        ).fetchall()

    def get_credential_by_id(self, credential_id: int) -> Optional[sqlite3.Row]:
        """Fetch a single credential by its primary key."""
        return self.connection.execute(
            "SELECT id, site, username, password, notes, created_at, updated_at "
            "FROM credentials WHERE id = ?",
            (credential_id,),
        ).fetchone()

    def search_credentials(self, query: str) -> list:
        """
        Search credentials by site or username (case-insensitive substring match).

        Parameters
        ----------
        query : Search term

        Returns
        -------
        list of matching rows
        """
        like = f"%{query}%"
        return self.connection.execute(
            "SELECT id, site, username, password, notes, created_at, updated_at "
            "FROM credentials "
            "WHERE site LIKE ? OR username LIKE ? "
            "ORDER BY site COLLATE NOCASE",
            (like, like),
        ).fetchall()

    def update_credential(
        self,
        credential_id: int,
        site: str,
        username: str,
        encrypted_password: bytes,
        notes: str = "",
    ):
        """
        Update an existing credential.

        Parameters
        ----------
        credential_id       : Primary key of the record to update
        site                : New site value
        username            : New username value
        encrypted_password  : New Fernet-encrypted password bytes
        notes               : New notes value
        """
        self.connection.execute(
            """
            UPDATE credentials
            SET site = ?, username = ?, password = ?, notes = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (site.strip(), username.strip(), encrypted_password, notes.strip(), credential_id),
        )
        self.connection.commit()

    def delete_credential(self, credential_id: int):
        """Permanently remove a credential by its primary key."""
        self.connection.execute(
            "DELETE FROM credentials WHERE id = ?", (credential_id,)
        )
        self.connection.commit()

    # ------------------------------------------------------------------ #
    #  Housekeeping                                                        #
    # ------------------------------------------------------------------ #

    def close(self):
        """Close the database connection gracefully."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def __del__(self):
        self.close()
