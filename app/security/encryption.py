"""Encryption at rest module.

Provides encryption/decryption for sensitive data using Fernet symmetric encryption.
"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Any

import structlog

logger = structlog.get_logger()


class EncryptionManager:
    """Manages encryption/decryption of sensitive data."""

    def __init__(self, key: str | None = None) -> None:
        """Initialize encryption manager.

        Args:
            key: Fernet encryption key. If not provided, generates a new one.
        """
        self._key = key or os.environ.get("ENCRYPTION_KEY")
        self._fernet: Any = None

        if self._key:
            self._setup_fernet(self._key)
        else:
            logger.warning("no_encryption_key_provided")

    def _setup_fernet(self, key: str) -> None:
        """Setup Fernet encryption."""
        try:
            from cryptography.fernet import Fernet

            # If key is not a valid Fernet key, derive one
            try:
                self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
            except Exception:
                # Derive key from password
                key_bytes = key.encode() if isinstance(key, str) else key
                derived_key = hashlib.sha256(key_bytes).digest()
                fernet_key = base64.urlsafe_b64encode(derived_key)
                self._fernet = Fernet(fernet_key)

            logger.info("encryption_manager_initialized")
        except ImportError:
            logger.error("cryptography_not_installed")

    def encrypt(self, data: str) -> str:
        """Encrypt a string.

        Args:
            data: Plain text to encrypt.

        Returns:
            Encrypted string (base64 encoded).
        """
        if not self._fernet:
            logger.warning("encryption_not_available")
            return data

        try:
            encrypted = self._fernet.encrypt(data.encode())
            return str(encrypted.decode())
        except Exception as e:
            logger.error("encryption_failed", error=str(e))
            return data

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt a string.

        Args:
            encrypted_data: Encrypted string (base64 encoded).

        Returns:
            Decrypted plain text.
        """
        if not self._fernet:
            logger.warning("decryption_not_available")
            return encrypted_data

        try:
            decrypted = self._fernet.decrypt(encrypted_data.encode())
            return str(decrypted.decode())
        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            return encrypted_data

    def encrypt_dict(self, data: dict[str, Any], fields: list[str] | None = None) -> dict[str, Any]:
        """Encrypt specific fields in a dictionary.

        Args:
            data: Dictionary to encrypt.
            fields: List of field names to encrypt. If None, encrypts all string values.

        Returns:
            Dictionary with encrypted fields.
        """
        result = data.copy()
        fields_to_encrypt = fields or [k for k, v in data.items() if isinstance(v, str)]

        for field in fields_to_encrypt:
            if field in result and isinstance(result[field], str):
                result[field] = self.encrypt(result[field])

        return result

    def decrypt_dict(self, data: dict[str, Any], fields: list[str] | None = None) -> dict[str, Any]:
        """Decrypt specific fields in a dictionary.

        Args:
            data: Dictionary with encrypted fields.
            fields: List of field names to decrypt. If None, decrypts all string values.

        Returns:
            Dictionary with decrypted fields.
        """
        result = data.copy()
        fields_to_decrypt = fields or [k for k, v in data.items() if isinstance(v, str)]

        for field in fields_to_decrypt:
            if field in result and isinstance(result[field], str):
                result[field] = self.decrypt(result[field])

        return result

    def generate_key(self) -> str:
        """Generate a new Fernet encryption key.

        Returns:
            New encryption key (base64 encoded).
        """
        try:
            from cryptography.fernet import Fernet

            key_bytes: bytes = Fernet.generate_key()
            return key_bytes.decode()
        except ImportError:
            logger.error("cryptography_not_installed")
            return ""


# Global encryption manager
encryption_manager = EncryptionManager()


def setup_encryption() -> None:
    """Setup encryption from environment."""
    global encryption_manager
    encryption_manager = EncryptionManager()
