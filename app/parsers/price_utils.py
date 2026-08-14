"""Shared price parsing and currency detection utilities."""
import re

# Currency symbol to code mapping
CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
    "C$": "CAD",
    "A$": "AUD",
}

# Currency codes for detection
CURRENCY_CODES = {"USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD"}

# Compiled regex for price extraction — covers Indian formats (Rs., ₹, /-, ranges)
_PRICE_RE = re.compile(
    r"""
    (?:
        (?P<sym>[$€£₹¥])       # leading currency symbol
        \s*
    )?
    (?P<amount>[\d,]+(?:\.\d{1,2})?)   # numeric amount
    (?:
        \s*
        (?P<code>[A-Z]{3})             # trailing ISO currency code
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Indian price patterns: "Rs. 499", "₹499/-", "₹ 499", "from ₹499", "starting at Rs.499"
_INDIAN_PRICE_RE = re.compile(
    r'(?:rs\.?\s*|₹\s*|from\s+₹?\s*|starting\s+(?:at|from)\s+₹?\s*|price[:\s]*₹?\s*)'
    r'([\d,]+(?:\.\d{1,2})?)'
    r'(?:\s*/-|\s*onwards|\s*per\s+\w+|\s*/\s*\w+)?',
    re.IGNORECASE,
)

# Range pattern: "₹499 - ₹999", "Rs. 499-999", "499-999"
_PRICE_RANGE_RE = re.compile(
    r'(?:₹|rs\.?\s*)?\s*([\d,]+(?:\.\d{1,2})?)'
    r'\s*[-–to]+\s*'
    r'(?:₹|rs\.?\s*)?\s*([\d,]+(?:\.\d{1,2})?)',
    re.IGNORECASE,
)


def parse_price(text: str | None) -> float | None:
    """Extract numeric price from text, handling Indian notation (Rs., /-, ranges)."""
    if not text:
        return None

    # Check for Indian price patterns first (most common for our market)
    indian_match = _INDIAN_PRICE_RE.search(text)
    if indian_match:
        try:
            return float(indian_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Check for price range — return the lower bound
    range_match = _PRICE_RANGE_RE.search(text)
    if range_match:
        try:
            return float(range_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Check for Rs. prefix (Indian notation)
    rs_match = re.search(r'rs\.?\s*([\d,]+(?:\.\d{1,2})?)', text.lower())
    if rs_match:
        try:
            return float(rs_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Check for /- suffix (Indian notation)
    slash_match = re.search(r'([\d,]+(?:\.\d{1,2})?)/-', text)
    if slash_match:
        try:
            return float(slash_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Generic number extraction
    clean = text.replace(",", "")
    numbers = re.findall(r"[\d]+\.?\d*", clean)
    if numbers:
        try:
            return float(numbers[0])
        except ValueError:
            return None
    return None


def parse_price_with_currency(text: str) -> tuple[float | None, str]:
    """Return (amount, currency_code) from arbitrary text."""
    if not text:
        return None, "INR"

    # Check for Rs. prefix (Indian notation)
    if re.search(r'rs\.?\s*\d', text.lower()):
        m = _PRICE_RE.search(text.replace(",", ""))
        if m:
            amount_str = m.group("amount").replace(",", "")
            try:
                amount = float(amount_str)
            except ValueError:
                return None, "INR"
            return amount, "INR"
        # Fallback: extract number after Rs.
        rs_match = re.search(r'rs\.?\s*([\d,]+(?:\.\d{1,2})?)', text.lower())
        if rs_match:
            try:
                amount = float(rs_match.group(1).replace(",", ""))
                return amount, "INR"
            except ValueError:
                pass
        return None, "INR"

    m = _PRICE_RE.search(text.replace(",", ""))
    if not m:
        return None, "INR"
    amount_str = m.group("amount").replace(",", "")
    try:
        amount = float(amount_str)
    except ValueError:
        return None, "INR"
    sym = m.group("sym") or ""
    code = m.group("code") or ""
    currency = code.upper() if code else CURRENCY_SYMBOLS.get(sym, "INR")
    return amount, currency


def detect_currency(price_text: str | None) -> str:
    """Detect currency code from price text. Defaults to INR for Indian market."""
    if not price_text:
        return "INR"

    # Check ₹ and Rs. first (Indian market priority)
    if "₹" in price_text or "rs" in price_text.lower() or "inr" in price_text.lower():
        return "INR"

    # Check standard symbols
    if "$" in price_text:
        return "USD"
    if "€" in price_text:
        return "EUR"
    if "£" in price_text:
        return "GBP"

    # Check currency codes
    upper = price_text.upper()
    for code in CURRENCY_CODES:
        if code in upper:
            return code

    return "INR"
