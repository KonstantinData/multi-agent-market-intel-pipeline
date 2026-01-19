from __future__ import annotations

from src.validator.contract_validator import load_step_contracts, validate_ag00_output


def test_ag00_gatekeeper_passes_valid_output() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-00"]

    output = {
        "step_meta": {"step_id": "AG-00", "agent_name": "ag00_intake_normalization"},
        "case_normalized": {
            "company_name_canonical": "Liquisto Technologies GmbH",
            "web_domain_normalized": "liquisto.com",
            "entity_key": "domain:liquisto.com",
            "domain_valid": True,
        },
        "target_entity_stub": {
            "entity_type": "target_company",
            "entity_name": "Liquisto Technologies GmbH",
            "domain": "liquisto.com",
            "entity_key": "domain:liquisto.com",
        },
        "entities_delta": [],
        "relations_delta": [],
        "findings": [{"summary": "Intake normalized", "notes": []}],
        "sources": [],
    }

    vr = validate_ag00_output(output, contract)
    assert vr.ok is True
    assert vr.errors == []


def test_ag00_gatekeeper_fails_invalid_domain() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-00"]

    output = {
        "step_meta": {"step_id": "AG-00", "agent_name": "ag00_intake_normalization"},
        "case_normalized": {
            "company_name_canonical": "X",
            "web_domain_normalized": "not a domain",
            "entity_key": "domain:not a domain",
            "domain_valid": False,
        },
        "target_entity_stub": {
            "entity_type": "target_company",
            "entity_name": "X",
            "domain": "not a domain",
            "entity_key": "domain:not a domain",
        },
        "entities_delta": [],
        "relations_delta": [],
        "findings": [{"summary": "Intake normalized", "notes": []}],
        "sources": [],
    }

    vr = validate_ag00_output(output, contract)
    assert vr.ok is False
    assert len(vr.errors) >= 1
