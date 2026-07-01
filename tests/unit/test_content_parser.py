from app.parsers.content import ContentParser


class TestContentParser:
    def setup_method(self) -> None:
        self.parser = ContentParser()

    def test_parse_articles(self) -> None:
        html = """
        <html>
        <body>
            <article>
                <h2><a href="/blog/post1">How to Choose HVAC</a></h2>
                <span class="author">John Doe</span>
                <span class="date">2024-01-15</span>
                <p class="summary">A guide to choosing HVAC systems</p>
            </article>
            <article>
                <h2><a href="/blog/post2">Winter Maintenance Tips</a></h2>
                <p class="summary">Keep your home warm this winter</p>
            </article>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com/blog")
        assert len(result["content"]) == 2
        assert result["content"][0]["title"] == "How to Choose HVAC"
        assert result["content"][0]["author"] == "John Doe"
        assert result["content"][0]["publish_date"] == "2024-01-15"
        assert result["content"][0]["url"] == "/blog/post1"

    def test_parse_blog_posts(self) -> None:
        html = """
        <html>
        <body>
            <div class="blog-post">
                <h3>New Service Launch</h3>
                <p>We are excited to announce our new service</p>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com/blog")
        assert len(result["content"]) == 1
        assert result["content"][0]["title"] == "New Service Launch"

    def test_parse_from_listing(self) -> None:
        html = """
        <html>
        <body>
            <ul>
                <li>
                    <h3><a href="/news/1">Important Update</a></h3>
                    <p>Here is what changed</p>
                </li>
            </ul>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com/news")
        assert len(result["content"]) == 1
        assert result["content"][0]["title"] == "Important Update"

    def test_parse_empty_page(self) -> None:
        html = "<html><body></body></html>"
        result = self.parser.parse(html, "https://example.com")
        assert result["content"] == []

    def test_detect_blog_type(self) -> None:
        html = """
        <html>
        <body>
            <div class="blog-post">
                <h3>Our Latest Blog</h3>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["content"][0]["content_type"] == "blog"

    def test_detect_news_type(self) -> None:
        html = """
        <html>
        <body>
            <div class="news-item">
                <h3>Breaking News</h3>
            </div>
        </body>
        </html>
        """
        result = self.parser.parse(html, "https://example.com")
        assert result["content"][0]["content_type"] == "news"
