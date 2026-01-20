from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List, Optional

import yaml

from src.agents.common.text_normalization import is_valid_domain
from src.validator import error_codes


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str


@dataclass(frozen=True)
class ValidatorResult:
    ok: bool
    step_id: str
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]


def load_step_contracts(step_contracts_path: str) -> Dict[str, Any]:
    with open(step_contracts_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    steps = data.get("steps", [])
    return {s["step_id"]: s for s in steps}


def _is_low_quality_company_name(name: str) -> bool:
    """
    Heuristic WARN rule (not FAIL):
    - single token
    - all lowercase
    Example: "condata"
    """
    if not name:
        return False
    n = name.strip()
    if " " in n:
        return False
    if n.lower() == n and len(n) >= 3:
        return True
    return False


def validate_ag00_output(output: Dict[str, Any], contract: Dict[str, Any]) -> ValidatorResult:
    step_id = contract["step_id"]
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    # Required sections
    required_sections = contract["outputs"]["required_sections"]
    for section in required_sections:
        if section not in output:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_SECTIONS,
                    message=f"Missing required section: {section}",
                    path=f"$.{section}",
                )
            )

    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    _validate_step_meta(output, contract, errors)
    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    # Required fields in case_normalized
    cn = output.get("case_normalized", {})
    for field in contract["outputs"]["case_normalized_required_fields"]:
        if not cn.get(field):
            errors.append(
                ValidationIssue(
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
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"Missing required target_entity_stub field: {field}",
                    path=f"$.target_entity_stub.{field}",
                )
            )

    # Domain validation
    domain = cn.get("web_domain_normalized", "")
    if domain and not is_valid_domain(domain):
        errors.append(
            ValidationIssue(
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
            ValidationIssue(
                code=error_codes.INVALID_ENTITY_KEY,
                message=f"entity_key must be '{expected_entity_key}'",
                path="$.case_normalized.entity_key",
            )
        )

    # Company name sanity (WARN, not FAIL)
    company_name = str(cn.get("company_name_canonical", "")).strip()
    if _is_low_quality_company_name(company_name):
        warnings.append(
            ValidationIssue(
                code=error_codes.LOW_QUALITY_COMPANY_NAME,
                message="Company name looks low-quality (single token, all lowercase). Consider correcting intake.",
                path="$.case_normalized.company_name_canonical",
            )
        )

    ok = len(errors) == 0
    return ValidatorResult(ok=ok, step_id=step_id, errors=errors, warnings=warnings)


def _is_http_url(url: str) -> bool:
    u = (url or "").strip()
    return u.startswith("http://") or u.startswith("https://")

_ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_PIPELINE_VERSION_RE = re.compile(
    r"^(?:[0-9a-f]{7,40}|\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?\+[0-9A-Za-z.-]+)$",
    re.IGNORECASE,
)
_CLAIM_KEYWORDS = re.compile(
    r"\b("
    r"founded|incorporated|headquartered|headquarters|based in|located in|"
    r"subsidiary|parent company|acquired|acquisition|merger|"
    r"revenue|employees|staff|workforce|"
    r"ceo|chief executive|founder|ownership|"
    r"manufactures|produces|provides|offers|operates"
    r")\b",
    re.IGNORECASE,
)


def _finding_contains_claim(text: str) -> bool:
    if not text:
        return False
    return _CLAIM_KEYWORDS.search(text) is not None


def _is_iso_utc(value: str) -> bool:
    return bool(_ISO_UTC_RE.match(value))


def _findings_signal_no_evidence(texts: List[str]) -> bool:
    if not texts:
        return False
    combined = " ".join(texts).lower()
    return (
        "no evidence" in combined
        or "no verifiable" in combined
        or "n/v" in combined
    )


def _validate_step_meta(
    output: Dict[str, Any],
    contract: Dict[str, Any],
    errors: List[ValidationIssue],
) -> None:
    step_meta = output.get("step_meta")
    if not isinstance(step_meta, dict):
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="step_meta must be an object",
                path="$.step_meta",
            )
        )
        return

    required_fields = contract.get("outputs", {}).get("step_meta_required_fields", [])
    for field in required_fields:
        value = step_meta.get(field)
        if isinstance(value, str):
            if not value.strip():
                errors.append(
                    ValidationIssue(
                        code=error_codes.MISSING_REQUIRED_FIELDS,
                        message=f"Missing required step_meta field: {field}",
                        path=f"$.step_meta.{field}",
                    )
                )
        elif value is None:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"Missing required step_meta field: {field}",
                    path=f"$.step_meta.{field}",
                )
            )

    for field in ("started_at_utc", "finished_at_utc"):
        value = step_meta.get(field)
        if isinstance(value, str) and value.strip():
            if not _is_iso_utc(value):
                errors.append(
                    ValidationIssue(
                        code=error_codes.INVALID_STEP_META_TIMESTAMP,
                        message=f"step_meta.{field} must be ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)",
                        path=f"$.step_meta.{field}",
                    )
                )

    pipeline_version = step_meta.get("pipeline_version")
    if isinstance(pipeline_version, str):
        pipeline_version = pipeline_version.strip()
        if pipeline_version:
            if pipeline_version == "n/v" or not _PIPELINE_VERSION_RE.match(pipeline_version):
                errors.append(
                    ValidationIssue(
                        code=error_codes.INVALID_PIPELINE_VERSION,
                        message="step_meta.pipeline_version must be a git SHA or SemVer with build metadata",
                        path="$.step_meta.pipeline_version",
                    )
                )


