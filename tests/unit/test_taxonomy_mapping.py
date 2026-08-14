from app.services.taxonomy.taxonomy_engine import taxonomy_engine


def test_taxonomy_exact_match():
    res = taxonomy_engine.map_service("AC Split Unit Servicing & Deep Clean")
    assert res.canonical_service_name == "AC Split Unit Servicing & Deep Clean"
    assert res.similarity_score == 1.0
    assert res.matching_methodology == "exact_match"


def test_taxonomy_fuzzy_match():
    res = taxonomy_engine.map_service("Split AC Servicing Deep Clean")
    assert res.canonical_service_name == "AC Split Unit Servicing & Deep Clean"
    assert res.similarity_score >= 0.60
    assert res.mapping_confidence >= 0.50
