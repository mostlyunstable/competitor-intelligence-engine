"""Crawl frontier with intelligent page prioritization.

Implements priority-based crawling with:
- URL scoring based on content potential
- Depth-limited crawling
- Change frequency detection
- Budget-aware scheduling
"""

from app.crawlfrontier.frontier import CrawlFrontier, FrontierURL, Priority

__all__ = ["CrawlFrontier", "FrontierURL", "Priority"]