def _collect_finding_texts(findings: Any) -> List[str]:
    texts: List[str] = []
    if isinstance(findings, list):
        for entry in findings:
            if isinstance(entry, dict):
                summary = entry.get("summary")
                if isinstance(summary, str):
                    texts.append(summary)
                notes = entry.get("notes", [])
                if isinstance(notes, list):
                    texts.extend([note for note in notes if isinstance(note, str)])
            elif isinstance(entry, str):
                texts.append(entry)
    elif isinstance(findings, str):
        texts.append(findings)
    return texts


def _validate_source_list(
    sources: Any,
    path_prefix: str,
    errors: List[ValidationIssue],
) -> None:
    if not isinstance(sources, list):
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message=f"{path_prefix} must be a list",
                path=path_prefix,
            )
        )
        return

    for i, entry in enumerate(sources):
        if not isinstance(entry, dict):
            errors.append(
                ValidationIssue(
                    code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                    message="source entries must be objects with publisher and url",
                    path=f"{path_prefix}[{i}]",
                )
            )
            continue
        publisher = str(entry.get("publisher", "")).strip()
        url = str(entry.get("url", "")).strip()
        accessed = str(entry.get("accessed_at_utc", "")).strip()
        if (
            not publisher
            or not url
            or not accessed
            or not _is_http_url(url)
            or not _is_iso_utc(accessed)
        ):
            errors.append(
                ValidationIssue(
                    code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                    message="source requires publisher, http(s) url, accessed_at_utc",
                    path=f"{path_prefix}[{i}]",
                )
            )


def _validate_search_attempts(
    attempts: Any,
    path_prefix: str,
    errors: List[ValidationIssue],
) -> None:
    if not isinstance(attempts, list):
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message=f"{path_prefix} must be a list",
                path=path_prefix,
            )
        )
        return

    for i, entry in enumerate(attempts):
        if not isinstance(entry, dict):
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message="search_attempt entries must be objects with url and accessed_at_utc",
                    path=f"{path_prefix}[{i}]",
                )
            )
            continue
        url = str(entry.get("url", "")).strip()
        accessed = str(entry.get("accessed_at_utc", "")).strip()
        if not url or not accessed or not _is_http_url(url) or not _is_iso_utc(accessed):
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message="search_attempt requires http(s) url and accessed_at_utc",
                    path=f"{path_prefix}[{i}]",
                )
            )

def _current_year() -> int:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).year

