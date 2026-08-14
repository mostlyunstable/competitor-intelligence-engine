import re
from typing import Any


def normalize_string(s: str) -> str:
    """Normalize string for robust matching without fuzzy false positives."""
    if not s:
        return ""
    # Lowercase, replace non-alphanumeric (like hyphens, underscores, extra spaces) with a single space
    s = s.lower()
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return s.strip()

def compare_services(services_a: list[dict[str, Any]], services_b: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Determine shared, A-only, and B-only services based on normalized names."""

    # Create mapping of normalized name -> original name
    map_a = {normalize_string(s.get("name", "")): s.get("name", "") for s in services_a if s.get("name")}
    map_b = {normalize_string(s.get("name", "")): s.get("name", "") for s in services_b if s.get("name")}

    norm_a = set(map_a.keys())
    norm_b = set(map_b.keys())

    shared_norm = norm_a.intersection(norm_b)
    a_only_norm = norm_a - norm_b
    b_only_norm = norm_b - norm_a

    # Use A's original name for shared services as convention
    return {
        "shared_services": sorted([map_a[n] for n in shared_norm]),
        "a_only_services": sorted([map_a[n] for n in a_only_norm]),
        "b_only_services": sorted([map_b[n] for n in b_only_norm]),
    }

def compare_locations(locations_a: list[dict[str, Any]], locations_b: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Determine shared, A-only, and B-only locations."""

    map_a = {normalize_string(loc.get("name", "")): loc.get("name", "") for loc in locations_a if loc.get("name")}
    map_b = {normalize_string(loc.get("name", "")): loc.get("name", "") for loc in locations_b if loc.get("name")}

    norm_a = set(map_a.keys())
    norm_b = set(map_b.keys())

    shared_norm = norm_a.intersection(norm_b)
    a_only_norm = norm_a - norm_b
    b_only_norm = norm_b - norm_a

    return {
        "shared_locations": sorted([map_a[n] for n in shared_norm]),
        "a_only_locations": sorted([map_a[n] for n in a_only_norm]),
        "b_only_locations": sorted([map_b[n] for n in b_only_norm]),
    }

def compare_pricing(
    pricing_a: list[dict[str, Any]],
    pricing_b: list[dict[str, Any]],
    shared_services: list[str]
) -> list[dict[str, Any]]:
    """Compare pricing for shared services mathematically."""

    # Normalize shared services for lookup
    shared_norm = {normalize_string(s) for s in shared_services}

    # Build lookup tables for pricing
    map_a = {}
    for p in pricing_a:
        norm = normalize_string(p.get("service") or p.get("name") or "")
        if norm in shared_norm:
            map_a[norm] = p

    map_b = {}
    for p in pricing_b:
        norm = normalize_string(p.get("service") or p.get("name") or "")
        if norm in shared_norm:
            map_b[norm] = p

    results = []

    for norm in sorted(shared_norm):
        p_a = map_a.get(norm)
        p_b = map_b.get(norm)

        # Determine the original service name using one of the available
        service_name = (p_a.get("service") or p_a.get("name")) if p_a else ((p_b.get("service") or p_b.get("name")) if p_b else norm)

        price_a = (p_a.get("price") if p_a and p_a.get("price") is not None else (p_a.get("base_price") if p_a else None))
        price_b = (p_b.get("price") if p_b and p_b.get("price") is not None else (p_b.get("base_price") if p_b else None))
        curr_a = (p_a.get("currency") or "INR").strip().upper() if p_a else "INR"
        curr_b = (p_b.get("currency") or "INR").strip().upper() if p_b else "INR"

        comp = {
            "service": service_name,
            "price_a": price_a,
            "price_b": price_b,
            "currency_a": curr_a,
            "currency_b": curr_b,
            "absolute_difference": None,
            "percentage_difference": None,
            "comparison_status": "comparable",
            "reason": None
        }

        # Validation rules
        if not p_a or not p_b:
            comp["comparison_status"] = "not_comparable"
            comp["reason"] = "Pricing missing for one or both competitors"
            results.append(comp)
            continue

        if comp["price_a"] is None or comp["price_b"] is None:
            comp["comparison_status"] = "not_comparable"
            comp["reason"] = "Price value is null"
            results.append(comp)
            continue

        if comp["currency_a"] != comp["currency_b"]:
            comp["comparison_status"] = "not_comparable"
            comp["reason"] = f"Currency mismatch ({comp['currency_a']} vs {comp['currency_b']})"
            results.append(comp)
            continue

        try:
            val_a = float(comp["price_a"])
            val_b = float(comp["price_b"])
        except (ValueError, TypeError):
            comp["comparison_status"] = "not_comparable"
            comp["reason"] = "Price is not a valid number"
            results.append(comp)
            continue

        if val_a < 0 or val_b < 0:
            comp["comparison_status"] = "not_comparable"
            comp["reason"] = "Price cannot be negative"
            results.append(comp)
            continue

        # Calculation (Difference relative to A)
        diff = val_b - val_a
        comp["absolute_difference"] = round(diff, 2)

        if val_a == 0 and val_b == 0:
            comp["percentage_difference"] = 0.0
        elif val_a == 0:
            comp["comparison_status"] = "not_comparable"
            comp["reason"] = "Division by zero (Competitor A price is 0)"
        else:
            comp["percentage_difference"] = round((diff / val_a) * 100, 2)

        results.append(comp)

    return results

def generate_deterministic_comparison(comp_a_data: dict[str, Any], comp_b_data: dict[str, Any]) -> dict[str, Any]:
    """Generates the full deterministic comparison object."""

    srv_comp = compare_services(comp_a_data.get("services", []), comp_b_data.get("services", []))

    loc_a = comp_a_data.get("extracted", {}).get("locations", [])
    loc_b = comp_b_data.get("extracted", {}).get("locations", [])
    loc_comp = compare_locations(loc_a, loc_b)

    pricing_comp = compare_pricing(comp_a_data.get("pricing", []), comp_b_data.get("pricing", []), srv_comp["shared_services"])

    return {
        "competitor_a": {
            "name": comp_a_data.get("name"),
            "url": comp_a_data.get("url")
        },
        "competitor_b": {
            "name": comp_b_data.get("name"),
            "url": comp_b_data.get("url")
        },
        "shared_services": srv_comp["shared_services"],
        "a_only_services": srv_comp["a_only_services"],
        "b_only_services": srv_comp["b_only_services"],
        "shared_locations": loc_comp["shared_locations"],
        "a_only_locations": loc_comp["a_only_locations"],
        "b_only_locations": loc_comp["b_only_locations"],
        "pricing_comparison": pricing_comp,
    }
