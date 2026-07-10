from typing import Any

from app.parsers.strategy import FieldValue, ParsedResult


class EntityProfiler:
    def __init__(self) -> None:
        pass

    def extract_entities(self, result: ParsedResult) -> list[tuple[str, FieldValue]]:
        entities: list[tuple[str, FieldValue]] = []
        fielded = result._fielded

        # Scalars
        scalars = [
            "company_name",
            "description",
            "logo",
            "industry",
            "headquarters",
            "contact_email",
            "contact_phone",
        ]
        for s in scalars:
            val = getattr(fielded, s, None)
            if val:
                entities.append((s, val))

        # Social links
        for k, val in fielded.social_links.items():
            entities.append((f"social_{k}", val))

        # Lists
        lists = [
            "services",
            "pricing",
            "content",
            "social_profiles",
            "plans",
            "offers",
            "reviews",
            "features",
            "media",
            "locations",
            "team",
            "trust_signals",
            "assets",
        ]
        for lst in lists:
            vals = getattr(fielded, lst, [])
            for val in vals:
                entities.append((lst, val))

        return entities

    def profile_merge(
        self,
        strategy_name: str,
        partial: ParsedResult,
        pre_merge: ParsedResult,
        post_merge: ParsedResult,
        url: str,
    ) -> dict[str, Any]:
        partial_ents = self.extract_entities(partial)
        post_ents = self.extract_entities(post_merge)

        # We need to know which ones from partial_ents made it to post_ents.
        # FieldValue objects might be rebuilt, so we check by value and strategy.
        # But wait, in strategy.py, `FieldValue` objects are explicitly stored.
        # Let's collect all FieldValues in post_ents that have strategy_name == strategy_name.
        {id(fv) for _, fv in post_ents if fv.extraction_strategy == strategy_name}

        # Some FieldValues in partial are scalar, some are lists.
        # If partial has a FieldValue and it is NOT in post_merge (or equivalent), it was rejected.

        accepted_records = []
        rejected_records = []

        for e_type, fv in partial_ents:
            # Did this exact FieldValue make it into the post_merge?
            # We can check by checking if any FieldValue in post_ents matches its value and strategy.
            # (Because FieldValue object IDs might not be preserved if reconstructed, though they should be).
            # Actually, let's just check if there's a FieldValue in post_ents with the same strategy and value.
            # We must handle dicts gracefully.

            # For simplicity, convert the dict value to a string for comparison
            val_str = str(fv.value)

            is_accepted = False
            for pe_type, pfv in post_ents:
                if (
                    pe_type == e_type
                    and str(pfv.value) == val_str
                    and pfv.extraction_strategy == strategy_name
                ):
                    is_accepted = True
                    break

            record = {
                "Entity Type": e_type,
                "Entity Value": val_str[:100],  # Truncate for sanity
                "Source Strategy": strategy_name,
                "Confidence": fv.confidence,
                "Merged With": "existing" if not is_accepted else None,
                "Duplicate": not is_accepted,
                "Accepted": is_accepted,
                "Rejected": not is_accepted,
                "Storage Table": (
                    f"competitor_{e_type}" if not e_type.startswith("company") else "competitors"
                ),
                "Source URL": url,
                "Parser Pass": fv.pass_number,
            }
            if is_accepted:
                accepted_records.append(record)
            else:
                rejected_records.append(record)

        return {"accepted": accepted_records, "rejected": rejected_records}