def validate_ag01_output(output: Dict[str, Any], contract: Dict[str, Any]) -> ValidatorResult:
    step_id = contract["step_id"]
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    # Required sections
    required_sections = contract["outputs"]["required_sections"]
    for section in required_sections:
        if section not in output:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_SECTIONS,
                    message=f"Missing required section: {section}",
                    path=f"$.{section}",
                )
            )

    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    _validate_step_meta(output, contract, errors)
    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    source_registry = output.get("source_registry", {})
    for field in contract["outputs"]["source_registry_required_fields"]:
        if field not in source_registry:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"Missing required source_registry field: {field}",
                    path=f"$.source_registry.{field}",
                )
            )

    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    primary_sources = source_registry.get("primary_sources")
    secondary_sources = source_registry.get("secondary_sources")

    if not isinstance(primary_sources, list) or len(primary_sources) == 0:
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="primary_sources must be a non-empty list",
                path="$.source_registry.primary_sources",
            )
        )
    else:
        _validate_source_list(primary_sources, "$.source_registry.primary_sources", errors)

    if secondary_sources is not None:
        _validate_source_list(secondary_sources, "$.source_registry.secondary_sources", errors)

    findings = output.get("findings")
    finding_texts = _collect_finding_texts(findings)
    claim_texts = [text for text in finding_texts if _finding_contains_claim(text)]
    if claim_texts:
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_SOURCES_FOR_CLAIMS,
                message="findings must not include factual claims beyond source identification",
                path="$.findings",
            )
        )

    ok = len(errors) == 0
    return ValidatorResult(ok=ok, step_id=step_id, errors=errors, warnings=warnings)

