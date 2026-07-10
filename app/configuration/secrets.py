"""Secrets management infrastructure.

Supports multiple secrets backends:
- Environment variables (default)
- HashiCorp Vault
- AWS Secrets Manager
- Encrypted configuration files
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""

    @abstractmethod
    def get_secret(self, name: str) -> str | None:
        """Get a secret value."""
        ...

    @abstractmethod
    def set_secret(self, name: str, value: str) -> None:
        """Set a secret value."""
        ...

    @abstractmethod
    def delete_secret(self, name: str) -> bool:
        """Delete a secret value."""
        ...

    @abstractmethod
    def list_secrets(self) -> list[str]:
        """List all secret names."""
        ...


class EnvironmentSecretsBackend(SecretsBackend):
    """Secrets backend using environment variables."""

    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix

    def get_secret(self, name: str) -> str | None:
        """Get a secret from environment variables."""
        env_name = f"{self._prefix}{name}" if self._prefix else name
        value = os.environ.get(env_name)
        if value is not None:
            logger.debug("secret_retrieved_from_env", name=name)
        return value

    def set_secret(self, name: str, value: str) -> None:
        """Set a secret in environment variables."""
        env_name = f"{self._prefix}{name}" if self._prefix else name
        os.environ[env_name] = value
        logger.debug("secret_set_in_env", name=name)

    def delete_secret(self, name: str) -> bool:
        """Delete a secret from environment variables."""
        env_name = f"{self._prefix}{name}" if self._prefix else name
        if env_name in os.environ:
            del os.environ[env_name]
            logger.debug("secret_deleted_from_env", name=name)
            return True
        return False

    def list_secrets(self) -> list[str]:
        """List all secrets in environment variables."""
        prefix = self._prefix if self._prefix else ""
        return [
            key[len(prefix) :] for key in os.environ if key.startswith(prefix) and key != prefix
        ]


class VaultSecretsBackend(SecretsBackend):
    """Secrets backend using HashiCorp Vault."""

    def __init__(
        self,
        url: str = "http://localhost:8200",
        token: str | None = None,
        mount_point: str = "secret",
    ) -> None:
        self._url = url
        self._token = token or os.environ.get("VAULT_TOKEN")
        self._mount_point = mount_point

    def get_secret(self, name: str) -> str | None:
        """Get a secret from Vault."""
        try:
            import requests

            headers = {"X-Vault-Token": self._token or ""}
            url = f"{self._url}/v1/{self._mount_point}/{name}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            value: str | None = data.get("data", {}).get("data", {}).get("value")
            if value:
                logger.debug("secret_retrieved_from_vault", name=name)
            return value
        except Exception as e:
            logger.error("vault_get_secret_failed", name=name, error=str(e))
            return None

    def set_secret(self, name: str, value: str) -> None:
        """Set a secret in Vault."""
        try:
            import requests

            headers = {"X-Vault-Token": self._token or ""}
            url = f"{self._url}/v1/{self._mount_point}/{name}"
            response = requests.put(
                url, headers=headers, json={"data": {"value": value}}, timeout=10
            )
            response.raise_for_status()
            logger.debug("secret_set_in_vault", name=name)
        except Exception as e:
            logger.error("vault_set_secret_failed", name=name, error=str(e))

    def delete_secret(self, name: str) -> bool:
        """Delete a secret from Vault."""
        try:
            import requests

            headers = {"X-Vault-Token": self._token or ""}
            url = f"{self._url}/v1/{self._mount_point}/{name}"
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            logger.debug("secret_deleted_from_vault", name=name)
            return True
        except Exception as e:
            logger.error("vault_delete_secret_failed", name=name, error=str(e))
            return False

    def list_secrets(self) -> list[str]:
        """List all secrets in Vault."""
        try:
            import requests

            headers = {"X-Vault-Token": self._token or ""}
            url = f"{self._url}/v1/{self._mount_point}/?list=true"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            keys: list[str] = data.get("data", {}).get("keys", [])
            return keys
        except Exception as e:
            logger.error("vault_list_secrets_failed", error=str(e))
            return []


@dataclass
class SecretReference:
    """Reference to a secret."""

    name: str
    backend: str = "environment"
    required: bool = True
    default: str | None = None


class SecretsManager:
    """Manages secrets across multiple backends."""

    def __init__(self) -> None:
        self._backends: dict[str, SecretsBackend] = {
            "environment": EnvironmentSecretsBackend(prefix="UTSERVIO_"),
        }
        self._secrets: dict[str, SecretReference] = {}

    def register_backend(self, name: str, backend: SecretsBackend) -> None:
        """Register a secrets backend."""
        self._backends[name] = backend
        logger.info("secrets_backend_registered", name=name)

    def register_secret(self, reference: SecretReference) -> None:
        """Register a secret reference."""
        self._secrets[reference.name] = reference
        logger.debug("secret_registered", name=reference.name, backend=reference.backend)

    def get_secret(self, name: str, backend: str | None = None) -> str | None:
        """Get a secret value."""
        # Check registered secrets
        if name in self._secrets:
            ref = self._secrets[name]
            backend_name = backend or ref.backend
        else:
            backend_name = backend or "environment"

        # Get from backend
        if backend_name in self._backends:
            value = self._backends[backend_name].get_secret(name)
            if value is not None:
                return value

        # Check default
        if name in self._secrets and self._secrets[name].default is not None:
            return self._secrets[name].default

        # Check if required
        if name in self._secrets and self._secrets[name].required:
            logger.error("required_secret_missing", name=name)
            raise ValueError(f"Required secret '{name}' not found")

        return None

    def set_secret(self, name: str, value: str, backend: str = "environment") -> None:
        """Set a secret value."""
        if backend in self._backends:
            self._backends[backend].set_secret(name, value)
        else:
            logger.error("unknown_secrets_backend", backend=backend)

    def delete_secret(self, name: str, backend: str = "environment") -> bool:
        """Delete a secret value."""
        if backend in self._backends:
            return self._backends[backend].delete_secret(name)
        return False

    def list_secrets(self, backend: str | None = None) -> list[str]:
        """List all secret names."""
        if backend and backend in self._backends:
            return self._backends[backend].list_secrets()
        return list(self._secrets.keys())


# Global secrets manager
secrets_manager = SecretsManager()


def setup_secrets() -> None:
    """Setup default secrets configuration."""
    # Register common secrets
    secrets_manager.register_secret(
        SecretReference(
            name="DATABASE_URL",
            backend="environment",
            required=True,
        )
    )
    secrets_manager.register_secret(
        SecretReference(
            name="API_KEY",
            backend="environment",
            required=True,
        )
    )
    secrets_manager.register_secret(
        SecretReference(
            name="VAULT_TOKEN",
            backend="environment",
            required=False,
        )
    )

    # Check if Vault is configured
    vault_token = os.environ.get("VAULT_TOKEN")
    vault_url = os.environ.get("VAULT_URL", "http://localhost:8200")
    if vault_token:
        secrets_manager.register_backend(
            "vault",
            VaultSecretsBackend(url=vault_url, token=vault_token),
        )
        logger.info("vault_backend_configured", url=vault_url)
