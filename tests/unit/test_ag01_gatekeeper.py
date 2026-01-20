from __future__ import annotations

from src.validator.contract_validator import load_step_contracts, validate_ag01_output


def _base_ag01_output() -> dict:
    return {
        "step_meta": {"step_id": "AG-01", "agent_name": "ag01_source_registry"},
        "source_registry": {
            "primary_sources": [
                {
                    "publisher": "Example Inc.",
                    "url": "https://example.com/about",
                    "type": "company_website",
                }
            ],
            "secondary_sources": [
                {
                    "publisher": "Registry of Companies",
                    "url": "https://registry.example.com/example-inc",
                    "type": "registry",
                }
            ],
            "source_scope_notes": "Primary sources cover official company properties; secondary sources corroborate.",
        },
        "findings": [
            {
                "summary": "Source registry assembled",
                "notes": ["No factual company assertions are made; sources are recommended verification targets."],
            }
        ],
        "sources": [],
    }


def test_ag01_gatekeeper_passes_valid_output() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-01"]
    output = _base_ag01_output()

    vr = validate_ag01_output(output, contract)

    assert vr.ok is True
    assert vr.errors == []


def test_ag01_gatekeeper_fails_empty_primary_sources() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-01"]
    output = _base_ag01_output()
    output["source_registry"]["primary_sources"] = []

    vr = validate_ag01_output(output, contract)

    assert vr.ok is False
    assert len(vr.errors) >= 1


def test_ag01_gatekeeper_fails_missing_publisher_or_url() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-01"]
    output = _base_ag01_output()
    output["source_registry"]["primary_sources"] = [{"publisher": "", "url": "https://example.com/about"}]

    vr = validate_ag01_output(output, contract)

    assert vr.ok is False
    assert len(vr.errors) >= 1


def test_ag01_gatekeeper_fails_findings_with_claims() -> None:
    contract = load_step_contracts("configs/pipeline/step_contracts.yml")["AG-01"]
    output = _base_ag01_output()
    output["findings"] = [{"summary": "The company was founded in 2020.", "notes": []}]

    vr = validate_ag01_output(output, contract)

    assert vr.ok is False
    assert len(vr.errors) >= 1