def validate_ag10_output(
    output: Dict[str, Any],
    contract: Dict[str, Any],
    expected_entity_key: Optional[str] = None,
    expected_domain: Optional[str] = None,
) -> ValidatorResult:
    step_id = contract["step_id"]
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    # Required sections
    required_sections = contract["outputs"]["required_sections"]
    for section in required_sections:
        if section not in output:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_SECTIONS,
                    message=f"Missing required section: {section}",
                    path=f"$.{section}",
                )
            )

    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    _validate_step_meta(output, contract, errors)
    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    _validate_step_meta(output, contract, errors)
    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    _validate_step_meta(output, contract, errors)
    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    entities = output.get("entities_delta", [])
    if not isinstance(entities, list):
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="entities_delta must be a list",
                path="$.entities_delta",
            )
        )
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    # Target entity update must exist
    target = None
    for e in entities:
        if isinstance(e, dict) and e.get("entity_id") == "TGT-001":
            target = e
            break

    if target is None:
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_TARGET_ENTITY,
                message="Missing target entity update with entity_id='TGT-001'",
                path="$.entities_delta",
            )
        )
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    # Required fields in target entity
    for field in contract["outputs"]["target_entity_required_fields"]:
        if field not in target:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"Missing required field in target entity: {field}",
                    path=f"$.entities_delta[?(@.entity_id=='TGT-001')].{field}",
                )
            )

    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    # Core invariants
    if target.get("entity_type") != "target_company":
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="entity_type must be 'target_company' for TGT-001",
                path="$.entities_delta[?(@.entity_id=='TGT-001')].entity_type",
            )
        )

    if expected_entity_key is not None:
        actual_key = str(target.get("entity_key", ""))
        if actual_key != expected_entity_key:
            errors.append(
                ValidationIssue(
                    code=error_codes.INVALID_ENTITY_KEY,
                    message=f"entity_key must match meta.case_normalized.entity_key ({expected_entity_key})",
                    path="$.entities_delta[?(@.entity_id=='TGT-001')].entity_key",
                )
            )

    if expected_domain is not None:
        actual_domain = str(target.get("domain", ""))
        if actual_domain != expected_domain:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"domain must match meta.case_normalized.web_domain_normalized ({expected_domain})",
                    path="$.entities_delta[?(@.entity_id=='TGT-001')].domain",
                )
            )

    # Relations must be empty for AG-10
    relations = output.get("relations_delta", [])
    if isinstance(relations, list) and len(relations) > 0:
        errors.append(
            ValidationIssue(
                code=error_codes.RELATIONS_NOT_EMPTY,
                message="AG-10 must not emit relations_delta (must be empty list)",
                path="$.relations_delta",
            )
        )

    # Founding year format
    fy = target.get("founding_year")
    if fy != "n/v":
        if not isinstance(fy, int):
            errors.append(
                ValidationIssue(
                    code=error_codes.INVALID_FOUNDING_YEAR,
                    message="founding_year must be an integer or 'n/v'",
                    path="$.entities_delta[?(@.entity_id=='TGT-001')].founding_year",
                )
            )
        else:
            year_now = _current_year()
            if fy < 1800 or fy > year_now:
                errors.append(
                    ValidationIssue(
                        code=error_codes.INVALID_FOUNDING_YEAR,
                        message=f"founding_year out of range: {fy} (expected 1800..{year_now})",
                        path="$.entities_delta[?(@.entity_id=='TGT-001')].founding_year",
                    )
                )

    registration_signals = str(target.get("registration_signals", "")).strip()
    if registration_signals and registration_signals != "n/v":
        markers = (
            "handelsregister",
            "commercial register",
            "registergericht",
            "amtsgericht",
            "hrb",
            "hra",
        )
        lowered = registration_signals.lower()
        if not any(marker in lowered for marker in markers):
            errors.append(
                ValidationIssue(
                    code=error_codes.INVALID_REGISTRATION_SIGNALS,
                    message="registration_signals must include a known register marker (no invented registration numbers)",
                    path="$.entities_delta[?(@.entity_id=='TGT-001')].registration_signals",
                )
            )

    # Evidence rule: if any legal field is present, require sources
    legal_fields = ["legal_name", "legal_form", "founding_year", "registration_signals"]
    has_claim = any(target.get(k) not in (None, "", "n/v") for k in legal_fields)
    sources = output.get("sources", [])
    field_sources = output.get("field_sources", {})

    if has_claim:
        if not isinstance(sources, list) or len(sources) == 0:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_SOURCES_FOR_CLAIMS,
                    message="sources must be non-empty when legal identity claims are present",
                    path="$.sources",
                )
            )
        else:
            for i, s in enumerate(sources):
                if not isinstance(s, dict):
                    errors.append(
                        ValidationIssue(
                            code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                            message="each source must be an object",
                            path=f"$.sources[{i}]",
                        )
                    )
                    continue
                publisher = str(s.get("publisher", "")).strip()
                url = str(s.get("url", "")).strip()
                accessed = str(s.get("accessed_at_utc", "")).strip()
                if not publisher or not url or not accessed or not _is_http_url(url):
                    errors.append(
                        ValidationIssue(
                            code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                            message="source requires publisher, http(s) url, accessed_at_utc",
                            path=f"$.sources[{i}]",
                        )
                    )

    if not isinstance(field_sources, dict):
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="field_sources must be an object keyed by legal field",
                path="$.field_sources",
            )
        )
    else:
        for field in legal_fields:
            if field not in field_sources:
                errors.append(
                    ValidationIssue(
                        code=error_codes.MISSING_REQUIRED_FIELDS,
                        message=f"field_sources missing key for {field}",
                        path=f"$.field_sources.{field}",
                    )
                )
                continue

            evidence_list = field_sources.get(field)
            if not isinstance(evidence_list, list):
                errors.append(
                    ValidationIssue(
                        code=error_codes.MISSING_REQUIRED_FIELDS,
                        message=f"field_sources.{field} must be a list",
                        path=f"$.field_sources.{field}",
                    )
                )
                continue

            if target.get(field) not in (None, "", "n/v") and len(evidence_list) == 0:
                errors.append(
                    ValidationIssue(
                        code=error_codes.MISSING_SOURCES_FOR_CLAIMS,
                        message=f"field_sources.{field} must include at least one evidence url for non-n/v values",
                        path=f"$.field_sources.{field}",
                    )
                )
                continue

            for idx, evidence in enumerate(evidence_list):
                if isinstance(evidence, str):
                    url = evidence.strip()
                elif isinstance(evidence, dict):
                    url = str(evidence.get("url", "")).strip()
                else:
                    url = ""

                if not url or not _is_http_url(url):
                    errors.append(
                        ValidationIssue(
                            code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                            message=f"field_sources.{field} evidence must include a http(s) url",
                            path=f"$.field_sources.{field}[{idx}]",
                        )
                    )

    # Warning: all legal fields are n/v
    all_nv = all(target.get(k) in (None, "", "n/v") for k in legal_fields)
    if all_nv:
        warnings.append(
            ValidationIssue(
                code=error_codes.MISSING_SOURCES_FOR_CLAIMS,
                message="No verifiable legal identity evidence found (all legal fields n/v).",
                path="$.entities_delta[?(@.entity_id=='TGT-001')]",
            )
        )

    ok = len(errors) == 0
    return ValidatorResult(ok=ok, step_id=step_id, errors=errors, warnings=warnings)

