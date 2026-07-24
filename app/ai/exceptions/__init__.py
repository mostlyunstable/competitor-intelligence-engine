"""AI module exception hierarchy."""


class AIError(Exception):
    """Base exception for all AI module errors."""


class ProviderError(AIError):
    """Raised when an LLM provider fails (network, auth, rate limit)."""

    def __init__(self, message: str, provider: str = "", status_code: int = 0):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class ValidationError(AIError):
    """Raised when LLM output fails schema or field validation."""

    def __init__(self, message: str, errors: list | None = None):
        super().__init__(message)
        self.errors = errors or []


class PromptError(AIError):
    """Raised when prompt construction fails (missing data, template error)."""


class PipelineError(AIError):
    """Raised when the AI pipeline fails end-to-end."""


class WorkerError(AIError):
    """Raised when the background worker encounters an unrecoverable error."""


class StorageError(AIError):
    """Raised when database or file storage operations fail."""
