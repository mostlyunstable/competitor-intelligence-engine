from bs4 import BeautifulSoup

from app.parsers.strategies.asset_extraction import AssetExtractionStrategy
from app.parsers.strategies.location_extraction import LocationExtractionStrategy
from app.parsers.strategies.review_extraction import ReviewExtractionStrategy
from app.parsers.strategies.team_extraction import TeamExtractionStrategy
from app.parsers.strategies.trust_signal_extraction import TrustSignalExtractionStrategy


def test_team_extraction():
    html = """
    <div>
        <div itemscope itemtype="https://schema.org/Person">
            <span itemprop="name">Jane Doe</span>
            <span itemprop="jobTitle">CEO</span>
        </div>
        <div class="team-member">
            <h3 class="name">John Smith</h3>
            <p class="role">CTO</p>
        </div>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    strategy = TeamExtractionStrategy()
    result = strategy.parse(soup, "https://example.com")

    assert len(result.team) == 2
    assert result.team[0]["name"] == "Jane Doe"
    assert result.team[0]["title"] == "CEO"
    assert result.team[1]["name"] == "John Smith"
    assert result.team[1]["title"] == "CTO"


def test_location_extraction():
    html = """
    <div>
        <div itemscope itemtype="https://schema.org/PostalAddress">
            <span itemprop="streetAddress">123 Main St</span>
            <span itemprop="addressLocality">San Francisco</span>
            <span itemprop="addressRegion">CA</span>
        </div>
        <address>456 Tech Ave, New York, NY</address>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    strategy = LocationExtractionStrategy()
    result = strategy.parse(soup, "https://example.com")

    assert len(result.locations) == 2
    assert "San Francisco" in result.locations[0]["name"]
    assert "CA" in result.locations[0]["name"]
    assert "456 Tech Ave" in result.locations[1]["name"]


def test_review_extraction():
    html = """
    <div>
        <div itemscope itemtype="https://schema.org/Review">
            <span itemprop="author">Alice</span>
            <span itemprop="reviewBody">Great service!</span>
            <span itemprop="reviewRating"><span itemprop="ratingValue">5</span></span>
        </div>
        <section>
            <h2>Testimonials</h2>
            <blockquote class="testimonial">
                <p>We loved working with them.</p>
                <cite class="name">Bob</cite>
            </blockquote>
        </section>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    strategy = ReviewExtractionStrategy()
    result = strategy.parse(soup, "https://example.com")

    assert len(result.reviews) == 2
    assert result.reviews[0]["author"] == "Alice"
    assert result.reviews[0]["rating"] == 5.0
    assert result.reviews[1]["author"] == "Bob"
    assert "We loved working with them" in result.reviews[1]["body"]


def test_trust_signal_extraction():
    html = """
    <footer>
        <h2>Certifications</h2>
        <ul>
            <li>SOC 2 Type II Certified</li>
            <li>GDPR Compliant</li>
            <li>Best Software Award 2023</li>
        </ul>
        <h3>Guarantees</h3>
        <p>30-Day Money Back Guarantee</p>
    </footer>
    """
    soup = BeautifulSoup(html, "html.parser")
    strategy = TrustSignalExtractionStrategy()
    result = strategy.parse(soup, "https://example.com")

    assert len(result.trust_signals) == 4
    types = [ts["type"] for ts in result.trust_signals]
    assert "certification" in types
    assert "award" in types
    assert "guarantee" in types

    names = [ts["name"] for ts in result.trust_signals]
    assert "SOC 2 Type II Certified" in names
    assert "30-Day Money Back Guarantee" in names


def test_asset_extraction():
    html = """
    <div>
        <a href="https://example.com/brochure.pdf">Download Brochure</a>
        <a href="/specs.docx">Technical Specs</a>
        <a href="/report.csv" download>Dataset</a>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    strategy = AssetExtractionStrategy()
    result = strategy.parse(soup, "https://example.com")

    assert len(result.assets) == 3
    assert result.assets[0]["type"] == "pdf"
    assert result.assets[1]["type"] == "docx"
    assert result.assets[2]["type"] == "csv"
    assert result.assets[0]["name"] == "Download Brochure"
