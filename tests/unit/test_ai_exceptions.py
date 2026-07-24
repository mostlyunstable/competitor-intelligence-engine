"""Tests for AI module exceptions."""

import pytest

from app.ai.exceptions import (
    AIError,
    ProviderError,
    ValidationError,
    PromptError,
    PipelineError,
    WorkerError,
    StorageError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_ai_error(self) -> None:
        for exc_class in [ProviderError, ValidationError, PromptError, PipelineError, WorkerError, StorageError]:
            assert issubclass(exc_class, AIError)

    def test_ai_error_is_base_exception(self) -> None:
        assert issubclass(AIError, Exception)


class TestProviderError:
    def test_stores_provider_and_status(self) -> None:
        err = ProviderError("fail", provider="openai", status_code=429)
        assert err.provider == "openai"
        assert err.status_code == 429
        assert str(err) == "fail"

    def test_defaults(self) -> None:
        err = ProviderError("fail")
        assert err.provider == ""
        assert err.status_code == 0


class TestValidationError:
    def test_stores_errors(self) -> None:
        err = ValidationError("invalid", errors=["field missing", "bad type"])
        assert err.errors == ["field missing", "bad type"]

    def test_defaults(self) -> None:
        err = ValidationError("invalid")
        assert err.errors == []
