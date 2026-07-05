from typing import Any, ClassVar
from urllib.parse import urljoin

from app.parsers.base import BaseParser


class SocialParser(BaseParser):
    PLATFORMS: ClassVar[dict[str, str]] = {
        "linkedin.com": "linkedin",
        "facebook.com": "facebook",
        "instagram.com": "instagram",
        "twitter.com": "twitter",
        "x.com": "twitter",
        "youtube.com": "youtube",
        "pinterest.com": "pinterest",
        "threads.net": "threads",
    }

    def parse(self, html: str, url: str) -> dict[str, Any]:
        soup = self._soup(html)

        return {
            "url": url,
            "social_profiles": self._extract_social_profiles(soup, url),
        }

    def _extract_social_profiles(self, soup: Any, base_url: str) -> list[dict[str, str]]:
        profiles = []
        seen_platforms = set()

        # 1. Prefer <link rel="me"> — canonical social identity declarations
        rel_me_profiles = self._extract_rel_me_links(soup, base_url)
        for profile in rel_me_profiles:
            if profile["platform"] not in seen_platforms:
                profiles.append(profile)
                seen_platforms.add(profile["platform"])

        # 2. Fall back to scanning anchor tags
        for a_tag in soup.select("a[href]"):
            href = str(a_tag.get("href", ""))
            for domain, platform in self.PLATFORMS.items():
                if domain in href and platform not in seen_platforms:
                    full_url = urljoin(base_url, href)
                    if not self._is_valid_profile_url(full_url, domain):
                        continue
                    username = self._extract_username(href, domain)
                    profiles.append(
                        {
                            "platform": platform,
                            "profile_url": full_url,
                            "username": username or "",
                        }
                    )
                    seen_platforms.add(platform)

        meta_profiles = self._extract_meta_social(soup, base_url)
        for profile in meta_profiles:
            if profile["platform"] not in seen_platforms:
                profiles.append(profile)
                seen_platforms.add(profile["platform"])

        return profiles

    def _extract_rel_me_links(self, soup: Any, base_url: str) -> list[dict[str, str]]:
        """Extract social profiles from <link rel="me"> tags (canonical identity)."""
        profiles = []
        for link_el in soup.select("link[rel='me'], a[rel='me']"):
            href = str(link_el.get("href", ""))
            for domain, platform in self.PLATFORMS.items():
                if domain in href:
                    full_url = urljoin(base_url, href)
                    username = self._extract_username(href, domain)
                    profiles.append(
                        {
                            "platform": platform,
                            "profile_url": full_url,
                            "username": username or "",
                        }
                    )
                    break
        return profiles

    def _is_valid_profile_url(self, url: str, domain: str) -> bool:
        """Return False if the URL is a bare root social domain (share button, not a profile)."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Must have a meaningful path segment
        if not path:
            return False

        # LinkedIn: must have /company/ or /in/ in path
        if "linkedin.com" in domain:
            return "/company/" in url or "/in/" in url or "/school/" in url

        return True

    def _extract_username(self, href: str, domain: str) -> str | None:
        from urllib.parse import urlparse

        parsed = urlparse(href)
        path = parsed.path.rstrip("/")

        if domain == "linkedin.com":
            parts = path.split("/")
            if len(parts) >= 2:
                return parts[-1] if parts[-1] != "company" else parts[-2]
        elif domain in ("twitter.com", "x.com", "instagram.com", "facebook.com"):
            parts = path.split("/")
            if parts:
                return parts[-1]
        elif domain == "youtube.com":
            if "/channel/" in path or "/c/" in path or "/@" in path:
                parts = path.split("/")
                return parts[-1]
        elif domain == "pinterest.com":
            parts = path.split("/")
            if len(parts) >= 2:
                return parts[-1]
        return None

    def _extract_meta_social(self, soup: Any, base_url: str) -> list[dict[str, str]]:
        profiles = []
        for meta in soup.select("meta[property], meta[name]"):
            content = meta.get("content", "")
            prop = meta.get("property", "") or meta.get("name", "")

            if "twitter" in prop.lower() and content.startswith("http"):
                profiles.append(
                    {
                        "platform": "twitter",
                        "profile_url": content,
                        "username": None,
                    }
                )
            elif "og:url" in prop.lower() and any(d in content for d in self.PLATFORMS):
                for domain, platform in self.PLATFORMS.items():
                    if domain in content:
                        profiles.append(
                            {
                                "platform": platform,
                                "profile_url": content,
                                "username": None,
                            }
                        )
                        break
        return profiles
