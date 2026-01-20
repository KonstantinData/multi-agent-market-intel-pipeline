from __future__ import annotations

from src.validator.contract_validator import load_step_contracts, validate_ag00_output


def _step_meta() -> dict:
    return {
        "step_id": "AG-00",
        "agent_name": "ag00_intake_normalization",
        "run_id": "run-0001",
        "started_at_utc": "2024-01-01T00:00:00Z",
        "finished_at_utc": "2024-01-01T00:00:01Z",
        "pipeline_version": "git:abc123",
    }


def test_ag00_gatekeeper_passes_valid_output() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-00"]

    output = {
        "step_meta": _step_meta(),
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
    assert isinstance(vr.warnings, list)


def test_ag00_gatekeeper_warns_low_quality_company_name() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-00"]

    output = {
        "step_meta": _step_meta(),
        "case_normalized": {
            "company_name_canonical": "condata",
            "web_domain_normalized": "condata.io",
            "entity_key": "domain:condata.io",
            "domain_valid": True,
        },
        "target_entity_stub": {
            "entity_type": "target_company",
            "entity_name": "condata",
            "domain": "condata.io",
            "entity_key": "domain:condata.io",
        },
        "entities_delta": [],
        "relations_delta": [],
        "findings": [{"summary": "Intake normalized", "notes": []}],
        "sources": [],
    }

    vr = validate_ag00_output(output, contract)
    assert vr.ok is True
    assert vr.errors == []
    assert len(vr.warnings) >= 1


def test_ag00_gatekeeper_fails_invalid_domain() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-00"]

    output = {
        "step_meta": _step_meta(),
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


def test_ag00_gatekeeper_fails_missing_step_meta_field() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-00"]
    output = {
        "step_meta": _step_meta(),
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
    output["step_meta"].pop("run_id")

    vr = validate_ag00_output(output, contract)

    assert vr.ok is False
    assert len(vr.errors) >= 1
