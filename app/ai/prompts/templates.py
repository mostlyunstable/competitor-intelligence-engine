"""Prompt templates for AI competitor analysis."""

PROMPT_TEMPLATES = {
    "competitor_analysis": {
        "id": "competitor_analysis",
        "version": "3.0.0",
        "purpose": "Comprehensive competitor intelligence analysis",
        "required_variables": ["competitor_name", "competitor_url", "services", "pricing", "content", "social", "extracted_data", "data_summary"],
        "template": """You are a senior business intelligence analyst specializing in home warranty and home services companies.

Analyze the following competitor data and produce a structured intelligence report.

## Competitor: {{competitor_name}}
## Website: {{competitor_url}}
## Data Quality: {{data_summary}}

## Services Offered
{{services}}

## Pricing Data
{{pricing}}

## Content & Marketing
{{content}}

## Social Media Presence
{{social}}

## Extracted Website Data
{{extracted_data}}

---

Based on this data, produce a JSON object with these exact fields:

{{
  "summary": "A 2-3 sentence executive summary of this competitor's positioning and strategy",
  "key_differentiators": ["List 3-5 things that make this competitor unique or strong"],
  "market_position": "One paragraph describing where they sit in the market relative to competitors",
  "confidence_score": 0.75,
  "pricing_analysis": {{
    "overview": "Summary of their pricing strategy",
    "price_range": "Typical price range observed",
    "positioning": "budget/mid-range/premium"
  }},
  "feature_gaps": ["List 2-4 areas where this competitor is weak or missing features"],
  "strategic_moves": ["List 2-3 recent strategic initiatives or changes you can infer"],
  "recommendations": ["List 3-5 actionable recommendations for competing against them"],
  "latest_updates": ["List 2-3 notable recent changes on their website or offerings"]
}}

CONFIDENCE SCORE CALIBRATION (CRITICAL):
The confidence_score MUST reflect how much data you actually have. Use these guidelines:
- 0.9-1.0: Comprehensive data across ALL categories (15+ services, 10+ pricing, 8+ content, 4+ social)
- 0.7-0.9: Good data in most categories but gaps in 1-2 areas
- 0.5-0.7: Moderate data, significant gaps in multiple categories
- 0.3-0.5: Limited data, only 1-2 categories with meaningful information
- 0.1-0.3: Very sparse data, mostly guesses based on minimal signals
- Do NOT default to 0.85. Calibrate based on the actual data provided.

IMPORTANT:
- Return ONLY valid JSON, no markdown or explanation
- confidence_score must be between 0.0 and 1.0
- All list fields must have at least 2 items
- Do not fabricate information not present in the data""",
    },
}

DEFAULT_TEMPLATE_ID = "competitor_analysis"
