"""
vault.py
--------
High-level Vault facade that ties together the Database and CryptoManager.
The GUI (and any future CLI) interacts only with this class.
"""

import datetime
from typing import Optional

from database import Database
from crypto import CryptoManager
from password_generator import PasswordGenerator


class Vault:
    """
    Central controller for the Password Vault application.

    Responsibilities
    ----------------
    * First-run setup (master password creation)
    * Unlock / lock lifecycle
    * CRUD operations on credentials (encrypt/decrypt transparently)
    * Export to encrypted text file
    * Password generation
    """

    def __init__(self):
        self._db = Database()
        self._crypto = CryptoManager()
        self._generator = PasswordGenerator()

    # ------------------------------------------------------------------ #
    #  Setup & authentication                                              #
    # ------------------------------------------------------------------ #

    def is_first_run(self) -> bool:
        """Return True if no master password has been configured yet."""
        return not self._db.master_exists()

    def setup_master_password(self, master_password: str) -> bool:
        """
        Create and persist the master password on first run.

        Parameters
        ----------
        master_password : The user's chosen master password

        Returns
        -------
        bool : True on success
        """
        if not master_password:
            raise ValueError("Master password cannot be empty.")

        salt, encrypted_key = self._crypto.setup_master(master_password)
        self._db.save_master(salt, encrypted_key)
        return True

    def unlock(self, master_password: str) -> bool:
        """
        Unlock the vault with the master password.

        Parameters
        ----------
        master_password : Plain-text master password

        Returns
        -------
        bool : True if password is correct, False otherwise
        """
        row = self._db.get_master()
        if row is None:
            return False
        return self._crypto.unlock(master_password, bytes(row["salt"]), bytes(row["key"]))

    def lock(self):
        """Lock the vault, wiping the in-memory key."""
        self._crypto.lock()

    @property
    def is_unlocked(self) -> bool:
        return self._crypto.is_unlocked

    # ------------------------------------------------------------------ #
    #  Credential operations                                               #
    # ------------------------------------------------------------------ #

    def _require_unlocked(self):
        if not self.is_unlocked:
            raise PermissionError("Vault is locked.")

    def add_credential(
        self, site: str, username: str, plain_password: str, notes: str = ""
    ) -> int:
        """
        Encrypt and store a new credential.

        Parameters
        ----------
        site           : Website / app name
        username       : Username or e-mail
        plain_password : Plain-text password (will be encrypted before storage)
        notes          : Optional notes

        Returns
        -------
        int : New record ID
        """
        self._require_unlocked()
        self._validate_credential(site, username, plain_password)
        encrypted = self._crypto.encrypt_password(plain_password)
        return self._db.add_credential(site, username, encrypted, notes)

    def get_all_credentials(self) -> list[dict]:
        """
        Return all credentials with passwords **decrypted**.

        Returns
        -------
        list of dicts with keys: id, site, username, password, notes,
                                 created_at, updated_at
        """
        self._require_unlocked()
        rows = self._db.get_all_credentials()
        return [self._row_to_dict(r) for r in rows]

    def search_credentials(self, query: str) -> list[dict]:
        """
        Search credentials by site or username.

        Parameters
        ----------
        query : Search term (substring match)

        Returns
        -------
        list of matching credential dicts (passwords decrypted)
        """
        self._require_unlocked()
        rows = self._db.search_credentials(query)
        return [self._row_to_dict(r) for r in rows]

    def update_credential(
        self,
        credential_id: int,
        site: str,
        username: str,
        plain_password: str,
        notes: str = "",
    ):
        """
        Update an existing credential (re-encrypts the password).

        Parameters
        ----------
        credential_id  : ID of the record to update
        site           : Updated site name
        username       : Updated username
        plain_password : Updated plain-text password
        notes          : Updated notes
        """
        self._require_unlocked()
        self._validate_credential(site, username, plain_password)
        encrypted = self._crypto.encrypt_password(plain_password)
        self._db.update_credential(credential_id, site, username, encrypted, notes)

    def delete_credential(self, credential_id: int):
        """
        Permanently delete a credential.

        Parameters
        ----------
        credential_id : ID of the record to delete
        """
        self._require_unlocked()
        self._db.delete_credential(credential_id)

    # ------------------------------------------------------------------ #
    #  Password generator                                                  #
    # ------------------------------------------------------------------ #

    def generate_password(
        self,
        length: int = 16,
        use_uppercase: bool = True,
        use_digits: bool = True,
        use_symbols: bool = True,
    ) -> str:
        """Delegate to PasswordGenerator and return a strong random password."""
        return self._generator.generate(
            length=length,
            use_uppercase=use_uppercase,
            use_digits=use_digits,
            use_symbols=use_symbols,
        )

    @staticmethod
    def password_strength(password: str) -> str:
        """Return a human-readable strength label for *password*."""
        return PasswordGenerator.strength(password)

    # ------------------------------------------------------------------ #
    #  Export                                                              #
    # ------------------------------------------------------------------ #

    def export_to_file(self, filepath: str) -> int:
        """
        Export all credentials to a plain-text file (passwords in clear-text).
        Intended for personal backup; remind the user to store the file safely.

        Parameters
        ----------
        filepath : Absolute or relative path for the output .txt file

        Returns
        -------
        int : Number of entries exported
        """
        self._require_unlocked()
        credentials = self.get_all_credentials()

        header = (
            "=" * 60 + "\n"
            "  PASSWORD VAULT EXPORT\n"
            f"  Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  Total entries: {len(credentials)}\n"
            "  WARNING: This file contains plain-text passwords.\n"
            "           Store it securely and delete after use.\n"
            "=" * 60 + "\n\n"
        )

        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(header)
            for idx, cred in enumerate(credentials, 1):
                fh.write(f"[{idx}] {cred['site']}\n")
                fh.write(f"    Username : {cred['username']}\n")
                fh.write(f"    Password : {cred['password']}\n")
                if cred["notes"]:
                    fh.write(f"    Notes    : {cred['notes']}\n")
                fh.write(
                    f"    Added    : {cred['created_at']}  "
                    f"Updated: {cred['updated_at']}\n"
                )
                fh.write("-" * 60 + "\n")

        return len(credentials)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _row_to_dict(self, row) -> dict:
        """Convert a DB row to a plain dict, decrypting the password field."""
        return {
            "id": row["id"],
            "site": row["site"],
            "username": row["username"],
            "password": self._crypto.decrypt_password(bytes(row["password"])),
            "notes": row["notes"] or "",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _validate_credential(site: str, username: str, password: str):
        """Raise ValueError for blank required fields."""
        errors = []
        if not site.strip():
            errors.append("Site name is required.")
        if not username.strip():
            errors.append("Username is required.")
        if not password:
            errors.append("Password is required.")
        if errors:
            raise ValueError("\n".join(errors))

    def close(self):
        """Release all resources."""
        self.lock()
        self._db.close()
