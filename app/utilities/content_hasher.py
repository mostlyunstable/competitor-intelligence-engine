"""Content hashing for duplicate detection across collection runs.

Uses SHA-256 to generate deterministic content fingerprints that
detect identical data regardless of collection timing or ordering.
"""

import hashlib
import re
from typing import Any


def _canonicalize_value(value: Any) -> str:
    """Convert a value to a canonical string representation."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value.strip().lower())
    if isinstance(value, list):
        items = [_canonicalize_value(item) for item in value]
        return "[" + ",".join(items) + "]"
    if isinstance(value, dict):
        items = []
        for key in sorted(value.keys()):
            items.append(f"{key}:{_canonicalize_value(value[key])}")
        return "{" + ",".join(items) + "}"
    return re.sub(r"\s+", " ", str(value).strip().lower())


def compute_content_hash(*fields: Any) -> str:
    """Compute a SHA-256 hash from one or more field values.

    Fields are canonicalized before hashing to ensure consistent results
    regardless of whitespace, case, or ordering of collections/dicts.

    Args:
        *fields: Variable number of values to hash together.

    Returns:
        Hex-encoded SHA-256 hash string (64 characters).

    Example:
        >>> compute_content_hash("AC Repair", "home-services", 99.99)
        'a1b2c3d4...'
    """
    canonical_parts = [_canonicalize_value(field) for field in fields]
    joined = "|".join(canonical_parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def compute_page_content_hash(html: str, url: str) -> str:
    """Compute content hash for a raw page snapshot."""
    return compute_content_hash(html, url)


def compute_service_hash(
    service_name: str,
    service_category: str | None = None,
    description: str | None = None,
    starting_price: float | None = None,
    currency: str = "USD",
) -> str:
    """Compute content hash for a service listing."""
    return compute_content_hash(
        service_name,
        service_category or "",
        description or "",
        starting_price if starting_price is not None else "",
        currency,
    )


def compute_pricing_hash(
    service_name: str,
    category: str | None = None,
    base_price: float | None = None,
    promotional_price: float | None = None,
    currency: str = "USD",
) -> str:
    """Compute content hash for a pricing entry."""
    return compute_content_hash(
        service_name,
        category or "",
        base_price if base_price is not None else "",
        promotional_price if promotional_price is not None else "",
        currency,
    )


def compute_content_item_hash(
    title: str,
    url: str,
    author: str | None = None,
    publish_date: str | None = None,
    content_type: str | None = None,
) -> str:
    """Compute content hash for a content item (article, blog post, etc.)."""
    return compute_content_hash(
        title,
        url,
        author or "",
        publish_date or "",
        content_type or "",
    )


def compute_social_hash(
    platform: str,
    profile_url: str,
    username: str | None = None,
) -> str:
    """Compute content hash for a social profile."""
    return compute_content_hash(platform, profile_url, username or "")