def validate_ag11_output(output: Dict[str, Any], contract: Dict[str, Any]) -> ValidatorResult:
    step_id = contract["step_id"]
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    required_sections = contract["outputs"]["required_sections"]
    for section in required_sections:
        if section not in output:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_SECTIONS,
                    message=f"Missing required section: {section}",
                    path=f"$.{section}",
                )
            )

    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    entities = output.get("entities_delta", [])
    if not isinstance(entities, list):
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="entities_delta must be a list",
                path="$.entities_delta",
            )
        )
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    relations = output.get("relations_delta", [])
    if not isinstance(relations, list):
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="relations_delta must be a list",
                path="$.relations_delta",
            )
        )
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    site_keys: List[str] = []
    for i, entity in enumerate(entities):
        if not isinstance(entity, dict):
            errors.append(
                ValidationIssue(
                    code=error_codes.INVALID_SITE_ENTITY,
                    message="site entities must be objects",
                    path=f"$.entities_delta[{i}]",
                )
            )
            continue
        if entity.get("entity_type") != "site":
            errors.append(
                ValidationIssue(
                    code=error_codes.INVALID_SITE_ENTITY,
                    message="entities_delta must only contain site entities",
                    path=f"$.entities_delta[{i}].entity_type",
                )
            )
            continue
        required_fields = ["entity_key", "entity_name", "site_type", "country_region", "city"]
        for field in required_fields:
            if field not in entity:
                errors.append(
                    ValidationIssue(
                        code=error_codes.MISSING_REQUIRED_FIELDS,
                        message=f"Missing required field in site entity: {field}",
                        path=f"$.entities_delta[{i}].{field}",
                    )
                )
        country_region = str(entity.get("country_region", "")).strip()
        if country_region == "":
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message="country_region must be present or 'n/v'",
                    path=f"$.entities_delta[{i}].country_region",
                )
            )
        entity_key = str(entity.get("entity_key", "")).strip()
        if entity_key:
            site_keys.append(entity_key)

    relation_site_keys = set()
    for i, relation in enumerate(relations):
        if not isinstance(relation, dict):
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message="relations_delta entries must be objects",
                    path=f"$.relations_delta[{i}]",
                )
            )
            continue
        if relation.get("relation_type") != "operates_at":
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message="relations_delta must use relation_type='operates_at'",
                    path=f"$.relations_delta[{i}].relation_type",
                )
            )
        if relation.get("from_entity_id") != "TGT-001":
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_SITE_RELATION,
                    message="site relations must reference from_entity_id='TGT-001'",
                    path=f"$.relations_delta[{i}].from_entity_id",
                )
            )
        to_key = str(relation.get("to_entity_key", "")).strip()
        if to_key:
            relation_site_keys.add(to_key)

    for site_key in site_keys:
        if site_key not in relation_site_keys:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_SITE_RELATION,
                    message="site entities must have operates_at relation from TGT-001",
                    path="$.relations_delta",
                )
            )

    sources = output.get("sources", [])
    if site_keys:
        if not isinstance(sources, list) or len(sources) == 0:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_SOURCES_FOR_CLAIMS,
                    message="sources must be non-empty when site entities are present",
                    path="$.sources",
                )
            )
        else:
            for i, s in enumerate(sources):
                if not isinstance(s, dict):
                    errors.append(
                        ValidationIssue(
                            code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                            message="source entries must be objects",
                            path=f"$.sources[{i}]",
                        )
                    )
                    continue
                publisher = str(s.get("publisher", "")).strip()
                url = str(s.get("url", "")).strip()
                accessed = str(s.get("accessed_at_utc", "")).strip()
                if not publisher or not url or not accessed or not _is_http_url(url):
                    errors.append(
                        ValidationIssue(
                            code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                            message="source requires publisher, http(s) url, accessed_at_utc",
                            path=f"$.sources[{i}]",
                        )
                    )

    search_attempts = output.get("search_attempts")
    if search_attempts is not None:
        _validate_search_attempts(search_attempts, "$.search_attempts", errors)

    finding_texts = _collect_finding_texts(output.get("findings"))
    if _findings_signal_no_evidence(finding_texts):
        has_sources = isinstance(sources, list) and len(sources) > 0
        has_attempts = isinstance(search_attempts, list) and len(search_attempts) > 0
        if not has_sources and not has_attempts:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message="findings report no evidence; include sources or search_attempts",
                    path="$.sources",
                )
            )

    ok = len(errors) == 0
    return ValidatorResult(ok=ok, step_id=step_id, errors=errors, warnings=warnings)

