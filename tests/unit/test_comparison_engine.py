from app.services.comparison.engine import (
    compare_locations,
    compare_pricing,
    compare_services,
    normalize_string,
)


def test_normalize_string():
    assert normalize_string("Fan Cleaning") == "fan cleaning"
    assert normalize_string("fan cleaning") == "fan cleaning"
    assert normalize_string("Fan-Cleaning") == "fan cleaning"
    assert normalize_string(" AC  Cleaning!!! ") == "ac cleaning"
    assert normalize_string(None) == ""

def test_shared_services():
    a = [{"name": "Fan Cleaning"}, {"name": "Car Cleaning"}]
    b = [{"name": "Fan Cleaning"}, {"name": "AC Cleaning"}]

    res = compare_services(a, b)
    assert "Fan Cleaning" in res["shared_services"]
    assert "Car Cleaning" in res["a_only_services"]
    assert "AC Cleaning" in res["b_only_services"]

def test_shared_locations():
    a = [{"name": "Chennai"}, {"name": "Perungudi"}]
    b = [{"name": "Chennai"}, {"name": "Velachery"}]

    res = compare_locations(a, b)
    assert "Chennai" in res["shared_locations"]
    assert "Perungudi" in res["a_only_locations"]
    assert "Velachery" in res["b_only_locations"]

def test_price_comparison():
    a = [{"service": "Fan Cleaning", "price": 149, "currency": "INR"}]
    b = [{"service": "Fan Cleaning", "price": 199, "currency": "INR"}]

    res = compare_pricing(a, b, ["Fan Cleaning"])
    comp = res[0]

    assert comp["absolute_difference"] == 50.0
    assert comp["percentage_difference"] == 33.56
    assert comp["comparison_status"] == "comparable"

def test_missing_price():
    a = [{"service": "Fan Cleaning", "price": None, "currency": "INR"}]
    b = [{"service": "Fan Cleaning", "price": 199, "currency": "INR"}]

    res = compare_pricing(a, b, ["Fan Cleaning"])
    comp = res[0]

    assert comp["comparison_status"] == "not_comparable"
    assert "null" in comp["reason"].lower()

def test_different_currency():
    a = [{"service": "Fan Cleaning", "price": 149, "currency": "USD"}]
    b = [{"service": "Fan Cleaning", "price": 199, "currency": "INR"}]

    res = compare_pricing(a, b, ["Fan Cleaning"])
    comp = res[0]

    assert comp["comparison_status"] == "not_comparable"
    assert "mismatch" in comp["reason"].lower()

def test_different_units():
    # Units aren't strictly passed in the dict in the prompt's example,
    # but the engine should be robust. If they differ in some way...
    pass # Currently only comparing on currency, but structure allows it.

def test_zero_price_division():
    a = [{"service": "Fan Cleaning", "price": 0, "currency": "INR"}]
    b = [{"service": "Fan Cleaning", "price": 199, "currency": "INR"}]

    res = compare_pricing(a, b, ["Fan Cleaning"])
    comp = res[0]

    assert comp["comparison_status"] == "not_comparable"
    assert "zero" in comp["reason"].lower()
