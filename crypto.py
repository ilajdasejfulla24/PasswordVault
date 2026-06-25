"""
crypto.py
---------
Cryptography layer for the Password Vault.

Design
------
* The user's master password is used to derive a 32-byte key via PBKDF2-HMAC-SHA256.
* That derived key encrypts/decrypts a randomly-generated *vault key* (Fernet key).
* The vault key is what actually encrypts each stored password.
* This two-layer scheme lets us re-key the vault key on master-password change
  without re-encrypting every stored password.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class CryptoManager:
    """
    Handles key derivation, vault-key management, and per-password
    encryption / decryption using the Fernet symmetric scheme.
    """

    # PBKDF2 iteration count – high enough to slow brute-force attacks
    _ITERATIONS = 480_000

    def __init__(self):
        """Internal vault key (bytes) – set after successful unlock."""
        self._vault_key: bytes | None = None

    # ------------------------------------------------------------------ #
    #  Key derivation                                                      #
    # ------------------------------------------------------------------ #

    def _derive_key(self, master_password: str, salt: bytes) -> bytes:
        """
        Derive a 32-byte key from *master_password* using PBKDF2-HMAC-SHA256.

        Parameters
        ----------
        master_password : Plain-text master password
        salt            : Random 16-byte salt

        Returns
        -------
        bytes : URL-safe base64-encoded 32-byte key suitable for Fernet
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self._ITERATIONS,
            backend=default_backend(),
        )
        return base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))

    # ------------------------------------------------------------------ #
    #  Master-password / vault-key setup                                  #
    # ------------------------------------------------------------------ #

    def setup_master(self, master_password: str) -> tuple[bytes, bytes]:
        """
        Create a brand-new vault key and encrypt it with the master password.

        Call this once when the user sets their master password for the first time.

        Parameters
        ----------
        master_password : Chosen master password (plain text)

        Returns
        -------
        (salt, encrypted_vault_key) – both should be persisted in the DB
        """
        salt = os.urandom(16)
        derived_key = self._derive_key(master_password, salt)
        vault_key = Fernet.generate_key()          # Random vault key
        f = Fernet(derived_key)
        encrypted_vault_key = f.encrypt(vault_key) # Wrap vault key

        self._vault_key = vault_key                # Cache for immediate use
        return salt, encrypted_vault_key

    def unlock(self, master_password: str, salt: bytes, encrypted_vault_key: bytes) -> bool:
        """
        Attempt to unlock the vault with the supplied master password.

        Parameters
        ----------
        master_password      : Plain-text password entered by the user
        salt                 : Salt retrieved from the DB
        encrypted_vault_key  : Encrypted vault key retrieved from the DB

        Returns
        -------
        bool : True if the password is correct and the vault is now unlocked
        """
        try:
            derived_key = self._derive_key(master_password, salt)
            f = Fernet(derived_key)
            self._vault_key = f.decrypt(encrypted_vault_key)
            return True
        except Exception:
            return False

    def lock(self):
        """Clear the in-memory vault key, locking the vault."""
        self._vault_key = None

    @property
    def is_unlocked(self) -> bool:
        """Return True when the vault key is loaded in memory."""
        return self._vault_key is not None

    # ------------------------------------------------------------------ #
    #  Password encryption / decryption                                   #
    # ------------------------------------------------------------------ #

    def _get_fernet(self) -> Fernet:
        """Return a Fernet instance using the cached vault key."""
        if not self.is_unlocked:
            raise RuntimeError("Vault is locked. Unlock it before encrypting/decrypting.")
        return Fernet(self._vault_key)

    def encrypt_password(self, plain_password: str) -> bytes:
        """
        Encrypt a plain-text password.

        Parameters
        ----------
        plain_password : The password to protect

        Returns
        -------
        bytes : Fernet token (ciphertext)
        """
        return self._get_fernet().encrypt(plain_password.encode("utf-8"))

    def decrypt_password(self, encrypted_password: bytes) -> str:
        """
        Decrypt a previously encrypted password.

        Parameters
        ----------
        encrypted_password : Fernet token stored in the database

        Returns
        -------
        str : Original plain-text password
        """
        return self._get_fernet().decrypt(encrypted_password).decode("utf-8")
