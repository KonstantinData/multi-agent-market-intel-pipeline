from __future__ import annotations

from src.registry.deduper import dedupe_entities


def test_dedupe_entities_collapses_by_domain_and_name() -> None:
    entities = [
        {
            "entity_type": "target_company",
            "entity_name": "Example Corp",
            "domain": "Example.com",
            "entity_key": "",
        },
        {
            "entity_type": "target_company",
            "entity_name": "Example Corp",
            "domain": "https://example.com/about",
            "entity_key": "n/v",
        },
        {
            "entity_type": "customer",
            "entity_name": "Beta Industries",
            "domain": "",
            "entity_key": "",
        },
        {
            "entity_type": "customer",
            "entity_name": "Beta Industries",
            "domain": None,
            "entity_key": "",
        },
    ]

    deduped = dedupe_entities(entities)

    assert len(deduped) == 2
    dedupe_keys = {entity["entity_key"] for entity in deduped}
    assert "domain:example.com" in dedupe_keys
    assert "name:beta industries" in dedupe_keys
