from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import yaml

from src.agents.common.text_normalization import is_valid_domain
from src.validator import error_codes


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str
    path: str


@dataclass(frozen=True)
class ValidatorResult:
    ok: bool
    step_id: str
    errors: List[ValidationError]


def load_step_contracts(step_contracts_path: str) -> Dict[str, Any]:
    with open(step_contracts_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data.get("steps", [])
    return {s["step_id"]: s for s in steps}


def validate_ag00_output(output: Dict[str, Any], contract: Dict[str, Any]) -> ValidatorResult:
    step_id = contract["step_id"]
    errors: List[ValidationError] = []

    # Required sections
    required_sections = contract["outputs"]["required_sections"]
    for section in required_sections:
        if section not in output:
            errors.append(
                ValidationError(
                    code=error_codes.MISSING_REQUIRED_SECTIONS,
                    message=f"Missing required section: {section}",
                    path=f"$.{section}",
                )
            )

    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors)

    # Required fields in case_normalized
    cn = output.get("case_normalized", {})
    for field in contract["outputs"]["case_normalized_required_fields"]:
        if not cn.get(field):
            errors.append(
                ValidationError(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"Missing required case_normalized field: {field}",
                    path=f"$.case_normalized.{field}",
                )
            )

    # Required fields in target_entity_stub
    stub = output.get("target_entity_stub", {})
    for field in contract["outputs"]["target_entity_stub_required_fields"]:
        if not stub.get(field):
            errors.append(
                ValidationError(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"Missing required target_entity_stub field: {field}",
                    path=f"$.target_entity_stub.{field}",
                )
            )

    # Domain validation
    domain = cn.get("web_domain_normalized", "")
    if domain and not is_valid_domain(domain):
        errors.append(
            ValidationError(
                code=error_codes.INVALID_DOMAIN_FORMAT,
                message=f"Invalid domain format: {domain}",
                path="$.case_normalized.web_domain_normalized",
            )
        )

    # Entity key must be derived from domain
    expected_entity_key = f"domain:{domain}" if domain else ""
    actual_entity_key = cn.get("entity_key", "")
    if expected_entity_key and actual_entity_key != expected_entity_key:
        errors.append(
            ValidationError(
                code=error_codes.INVALID_ENTITY_KEY,
                message=f"entity_key must be '{expected_entity_key}'",
                path="$.case_normalized.entity_key",
            )
        )

    return ValidatorResult(ok=(len(errors) == 0), step_id=step_id, errors=errors)
