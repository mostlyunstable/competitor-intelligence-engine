"""Enhanced data collection for additional business intelligence fields."""

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class EnhancedBusinessData:
    """Additional business data fields for competitor intelligence."""
    # Mobile app
    has_android_app: bool = False
    has_ios_app: bool = False
    android_app_url: str = ""
    ios_app_url: str = ""

    # Customer ratings
    google_rating: float = 0.0
    google_reviews_count: int = 0
    justdial_rating: float = 0.0
    justdial_reviews_count: int = 0
    sulekha_rating: float = 0.0

    # Payment methods
    accepts_upi: bool = False
    accepts_card: bool = False
    accepts_cash: bool = False
    accepts_netbanking: bool = False
    payment_methods: list[str] = field(default_factory=list)

    # Service features
    offers_emi: bool = False
    offers_insurance: bool = False
    has_verified_professionals: bool = False
    has_background_check: bool = False
    offers_guarantee: bool = False
    has_24_7_support: bool = False
    has_online_booking: bool = False
    has_walk_in: bool = False

    # Business hours
    business_hours: str = ""
    offers_weekend_service: bool = False
    offers_emergency_service: bool = False

    # Pricing signals
    has_transparent_pricing: bool = False
    offers_free_quotes: bool = False
    has_price_match: bool = False

    # Trust signals
    years_in_business: int = 0
    has_certifications: bool = False
    has_insurance: bool = False
    has_license: bool = False
    member_of_associations: list[str] = field(default_factory=list)

    # Social proof
    has_testimonials: bool = False
    has_case_studies: bool = False
    has_portfolio: bool = False
    social_media_followers: int = 0

    # Response metrics
    response_time_hours: int = 0
    same_day_service: bool = False
    next_day_service: bool = False


