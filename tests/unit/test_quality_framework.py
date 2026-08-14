from app.services.quality.quality_framework import data_quality_framework


def test_quality_framework_valid_record():
    obs = {
        "original_service_name": "AC Split Unit Servicing & Deep Clean",
        "price": 599.0,
        "currency": "INR",
        "competitor_id": 1,
        "location": "Chennai",
        "pricing_unit": "per_unit",
        "confidence_score": 0.95,
    }
    report = data_quality_framework.evaluate(obs)
    assert report.overall_quality_score >= 0.80
    assert report.is_ml_ready is True
    assert report.completeness == 1.0


def test_quality_framework_invalid_record():
    obs = {
        "original_service_name": "AC",
        "price": 0.0,
        "currency": "INR",
    }
    report = data_quality_framework.evaluate(obs)
    assert report.is_ml_ready is False
    assert len(report.quality_flags) > 0
