"""Domain entities for the AI module."""

from pydantic import BaseModel, Field


class AIInsightResponse(BaseModel):
    """
    Strict schema for LLM output. Maps 1:1 to CompetitorAIInsight DB columns.
    Every LLM response must conform to this schema before persistence.
    """

    summary: str = Field(..., min_length=1, description="High-level competitor summary")
    key_differentiators: list[str] = Field(default_factory=list, description="Key differentiators vs competitors")
    market_position: str = Field(..., min_length=1, description="Market position description")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    pricing_analysis: dict = Field(default_factory=dict, description="Pricing strategy analysis")
    feature_gaps: list[str] = Field(default_factory=list, description="Features they lack vs market")
    strategic_moves: list[str] = Field(default_factory=list, description="Recent strategic moves")
    recommendations: list[str] = Field(default_factory=list, description="Counter-strategy recommendations")
    latest_updates: list[str] = Field(default_factory=list, description="Recent changes detected")


class PromptTemplate(BaseModel):
    """Versioned prompt template with variable substitution."""

    id: str = Field(..., description="Unique template identifier")
    version: str = Field(..., description="Semantic version")
    purpose: str = Field(..., description="What this template analyzes")
    template: str = Field(..., description="Template text with {{ variable }} placeholders")
    required_variables: list[str] = Field(default_factory=list)

    def render(self, **kwargs: str) -> str:
        """Render template with provided variables. Raises if required vars missing."""
        missing = [v for v in self.required_variables if v not in kwargs]
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        text = self.template
        for key, value in kwargs.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text


class ProviderHealth(BaseModel):
    """Health check result from an LLM provider."""

    healthy: bool
    provider: str
    model: str
    latency_ms: float = 0.0
    error: str | None = None
