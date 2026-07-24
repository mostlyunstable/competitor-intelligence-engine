import datetime

from pydantic import BaseModel, Field


class PricingAnalysis(BaseModel):
    summary: str = Field(..., description="Summary of the pricing strategy")
    price_points: list[str] = Field(default_factory=list, description="Extracted price points")
    tier_names: list[str] = Field(default_factory=list, description="Names of pricing tiers")


class ServiceComparison(BaseModel):
    summary: str = Field(..., description="Summary of services offered compared to market")
    unique_services: list[str] = Field(default_factory=list, description="Services unique to this competitor")
    missing_services: list[str] = Field(default_factory=list, description="Standard market services they are missing")


class AIInsightResponse(BaseModel):
    """
    The strict JSON schema that all LLM providers must return.
    """
    summary: str = Field(..., description="A high-level summary of the competitor")
    pricing_analysis: PricingAnalysis = Field(..., description="Analysis of their pricing")
    service_comparison: ServiceComparison = Field(..., description="Comparison of their services")
    strengths: list[str] = Field(default_factory=list, description="List of key strengths")
    weaknesses: list[str] = Field(default_factory=list, description="List of key weaknesses")
    recommendations: list[str] = Field(default_factory=list, description="Strategic recommendations to counter them")
    executive_summary: str = Field(..., description="A short paragraph suitable for an executive briefing")
    market_position: str = Field(..., description="Description of their position in the market")
    latest_updates: list[str] = Field(default_factory=list, description="Recent changes or updates detected")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence score between 0.0 and 1.0")
    generated_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat(), description="ISO format timestamp of generation")


class PromptTemplate(BaseModel):
    """
    Represents a versioned prompt template.
    """
    id: str = Field(..., description="Unique identifier for this prompt")
    version: str = Field(..., description="Semantic version string")
    purpose: str = Field(..., description="What this prompt is used for")
    template: str = Field(..., description="The actual prompt text with {{ variables }}")
    required_variables: list[str] = Field(default_factory=list, description="List of variables that must be provided")

    def format(self, **kwargs) -> str:  # type: ignore
        """Formats the template with the provided variables."""
        missing = [var for var in self.required_variables if var not in kwargs]
        if missing:
            raise ValueError(f"Missing required variables for prompt {self.id}: {missing}")

        text = self.template
        for key, value in kwargs.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text
