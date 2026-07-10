import re


class BudgetEngine:
    def __init__(self, max_pages: int = 50, max_depth: int = 3, max_time_seconds: int = 600):
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.max_time_seconds = max_time_seconds

    def score_url(self, url: str) -> int:
        score = 0
        url_lower = url.lower()

        if re.search(r"/pricing|/plans|/costs", url_lower):
            score += 50
        if re.search(r"/services|/solutions|/products", url_lower):
            score += 40
        if re.search(r"/about|/team|/company", url_lower):
            score += 30
        if re.search(r"/features|/benefits", url_lower):
            score += 25
        if re.search(r"/faq|/help|/support", url_lower):
            score += 20
        if re.search(r"/blog|/resources|/news", url_lower):
            score += 10

        # Penalize deeply nested URLs
        depth = url.strip("/").count("/")
        if depth > 2:
            score -= (depth - 2) * 5

        # Penalize likely unhelpful files
        if re.search(r"\.(pdf|jpg|jpeg|png|gif|svg|css|js|woff|woff2)$", url_lower):
            score -= 100

        return score

    def prioritize(self, urls: list[str]) -> list[str]:
        # Filter and sort URLs based on score
        scored_urls = [(url, self.score_url(url)) for url in urls]
        # Sort descending by score
        scored_urls.sort(key=lambda x: x[1], reverse=True)

        # Return top URLs up to max_pages
        return [url for url, score in scored_urls if score > -50][: self.max_pages]


budget_engine = BudgetEngine()
