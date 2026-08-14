from app.services.pricing.utservio_auditor import utservio_auditor


def test_utservio_audit_catalog():
    report = utservio_auditor.audit_catalog()
    assert report.total_services_audited > 0
    assert report.total_discrepancies_found > 0
    assert len(report.canonical_catalog) > 0

    # Verify discrepancy structure
    disc = report.discrepancies[0]
    assert disc.discrepancy_type != ""
    assert disc.resolved_canonical_value["base_price"] > 0
    assert disc.confidence_score > 0.5
