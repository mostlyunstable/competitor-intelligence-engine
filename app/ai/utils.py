"""Shared utilities for the AI module."""

import json
from decimal import Decimal
from typing import Any


def json_serialize(obj: Any) -> Any:
    """JSON serializer for non-standard types (Decimal, datetime, etc.)."""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def to_json(data: Any, indent: int = 2) -> str:
    """Serialize data to JSON string with custom serializer."""
    return json.dumps(data, indent=indent, default=json_serialize)
