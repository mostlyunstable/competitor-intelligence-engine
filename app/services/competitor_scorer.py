"""Competitor scoring system for Indian/Chennai market intelligence."""

from dataclasses import dataclass, field

import structlog

from app.services.location_validator import LocationInfo
from app.services.enhanced_data_collector import EnhancedBusinessData

logger = structlog.get_logger(__name__)


@dataclass
class CompetitorScore:
    """Comprehensive competitor score."""
    total_score: float = 0.0
    location_score: float = 0.0
    digital_presence_score: float = 0.0
    service_quality_score: float = 0.0
    trust_score: float = 0.0
    market_relevance_score: float = 0.0

    # Breakdown details
    location_breakdown: dict = field(default_factory=dict)
    digital_breakdown: dict = field(default_factory=dict)
    service_breakdown: dict = field(default_factory=dict)
    trust_breakdown: dict = field(default_factory=dict)
    market_breakdown: dict = field(default_factory=dict)

    # Grade
    grade: str = ""
    tier: str = ""  # Tier 1, Tier 2, Tier 3


class CompetitorScorer:
    """Scores competitors based on multiple dimensions."""

    # Weights for each dimension
    WEIGHTS = {
        "location": 0.25,
        "digital_presence": 0.20,
        "service_quality": 0.20,
        "trust": 0.20,
        "market_relevance": 0.15,
    }

    def score(
        self,
        location_info: LocationInfo,
        enhanced_data: EnhancedBusinessData,
        basic_data: dict,
        tags: list[str] = None,
    ) -> CompetitorScore:
        """Calculate comprehensive competitor score."""
        score = CompetitorScore()

        # Calculate individual dimension scores
        score.location_score, score.location_breakdown = self._score_location(location_info)
        score.digital_presence_score, score.digital_breakdown = self._score_digital_presence(enhanced_data, basic_data)
        score.service_quality_score, score.service_breakdown = self._score_service_quality(enhanced_data, basic_data)
        score.trust_score, score.trust_breakdown = self._score_trust(enhanced_data)
        score.market_relevance_score, score.market_breakdown = self._score_market_relevance(tags, basic_data)

        # Calculate total weighted score
        score.total_score = (
            score.location_score * self.WEIGHTS["location"]
            + score.digital_presence_score * self.WEIGHTS["digital_presence"]
            + score.service_quality_score * self.WEIGHTS["service_quality"]
            + score.trust_score * self.WEIGHTS["trust"]
            + score.market_relevance_score * self.WEIGHTS["market_relevance"]
        )

        # Assign grade and tier
        score.grade = self._calculate_grade(score.total_score)
        score.tier = self._calculate_tier(score)

        return score

    def _score_location(self, info: LocationInfo) -> tuple[float, dict]:
        """Score location relevance."""
        breakdown = {}
        score = 0.0

        if info.is_chennai:
            score += 50
            breakdown["chennai_based"] = 50
        elif info.is_indian:
            score += 30
            breakdown["indian_based"] = 30

        if info.state == "Tamil Nadu":
            score += 20
            breakdown["tamil_nadu"] = 20

        if info.domain_indian:
            score += 10
            breakdown["indian_domain"] = 10

        if info.phone_indian:
            score += 10
            breakdown["indian_phone"] = 10

        if info.city:
            score += 10
            breakdown["city_identified"] = 10

        return min(score, 100), breakdown

    def _score_digital_presence(self, data: EnhancedBusinessData, basic: dict) -> tuple[float, dict]:
        """Score digital presence strength."""
        breakdown = {}
        score = 0.0

        # Mobile apps
        if data.has_android_app:
            score += 15
            breakdown["android_app"] = 15
        if data.has_ios_app:
            score += 15
            breakdown["ios_app"] = 15

        # Online booking
        if data.has_online_booking:
            score += 20
            breakdown["online_booking"] = 20

        # Social media
        if data.social_media_followers > 0:
            if data.social_media_followers > 10000:
                score += 20
                breakdown["strong_social"] = 20
            elif data.social_media_followers > 1000:
                score += 10
                breakdown["moderate_social"] = 10
            else:
                score += 5
                breakdown["basic_social"] = 5

        # Ratings
        if data.google_rating > 0:
            score += 15
            breakdown["google_rating"] = 15
        if data.justdial_rating > 0:
            score += 10
            breakdown["justdial_rating"] = 10

        # Website presence
        if basic.get("website_url"):
            score += 10
            breakdown["website"] = 10

        return min(score, 100), breakdown

    def _score_service_quality(self, data: EnhancedBusinessData, basic: dict) -> tuple[float, dict]:
        """Score service quality indicators."""
        breakdown = {}
        score = 0.0

        # Verified professionals
        if data.has_verified_professionals:
            score += 25
            breakdown["verified_professionals"] = 25

        # Background check
        if data.has_background_check:
            score += 20
            breakdown["background_check"] = 20

        # Guarantee/warranty
        if data.offers_guarantee:
            score += 15
            breakdown["guarantee"] = 15

        # 24/7 support
        if data.has_24_7_support:
            score += 15
            breakdown["24_7_support"] = 15

        # Same day service
        if data.same_day_service:
            score += 10
            breakdown["same_day_service"] = 10

        # Transparent pricing
        if data.has_transparent_pricing:
            score += 10
            breakdown["transparent_pricing"] = 10

        # Free quotes
        if data.offers_free_quotes:
            score += 5
            breakdown["free_quotes"] = 5

        return min(score, 100), breakdown

    def _score_trust(self, data: EnhancedBusinessData) -> tuple[float, dict]:
        """Score trust and credibility."""
        breakdown = {}
        score = 0.0

        # Years in business
        if data.years_in_business >= 10:
            score += 25
            breakdown["established"] = 25
        elif data.years_in_business >= 5:
            score += 15
            breakdown["experienced"] = 15
        elif data.years_in_business >= 2:
            score += 10
            breakdown["growing"] = 10

        # Certifications
        if data.has_certifications:
            score += 20
            breakdown["certified"] = 20

        # Insurance
        if data.has_insurance:
            score += 15
            breakdown["insured"] = 15

        # License
        if data.has_license:
            score += 15
            breakdown["licensed"] = 15

        # Testimonials
        if data.has_testimonials:
            score += 10
            breakdown["testimonials"] = 10

        # Portfolio
        if data.has_portfolio:
            score += 10
            breakdown["portfolio"] = 10

        # Professional associations
        if data.member_of_associations:
            score += 5
            breakdown["associations"] = 5

        return min(score, 100), breakdown

    def _score_market_relevance(self, tags: list[str], basic: dict) -> tuple[float, dict]:
        """Score market relevance and positioning."""
        breakdown = {}
        score = 0.0

        if not tags:
            return score, breakdown

        tags_lower = [t.lower() for t in tags]

        # Tier classification
        if "tier-1" in tags_lower:
            score += 40
            breakdown["tier_1"] = 40
        elif "tier-2" in tags_lower:
            score += 25
            breakdown["tier_2"] = 25
        elif "tier-3" in tags_lower:
            score += 10
            breakdown["tier_3"] = 10

        # Market position
        if "market-leader" in tags_lower:
            score += 30
            breakdown["market_leader"] = 30
        elif "major-player" in tags_lower:
            score += 20
            breakdown["major_player"] = 20

        # Service categories
        service_tags = ["cleaning", "plumbing", "electrical", "appliance-repair", "pest-control"]
        for tag in service_tags:
            if tag in tags_lower:
                score += 5
                breakdown[f"service_{tag}"] = 5
                break  # Only count one service category

        # Regional relevance
        if "chennai" in tags_lower:
            score += 15
            breakdown["chennai_focus"] = 15
        elif "india" in tags_lower:
            score += 10
            breakdown["india_focus"] = 10

        return min(score, 100), breakdown

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        if score >= 80:
            return "A"
        elif score >= 60:
            return "B"
        elif score >= 40:
            return "C"
        elif score >= 20:
            return "D"
        return "F"

    def _calculate_tier(self, score: CompetitorScore) -> str:
        """Calculate competitor tier from scores."""
        if score.total_score >= 70:
            return "Tier 1"
        elif score.total_score >= 50:
            return "Tier 2"
        elif score.total_score >= 30:
            return "Tier 3"
        return "Tier 4"


competitor_scorer = CompetitorScorer()
