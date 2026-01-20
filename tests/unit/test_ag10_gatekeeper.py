from __future__ import annotations

from src.validator.contract_validator import load_step_contracts, validate_ag10_output


def _base_ag10_output() -> dict:
    return {
        "step_meta": {"step_id": "AG-10", "agent_name": "ag10_identity_legal"},
        "entities_delta": [
            {
                "entity_id": "TGT-001",
                "entity_type": "target_company",
                "entity_name": "Liquisto Technologies GmbH",
                "domain": "liquisto.com",
                "entity_key": "domain:liquisto.com",
                "legal_name": "Liquisto Technologies GmbH",
                "legal_form": "GmbH",
                "founding_year": "n/v",
                "registration_signals": "n/v",
            }
        ],
        "relations_delta": [],
        "findings": [{"summary": "Identity and legal signals extracted", "notes": []}],
        "sources": [
            {
                "publisher": "Liquisto Technologies GmbH",
                "url": "https://liquisto.com/impressum",
                "accessed_at_utc": "2026-01-20T00:00:00Z",
            }
        ],
    }


def test_ag10_gatekeeper_passes_valid_output() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-10"]
    output = _base_ag10_output()

    vr = validate_ag10_output(
        output,
        contract,
        expected_entity_key="domain:liquisto.com",
        expected_domain="liquisto.com",
    )

    assert vr.ok is True
    assert vr.errors == []

def test_ag10_gatekeeper_fails_invalid_registration_signals() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-10"]
    output = _base_ag10_output()
    output["entities_delta"][0]["registration_signals"] = "123456"

    vr = validate_ag10_output(output, contract, expected_entity_key="domain:liquisto.com", expected_domain="liquisto.com")

    assert vr.ok is False
    assert len(vr.errors) >= 1


def test_ag10_gatekeeper_warns_all_nv_fields() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-10"]
    output = _base_ag10_output()
    tgt = output["entities_delta"][0]
    tgt["legal_name"] = "n/v"
    tgt["legal_form"] = "n/v"
    tgt["founding_year"] = "n/v"
    tgt["registration_signals"] = "n/v"
    output["sources"] = []

    vr = validate_ag10_output(output, contract, expected_entity_key="domain:liquisto.com", expected_domain="liquisto.com")

    assert vr.ok is True
    assert vr.errors == []
    assert len(vr.warnings) >= 1


def test_ag10_gatekeeper_fails_missing_sources_for_claims() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-10"]
    output = _base_ag10_output()
    output["sources"] = []

    vr = validate_ag10_output(output, contract, expected_entity_key="domain:liquisto.com", expected_domain="liquisto.com")

    assert vr.ok is False
    assert len(vr.errors) >= 1


def test_ag10_gatekeeper_fails_invalid_founding_year() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-10"]
    output = _base_ag10_output()
    output["entities_delta"][0]["founding_year"] = 2500

    vr = validate_ag10_output(output, contract, expected_entity_key="domain:liquisto.com", expected_domain="liquisto.com")

    assert vr.ok is False
    assert len(vr.errors) >= 1


def test_ag10_gatekeeper_fails_missing_target_entity() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-10"]
    output = _base_ag10_output()
    output["entities_delta"] = []

    vr = validate_ag10_output(output, contract, expected_entity_key="domain:liquisto.com", expected_domain="liquisto.com")

    assert vr.ok is False
    assert len(vr.errors) >= 1
