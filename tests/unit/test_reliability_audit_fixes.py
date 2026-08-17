"""Regression tests for reliability audit fixes."""

import pytest
from bs4 import BeautifulSoup
from app.parsers.resolution import EntityResolver
from app.parsers.strategy import ParsedResult
from app.parsers.strategies.json_ld import JsonLdStrategy, _safe_float
from app.parsers.strategies.schema_org import _safe_float as schema_safe_float, _safe_int as schema_safe_int


def test_entity_resolution_word_boundary():
    """Verify that short keywords like 'ac' or 'tap' don't match substrings in unrelated words."""
    resolver = EntityResolver()
    
    # 'Facial' or 'Back Massage' must NOT match 'ac' from appliance-repair
    result = ParsedResult()
    result.services.append({"name": "Full Facial Treatment", "category": ""})
    result.services.append({"name": "Back Massage", "category": ""})
    result.services.append({"name": "Split AC Installation", "category": ""})
    
    resolver.map_to_catalog(result)
    
    assert result.services[0]["category"] == "other"
    assert result.services[1]["category"] == "other"
    assert result.services[2]["category"] == "appliance-repair"


def test_safe_float_parser_varieties():
    """Verify that _safe_float gracefully parses formatted currency and numbers."""
    assert _safe_float("$49.99") == 49.99
    assert _safe_float("₹1,249.50") == 1249.50
    assert _safe_float("Free") is None
    assert _safe_float(None) is None
    assert _safe_float(150) == 150.0


def test_schema_org_safe_numeric_parsing():
    """Verify safe float and int conversion in schema.org parsing."""
    assert schema_safe_float("4.8") == 4.8
    assert schema_safe_float("4.8/5.0") == 4.8
    assert schema_safe_float("N/A") is None
    
    assert schema_safe_int("1,250 reviews") == 1250
    assert schema_safe_int("150+") == 150
    assert schema_safe_int(None) is None


def test_json_ld_offer_safe_extraction():
    """Verify JSON-LD strategy does not crash on formatted string pricing."""
    strategy = JsonLdStrategy()
    html = """
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Offer",
      "name": "Special Clean",
      "price": "$59.99",
      "priceCurrency": "USD"
    }
    </script>
    """
    soup = BeautifulSoup(html, "html.parser")
    result = strategy.parse(soup, "https://example.com")
    assert len(result.pricing) == 1
    assert result.pricing[0]["base_price"] == 59.99