class EnhancedDataCollector:
    """Collects enhanced business data from HTML content."""

    def collect(self, html: str, url: str = "") -> EnhancedBusinessData:
        """Extract enhanced business data from HTML."""
        data = EnhancedBusinessData()

        html_lower = html.lower()

        # Detect mobile apps
        self._detect_mobile_apps(data, html_lower, url)

        # Detect ratings
        self._detect_ratings(data, html_lower)

        # Detect payment methods
        self._detect_payment_methods(data, html_lower)

        # Detect service features
        self._detect_service_features(data, html_lower)

        # Detect business hours
        self._detect_business_hours(data, html_lower)

        # Detect pricing signals
        self._detect_pricing_signals(data, html_lower)

        # Detect trust signals
        self._detect_trust_signals(data, html_lower)

        # Detect social proof
        self._detect_social_proof(data, html_lower)

        # Detect response metrics
        self._detect_response_metrics(data, html_lower)

        return data

    def _detect_mobile_apps(self, data: EnhancedBusinessData, html: str, url: str) -> None:
        """Detect mobile app availability."""
        # Android app
        if "play.google.com" in html or "android" in html and "app" in html:
            data.has_android_app = True
            match = re.search(r'play\.google\.com/store/apps/details\?id=([^\s"&]+)', html)
            if match:
                data.android_app_url = f"https://play.google.com/store/apps/details?id={match.group(1)}"

        # iOS app
        if "apps.apple.com" in html or "itunes.apple.com" in html:
            data.has_ios_app = True
            match = re.search(r'apps\.apple\.com/[^"]+/id(\d+)', html)
            if match:
                data.ios_app_url = f"https://apps.apple.com/app/id{match.group(1)}"

    def _detect_ratings(self, data: EnhancedBusinessData, html: str) -> None:
        """Detect customer ratings from various platforms."""
        # Google rating
        google_pattern = r'(\d\.?\d?)\s*(?:out of 5|/5|stars?|rating)'
        match = re.search(google_pattern, html)
        if match:
            try:
                rating = float(match.group(1))
                if 1.0 <= rating <= 5.0:
                    data.google_rating = rating
            except ValueError:
                pass

        # Reviews count
        review_pattern = r'(\d[\d,]*)\s*(?:reviews?|ratings?|feedback)'
        match = re.search(review_pattern, html)
        if match:
            try:
                count = int(match.group(1).replace(",", ""))
                data.google_reviews_count = count
            except ValueError:
                pass

        # Justdial rating
        if "justdial" in html:
            match = re.search(r'(\d\.?\d?)\s*/\s*5', html)
            if match:
                try:
                    data.justdial_rating = float(match.group(1))
                except ValueError:
                    pass

    def _detect_payment_methods(self, data: EnhancedBusinessData, html: str) -> None:
        """Detect accepted payment methods."""
        payment_keywords = {
            "upi": ["upi", "gpay", "google pay", "phonepe", "paytm", "bhim", "upi payment", "upi id", "qr code", "scan to pay"],
            "card": ["credit card", "debit card", "visa", "mastercard", "rupay", "amex", "american express", "diners"],
            "cash": ["cash", "cash on delivery", "cod", "cash payment", "pay cash"],
            "netbanking": ["net banking", "netbanking", "online transfer", "neft", "imps", "rtgs", "bank transfer", "online payment"],
            "wallet": ["wallet", "olamoney", "mobikwik", "freecharge", "airtel money", "jio money", "amazon pay"],
            "emi": ["emi", "easy installments", "monthly payment", "no cost emi", "zero emi", "bajaj finserv", "credit card emi"],
        }

        for method, keywords in payment_keywords.items():
            for keyword in keywords:
                if keyword in html:
                    data.payment_methods.append(method)
                    if method == "upi":
                        data.accepts_upi = True
                    elif method == "card":
                        data.accepts_card = True
                    elif method == "cash":
                        data.accepts_cash = True
                    elif method == "netbanking":
                        data.accepts_netbanking = True
                    break

    def _detect_service_features(self, data: EnhancedBusinessData, html: str) -> None:
        """Detect service features and policies."""
        features = {
            "has_verified_professionals": ["verified", "trained", "certified professionals", "verified professional", "trained professional", "bgv verified", "police verified", "background verified"],
            "has_background_check": ["background check", "police verified", "bgv", "background verification", "character verification", "antecedent verification"],
            "offers_guarantee": ["guarantee", "warranty", "assurance", "satisfaction guarantee", "quality guarantee", "service guarantee", "money back guarantee", "no questions asked"],
            "has_24_7_support": ["24/7", "24x7", "round the clock", "24 hours", "24 hours support", "24/7 support", "anytime support", "emergency support"],
            "has_online_booking": ["book online", "online booking", "book now", "schedule online", "instant booking", "one click booking", "whatsapp booking", "app booking"],
            "offers_emi": ["emi", "easy installments", "monthly payment", "no cost emi", "zero emi", "installment payment", "easy payment"],
            "offers_insurance": ["insurance", "insured", "coverage", "insured service", "service insurance", "damage protection", "accidental damage"],
            "has_walk_in": ["walk-in", "walk in", "store visit", "visit us", "showroom", "experience center", "service center", "branch"],
            "offers_free_quotes": ["free quote", "free estimate", "free inspection", "free assessment", "free consultation", "free survey", "no obligation quote"],
            "has_price_match": ["price match", "best price", "lowest price", "price guarantee", "price match guarantee", "beat any price", "cheapest price"],
        }

        for field_name, keywords in features.items():
            for keyword in keywords:
                if keyword in html:
                    setattr(data, field_name, True)
                    break

    def _detect_business_hours(self, data: EnhancedBusinessData, html: str) -> None:
        """Detect business hours and availability."""
        # 24/7 detection
        if "24/7" in html or "24x7" in html or "24 hours" in html or "24 ghante" in html or "din rat" in html or "subah se sham" in html:
            data.business_hours = "24/7"
            data.offers_weekend_service = True
            data.offers_emergency_service = True
        else:
            # Try to extract hours
            hours_pattern = r'(\d{1,2})\s*(?:am|pm|baje|bajkar)\s*(?:to|-|se)\s*(\d{1,2})\s*(?:am|pm|baje|tak)'
            match = re.search(hours_pattern, html.lower())
            if match:
                data.business_hours = f"{match.group(1)} - {match.group(2)}"

        # Weekend service
        if "weekend" in html or "saturday" in html or "sunday" in html or "saturday sunday" in html or "weekend service" in html or "holiday service" in html or "chhutti" in html:
            data.offers_weekend_service = True

        # Emergency service
        if "emergency" in html or "urgent" in html or "same day" in html or "emergency service" in html or "urgent service" in html or "emergency repair" in html or "urgent repair" in html:
            data.offers_emergency_service = True
            data.same_day_service = True

    def _detect_pricing_signals(self, data: EnhancedBusinessData, html: str) -> None:
        """Detect pricing transparency and offers."""
        if "transparent pricing" in html or "no hidden charges" in html or "no hidden cost" in html or "fixed price" in html or "price transparency" in html or "no surprise" in html or "what you see is what you pay" in html:
            data.has_transparent_pricing = True

        if "free quote" in html or "free estimate" in html or "free inspection" in html or "free assessment" in html or "free consultation" in html or "free survey" in html or "no obligation" in html:
            data.offers_free_quotes = True

        if "price match" in html or "best price" in html or "lowest price" in html or "price guarantee" in html or "beat any price" in html or "cheapest price" in html or "price match guarantee" in html:
            data.has_price_match = True

    def _detect_trust_signals(self, data: EnhancedBusinessData, html: str) -> None:
        """Detect trust and credibility signals."""
        # Years in business
        years_pattern = r'(\d+)\s*(?:years?|yrs?|saal|varsh)\s*(?:of\s+)?(?:experience|service|in business|ka anubhav|ka experience)'
        match = re.search(years_pattern, html)
        if match:
            try:
                data.years_in_business = int(match.group(1))
            except ValueError:
                pass

        # Certifications
        if "certified" in html or "iso" in html or "accredited" in html or "approved" in html or "certified by" in html or "authorized" in html:
            data.has_certifications = True

        # Insurance
        if "insured" in html or "insurance" in html or "insured service" in html or "service insurance" in html:
            data.has_insurance = True

        # License
        if "licensed" in html or "license" in html or "registration" in html or "registered" in html or "gst registered" in html or "gst number" in html or "gstin" in html:
            data.has_license = True

        # Professional associations (Indian associations)
        associations = [
            "nasci", "bcci", "iaop", "cleaning association",
            "cama", "naredco", "crepai", "ibha", "ficci", "cii", "phd chamber",
            "indian plumbing association", "electrical contractors association",
            "painting contractors association", "cleaning services association",
            "home services association", "facility management association",
        ]
        for assoc in associations:
            if assoc in html:
                data.member_of_associations.append(assoc)

    def _detect_social_proof(self, data: EnhancedBusinessData, html: str) -> None:
        """Detect social proof elements."""
        if "testimonial" in html or "what our customers" in html or "client says" in html or "customer review" in html or "customer feedback" in html or "happy customers" in html or "satisfied customers" in html or "hamare grahak" in html:
            data.has_testimonials = True

        if "case study" in html or "success story" in html or "project showcase" in html or "portfolio" in html or "our projects" in html or "completed projects" in html:
            data.has_case_studies = True

        if "portfolio" in html or "our work" in html or "gallery" in html or "photo gallery" in html or "work gallery" in html or "project gallery" in html or "before after" in html or "before and after" in html:
            data.has_portfolio = True

        # Social media followers (rough detection)
        follower_pattern = r'(\d[\d,.]*k?)\s*(?:followers?|fans?|subscribers?|members?)'
        match = re.search(follower_pattern, html)
        if match:
            try:
                count_str = match.group(1).lower().replace(",", "")
                if "k" in count_str:
                    data.social_media_followers = int(float(count_str.replace("k", "")) * 1000)
                elif "m" in count_str or "lakh" in count_str or "lac" in count_str:
                    data.social_media_followers = int(float(count_str.replace("m", "").replace("lakh", "").replace("lac", "")) * 100000)
                else:
                    data.social_media_followers = int(count_str)
            except ValueError:
                pass

    def _detect_response_metrics(self, data: EnhancedBusinessData, html: str) -> None:
        """Detect response time and service speed."""
        # Same day service
        if "same day" in html or "within 24 hours" in html or "aaj hi" in html or "isi din" in html or "turant" in html or "instant" in html:
            data.same_day_service = True
            data.response_time_hours = 24

        # Next day service
        if "next day" in html or "within 48 hours" in html or "agle din" in html or "kal hi" in html:
            data.next_day_service = True
            if not data.response_time_hours:
                data.response_time_hours = 48

        # Quick response
        if "quick response" in html or "instant response" in html or "fast response" in html or "immediate response" in html or "tat" in html or "turnaround time" in html:
            data.response_time_hours = 2

        # Emergency service
        if "emergency" in html or "urgent" in html or "emergency service" in html or "urgent service" in html or "emergency repair" in html or "urgent repair" in html:
            data.offers_emergency_service = True
            data.same_day_service = True

    def to_dict(self, data: EnhancedBusinessData) -> dict:
        """Convert to dictionary for storage."""
        return {
            "has_android_app": data.has_android_app,
            "has_ios_app": data.has_ios_app,
            "android_app_url": data.android_app_url,
            "ios_app_url": data.ios_app_url,
            "google_rating": data.google_rating,
            "google_reviews_count": data.google_reviews_count,
            "justdial_rating": data.justdial_rating,
            "justdial_reviews_count": data.justdial_reviews_count,
            "sulekha_rating": data.sulekha_rating,
            "payment_methods": data.payment_methods,
            "accepts_upi": data.accepts_upi,
            "accepts_card": data.accepts_card,
            "accepts_cash": data.accepts_cash,
            "accepts_netbanking": data.accepts_netbanking,
            "offers_emi": data.offers_emi,
            "offers_insurance": data.offers_insurance,
            "has_verified_professionals": data.has_verified_professionals,
            "has_background_check": data.has_background_check,
            "offers_guarantee": data.offers_guarantee,
            "has_24_7_support": data.has_24_7_support,
            "has_online_booking": data.has_online_booking,
            "business_hours": data.business_hours,
            "offers_weekend_service": data.offers_weekend_service,
            "offers_emergency_service": data.offers_emergency_service,
            "has_transparent_pricing": data.has_transparent_pricing,
            "offers_free_quotes": data.offers_free_quotes,
            "years_in_business": data.years_in_business,
            "has_certifications": data.has_certifications,
            "has_insurance": data.has_insurance,
            "has_license": data.has_license,
            "member_of_associations": data.member_of_associations,
            "has_testimonials": data.has_testimonials,
            "has_case_studies": data.has_case_studies,
            "has_portfolio": data.has_portfolio,
            "social_media_followers": data.social_media_followers,
            "response_time_hours": data.response_time_hours,
            "same_day_service": data.same_day_service,
            "next_day_service": data.next_day_service,
        }


enhanced_data_collector = EnhancedDataCollector()
