"""URL normalization for consistent duplicate detection.

Canonical URL normalization ensures that functionally identical URLs
are reduced to a single canonical form before comparison or hashing.
"""

from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

# Query parameters to strip during normalization (tracking/analytics noise)
_STRIP_PARAMS: set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def normalize_url(url: str, *, base_url: str | None = None) -> str:
    """Normalize a URL to its canonical form.

    Steps:
        1. Resolve relative URLs against base_url
        2. Lowercase scheme and host
        3. Strip default ports (80/443)
        4. Remove trailing slash from path (except root)
        5. Sort query parameters
        6. Strip tracking parameters
        7. Remove fragment
        8. Remove www. prefix from host

    Args:
        url: The URL to normalize.
        base_url: Optional base URL for resolving relative paths.

    Returns:
        The canonical URL string.
    """
    if not url:
        return url

    # Resolve relative URLs
    if base_url:
        url = urljoin(base_url, url)

    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Strip www. prefix
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Normalize path
    path = parsed.path
    if path == "/":
        pass  # Keep root path as-is
    elif path.endswith("/"):
        path = path.rstrip("/")

    # Sort and filter query parameters
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    filtered_params = {k: v for k, v in query_params.items() if k.lower() not in _STRIP_PARAMS}
    sorted_query = urlencode(sorted(filtered_params.items()), doseq=True)

    # Reconstruct URL without fragment
    normalized = urlunparse(
        (
            scheme,
            netloc,
            path,
            parsed.params,
            sorted_query,
            "",  # No fragment
        )
    )

    return normalized


def normalize_content_url(url: str, *, base_url: str | None = None) -> str:
    """Normalize a content URL for deduplication.

    Strips trailing slashes and normalizes to allow content-level matching.
    """
    normalized = normalize_url(url, base_url=base_url)
    # For content URLs, also strip trailing slashes for comparison
    if normalized.endswith("/") and len(normalized) > 1:
        normalized = normalized.rstrip("/")
    return normalized
