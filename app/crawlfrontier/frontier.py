"""Crawl frontier with intelligent page prioritization.

Implements priority-based crawling with:
- URL scoring based on content potential
- Depth-limited crawling
- Change frequency detection
- Budget-aware scheduling
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import structlog

logger = structlog.get_logger()


class Priority(IntEnum):
    """URL priority levels."""

    CRITICAL = 0  # Homepage, sitemap
    HIGH = 1  # Service pages, pricing
    MEDIUM = 2  # About, team, contact
    LOW = 3  # Blog, news, articles
    BACKGROUND = 4  # Archives, old content


@dataclass
class FrontierURL:
    """URL in the crawl frontier with priority and metadata."""

    url: str
    priority: Priority
    depth: int = 0
    score: float = 0.0
    last_crawled: float | None = None
    change_frequency: float = 0.0  # Changes per day
    content_potential: float = 0.0  # Expected extraction value
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: FrontierURL) -> bool:
        """Compare for priority queue ordering."""
        if self.priority != other.priority:
            return self.priority < other.priority
        if self.score != other.score:
            return self.score > other.score
        return self.created_at < other.created_at


class CrawlFrontier:
    """Intelligent crawl frontier with priority-based scheduling."""

    def __init__(
        self,
        max_depth: int = 3,
        max_urls: int = 10000,
        score_decay: float = 0.95,
    ) -> None:
        self._max_depth = max_depth
        self._max_urls = max_urls
        self._score_decay = score_decay

        # Priority queue
        self._queue: list[FrontierURL] = []
        self._queued_urls: set[str] = set()

        # Crawled URLs tracking
        self._crawled: dict[str, FrontierURL] = {}
        self._failed: dict[str, int] = {}  # URL -> failure count

        # Statistics
        self._stats = {
            "total_queued": 0,
            "total_crawled": 0,
            "total_failed": 0,
            "total_budget_exceeded": 0,
        }

    def add_url(
        self,
        url: str,
        priority: Priority = Priority.MEDIUM,
        depth: int = 0,
        score: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Add a URL to the frontier."""
        if url in self._queued_urls or url in self._crawled:
            return False

        if len(self._queue) >= self._max_urls:
            logger.warning("frontier_full", url=url, max_urls=self._max_urls)
            self._stats["total_budget_exceeded"] += 1
            return False

        if depth > self._max_depth:
            logger.debug("depth_exceeded", url=url, depth=depth, max_depth=self._max_depth)
            return False

        frontier_url = FrontierURL(
            url=url,
            priority=priority,
            depth=depth,
            score=score,
            metadata=metadata or {},
        )

        heapq.heappush(self._queue, frontier_url)
        self._queued_urls.add(url)
        self._stats["total_queued"] += 1

        logger.debug("url_queued", url=url, priority=priority.name, depth=depth, score=score)
        return True

    def get_next_url(self) -> FrontierURL | None:
        """Get the next URL to crawl."""
        while self._queue:
            frontier_url = heapq.heappop(self._queue)
            self._queued_urls.discard(frontier_url.url)

            # Skip if already crawled
            if frontier_url.url in self._crawled:
                continue

            # Skip if too many failures
            if self._failed.get(frontier_url.url, 0) >= 3:
                logger.debug("url_skip_failed", url=frontier_url.url)
                continue

            return frontier_url

        return None

    def mark_crawled(self, url: str, success: bool = True) -> None:
        """Mark a URL as crawled."""
        if url in self._queued_urls:
            self._queued_urls.discard(url)

        if success:
            self._crawled[url] = FrontierURL(
                url=url,
                priority=Priority.LOW,
                last_crawled=time.time(),
            )
            self._stats["total_crawled"] += 1
        else:
            self._failed[url] = self._failed.get(url, 0) + 1
            self._stats["total_failed"] += 1

    def get_frontier_stats(self) -> dict[str, Any]:
        """Get frontier statistics."""
        return {
            "queue_size": len(self._queue),
            "crawled_count": len(self._crawled),
            "failed_count": len(self._failed),
            "stats": self._stats,
            "priority_distribution": self._get_priority_distribution(),
        }

    def _get_priority_distribution(self) -> dict[str, int]:
        """Get distribution of URLs by priority."""
        distribution: dict[str, int] = {}
        for url in self._queue:
            priority_name = url.priority.name
            distribution[priority_name] = distribution.get(priority_name, 0) + 1
        return distribution

    def get_urls_by_priority(self, priority: Priority) -> list[str]:
        """Get all URLs with a specific priority."""
        return [url.url for url in self._queue if url.priority == priority]

    def clear(self) -> None:
        """Clear the frontier."""
        self._queue.clear()
        self._queued_urls.clear()
        self._crawled.clear()
        self._failed.clear()
        self._stats = {
            "total_queued": 0,
            "total_crawled": 0,
            "total_failed": 0,
            "total_budget_exceeded": 0,
        }

    def calculate_priority(
        self,
        url: str,
        depth: int = 0,
        is_sitemap: bool = False,
        has_services: bool = False,
        has_pricing: bool = False,
    ) -> Priority:
        """Calculate URL priority based on content potential."""
        url_lower = url.lower()

        # Critical: Homepage, sitemap
        if is_sitemap or url.endswith("/") or url.endswith("/sitemap.xml"):
            return Priority.CRITICAL

        # High: Service pages, pricing
        if has_services or has_pricing:
            return Priority.HIGH

        service_keywords = [
            "service",
            "services",
            "pricing",
            "price",
            "plan",
            "plans",
            "product",
            "products",
            "solution",
            "solutions",
            "offer",
        ]
        if any(kw in url_lower for kw in service_keywords):
            return Priority.HIGH

        # Medium: About, team, contact
        info_keywords = [
            "about",
            "team",
            "contact",
            "company",
            "leadership",
            "careers",
            "location",
            "locations",
            "office",
        ]
        if any(kw in url_lower for kw in info_keywords):
            return Priority.MEDIUM

        # Low: Blog, news, articles
        content_keywords = [
            "blog",
            "news",
            "article",
            "articles",
            "post",
            "posts",
            "press",
            "release",
            "releases",
            "resource",
            "resources",
        ]
        if any(kw in url_lower for kw in content_keywords):
            return Priority.LOW

        # Background: Archives, old content
        archive_keywords = [
            "archive",
            "archives",
            "old",
            "history",
            "past",
            "year",
            "month",
            "category",
        ]
        if any(kw in url_lower for kw in archive_keywords):
            return Priority.BACKGROUND

        # Default based on depth
        depth_priority = {
            0: Priority.CRITICAL,
            1: Priority.HIGH,
            2: Priority.MEDIUM,
        }
        return depth_priority.get(depth, Priority.LOW)

    def score_url(
        self,
        url: str,
        depth: int = 0,
        last_modified: float | None = None,
        change_frequency: float = 0.0,
    ) -> float:
        """Calculate URL score for prioritization."""
        score = 0.0

        # Depth penalty (lower depth = higher score)
        score += max(0, 10 - depth * 2)

        # Freshness bonus (recently modified = higher score)
        if last_modified:
            days_since_modified = (time.time() - last_modified) / 86400
            freshness = max(0, 1 - days_since_modified / 30)  # Decays over 30 days
            score += freshness * 5

        # Change frequency bonus
        score += min(change_frequency * 10, 5)  # Cap at 5

        # URL quality signals
        # Bonus for clean URLs (no query params, no deep paths)
        if "?" not in url and url.count("/") <= 4:
            score += 2

        # Bonus for HTTPS
        if url.startswith("https://"):
            score += 1

        # Penalty for very long URLs
        if len(url) > 100:
            score -= 1

        # Penalty for URLs with many segments
        if url.count("/") > 5:
            score -= 2

        return max(0, score)

    def estimate_content_potential(self, url: str) -> float:
        """Estimate content extraction potential."""
        url_lower = url.lower()
        potential = 0.0

        # High potential: Service, pricing, team pages
        high_potential_keywords = [
            "service",
            "pricing",
            "plan",
            "team",
            "about",
            "product",
            "solution",
            "company",
        ]
        if any(kw in url_lower for kw in high_potential_keywords):
            potential += 0.8

        # Medium potential: Blog, resources
        medium_potential_keywords = [
            "blog",
            "resource",
            "article",
            "news",
        ]
        if any(kw in url_lower for kw in medium_potential_keywords):
            potential += 0.5

        # Low potential: Archives, legal
        low_potential_keywords = [
            "archive",
            "legal",
            "privacy",
            "terms",
            "policy",
        ]
        if any(kw in url_lower for kw in low_potential_keywords):
            potential += 0.2

        return min(potential, 1.0)