def validate_ag20_output(
    output: Dict[str, Any],
    contract: Dict[str, Any],
    expected_entity_key: Optional[str] = None,
    expected_domain: Optional[str] = None,
) -> ValidatorResult:
    step_id = contract["step_id"]
    errors: List[ValidationIssue] = []
    warnings: List[ValidationIssue] = []

    required_sections = contract["outputs"]["required_sections"]
    for section in required_sections:
        if section not in output:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_SECTIONS,
                    message=f"Missing required section: {section}",
                    path=f"$.{section}",
                )
            )

    if errors:
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    entities = output.get("entities_delta", [])
    if not isinstance(entities, list):
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="entities_delta must be a list",
                path="$.entities_delta",
            )
        )
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    target = None
    for e in entities:
        if isinstance(e, dict) and e.get("entity_id") == "TGT-001":
            target = e
            break

    if target is None:
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_TARGET_ENTITY,
                message="Missing target entity update with entity_id='TGT-001'",
                path="$.entities_delta",
            )
        )
        return ValidatorResult(ok=False, step_id=step_id, errors=errors, warnings=warnings)

    for field in contract["outputs"]["target_entity_required_fields"]:
        if field not in target:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"Missing required field in target entity: {field}",
                    path=f"$.entities_delta[?(@.entity_id=='TGT-001')].{field}",
                )
            )

    if target.get("entity_type") != "target_company":
        errors.append(
            ValidationIssue(
                code=error_codes.MISSING_REQUIRED_FIELDS,
                message="entity_type must be 'target_company' for TGT-001",
                path="$.entities_delta[?(@.entity_id=='TGT-001')].entity_type",
            )
        )

    if expected_entity_key is not None:
        actual_key = str(target.get("entity_key", ""))
        if actual_key != expected_entity_key:
            errors.append(
                ValidationIssue(
                    code=error_codes.INVALID_ENTITY_KEY,
                    message=f"entity_key must match meta.case_normalized.entity_key ({expected_entity_key})",
                    path="$.entities_delta[?(@.entity_id=='TGT-001')].entity_key",
                )
            )

    if expected_domain is not None:
        actual_domain = str(target.get("domain", ""))
        if actual_domain != expected_domain:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"domain must match meta.case_normalized.web_domain_normalized ({expected_domain})",
                    path="$.entities_delta[?(@.entity_id=='TGT-001')].domain",
                )
            )

    size_fields = ["employee_range", "revenue_band", "market_scope_signal"]
    for field in size_fields:
        value = target.get(field)
        if value is None:
            continue
        if value != "n/v" and not isinstance(value, str):
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_REQUIRED_FIELDS,
                    message=f"{field} must be a string or 'n/v'",
                    path=f"$.entities_delta[?(@.entity_id=='TGT-001')].{field}",
                )
            )

    has_claim = any(target.get(k) not in (None, "", "n/v") for k in size_fields)
    sources = output.get("sources", [])

    if has_claim:
        if not isinstance(sources, list) or len(sources) == 0:
            errors.append(
                ValidationIssue(
                    code=error_codes.MISSING_SOURCES_FOR_CLAIMS,
                    message="sources must be non-empty when size claims are present",
                    path="$.sources",
                )
            )
        else:
            for i, s in enumerate(sources):
                if not isinstance(s, dict):
                    errors.append(
                        ValidationIssue(
                            code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                            message="each source must be an object",
                            path=f"$.sources[{i}]",
                        )
                    )
                    continue
                publisher = str(s.get("publisher", "")).strip()
                url = str(s.get("url", "")).strip()
                accessed = str(s.get("accessed_at_utc", "")).strip()
                if not publisher or not url or not accessed or not _is_http_url(url):
                    errors.append(
                        ValidationIssue(
                            code=error_codes.SOURCE_MISSING_REQUIRED_FIELDS,
                            message="source requires publisher, http(s) url, accessed_at_utc",
                            path=f"$.sources[{i}]",
                        )
                    )

    ok = len(errors) == 0
    return ValidatorResult(ok=ok, step_id=step_id, errors=errors, warnings=warnings)
