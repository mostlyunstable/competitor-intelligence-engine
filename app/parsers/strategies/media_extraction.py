"""Media Extraction — extract logos, images, icons, videos, PDFs, and downloads.

Uses structural clues (element type, attributes, context) to identify
media assets.  No class names, no visual rendering.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin, urlparse

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

    from app.parsers.page_segmenter import PageSegment

_IMAGE_EXT = re.compile(r"\.(png|jpg|jpeg|gif|svg|webp|avif|ico)", re.IGNORECASE)
_VIDEO_EXT = re.compile(r"\.(mp4|webm|ogg|mov|avi|mkv)", re.IGNORECASE)
_DOC_EXT = re.compile(r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx|csv)", re.IGNORECASE)


class MediaExtractionStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "media_extraction"

    @property
    def weight(self) -> float:
        return 0.10

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_logo(soup, result, url)
        self._extract_images(soup, result, url)
        self._extract_videos(soup, result, url)
        self._extract_downloads(soup, result, url)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            if seg.segment_type == "hero":
                self._extract_logo(soup, result, url)
            elif seg.segment_type in ("gallery", "hero"):
                self._extract_images(soup, result, url)
            self._extract_videos(soup, result, url)
            self._extract_downloads(soup, result, url)
        return result

    def _extract_logo(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        """Extract company logo from header, nav, or schema markup."""
        if result.logo:
            return
        # Check JSON-LD / structured data first (handled by other strategies)
        # Fallback: find logo in header / nav area
        for container in soup.select("header, nav, div[itemscope], [itemtype]"):
            img = container.select_one("img[src]")
            if not img:
                continue
            src = str(img.get("src", ""))
            if not src:
                continue
            # Likely a logo if it's in the header and small
            result.logo = urljoin(url, src)
            return

    def _extract_images(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        """Extract service/product images and gallery images."""
        seen_srcs: set[str] = set()
        for img in soup.select("img[src]"):
            src = str(img.get("src", ""))
            if not src:
                continue
            full_url = urljoin(url, src)
            if not _IMAGE_EXT.search(full_url):
                continue
            if full_url in seen_srcs:
                continue
            seen_srcs.add(full_url)

            alt = str(img.get("alt", "")).strip() or None
            title = str(img.get("title", "")).strip() or alt or None
            width = img.get("width")
            height = img.get("height")

            # Skip tiny icons (likely UI elements, not content)
            try:
                if width is not None and int(str(width)) < 48:
                    continue
                if height is not None and int(str(height)) < 48:
                    continue
            except (ValueError, TypeError):
                pass

            # Determine if this is a service/product image or decorative
            parent = img.find_parent(["div", "section", "article", "figure", "li"])
            parent_text = parent.get_text(" ", strip=True).lower() if parent else ""

            media_type = "image"
            if any(kw in parent_text for kw in ("service", "product", "offer", "plan")):
                media_type = "service_image"
            elif any(kw in parent_text for kw in ("gallery", "portfolio", "showcase")):
                media_type = "gallery_image"

            media_entry: dict[str, Any] = {
                "type": media_type,
                "url": full_url,
                "title": title,
                "alt_text": alt,
                "mime_type": self._guess_mime(full_url),
            }
            if title and title not in [m.get("title") for m in result.media]:
                media_entry["title"] = title
            result.media.append(media_entry)

    def _extract_videos(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        """Extract video URLs from video tags and iframe embeds."""
        seen_urls: set[str] = set()

        for video in soup.select("video source[src], video[src]"):
            src = str(video.get("src", ""))
            if src and src not in seen_urls:
                seen_urls.add(src)
                result.media.append(
                    {
                        "type": "video",
                        "url": urljoin(url, src),
                        "title": None,
                        "alt_text": None,
                        "mime_type": self._guess_mime(src),
                    }
                )

        for iframe in soup.select("iframe[src]"):
            src = str(iframe.get("src", ""))
            if not src:
                continue
            # Detect video embeds
            if (
                any(
                    domain in src.lower()
                    for domain in ("youtube", "youtu.be", "vimeo", "wistia", "loom")
                )
                and src not in seen_urls
            ):
                seen_urls.add(src)
                result.media.append(
                    {
                        "type": "video_embed",
                        "url": src,
                        "title": str(iframe.get("title", "")) or None,
                        "alt_text": None,
                        "mime_type": "text/html",
                    }
                )

    def _extract_downloads(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        """Extract downloadable documents (PDFs, brochures, spec sheets)."""
        seen_urls: set[str] = set()
        for a in soup.select("a[href]"):
            href = str(a.get("href", ""))
            if not href:
                continue
            full_url = urljoin(url, href)
            if not _DOC_EXT.search(full_url):
                continue
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            text = a.get_text(strip=True) or None
            result.media.append(
                {
                    "type": "download",
                    "url": full_url,
                    "title": text,
                    "alt_text": None,
                    "mime_type": self._guess_mime(full_url),
                }
            )

    @staticmethod
    def _guess_mime(url_str: str) -> str:
        ext = urlparse(url_str).path.split(".")[-1].lower() if "." in url_str else ""
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "svg": "image/svg+xml",
            "webp": "image/webp",
            "avif": "image/avif",
            "ico": "image/x-icon",
            "mp4": "video/mp4",
            "webm": "video/webm",
            "ogg": "video/ogg",
            "mov": "video/quicktime",
            "avi": "video/x-msvideo",
            "mkv": "video/x-matroska",
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
        }
        return mime_map.get(ext, "application/octet-stream")
