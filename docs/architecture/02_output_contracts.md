# Output Contracts

This document enumerates the **actual output contracts** enforced by the gatekeeper. The source of truth is `configs/pipeline/step_contracts.yml`, enforced by `src/validator/contract_validator.py`.

## 1. Shared Contract Surface

All step outputs are JSON objects that include `step_meta` and step-specific sections. The gatekeeper validates:

- Required sections exist (per step contract).
- Required fields exist (per contract and validator rules).
- Timestamp and pipeline version formats in `step_meta`.
- Evidence/source rules (when claims are present).

`step_meta` must include:

- `step_id`
- `agent_name`
- `run_id`
- `started_at_utc` (ISO-8601 UTC)
- `finished_at_utc` (ISO-8601 UTC)
- `pipeline_version` (git SHA or SemVer+build metadata)

## 2. Step-Specific Contracts

### 2.1 AG-00 (Intake Normalization)

Required sections:

- `step_meta`
- `case_normalized`
- `target_entity_stub`
- `entities_delta`
- `relations_delta`
- `findings`

Required fields:

- `case_normalized.company_name_canonical`
- `case_normalized.web_domain_normalized`
- `case_normalized.entity_key` (must be `domain:<normalized_domain>`)
- `target_entity_stub.entity_type`
- `target_entity_stub.entity_name`
- `target_entity_stub.domain`
- `target_entity_stub.entity_key`

Validation highlights:

- Domain must pass format validation.
- `entity_key` must match the normalized domain.

### 2.2 AG-01 (Source Registry)

Required sections:

- `step_meta`
- `source_registry`
- `findings`
- `sources`

Required fields:

- `source_registry.primary_sources` (non-empty list)
- `source_registry.secondary_sources`
- `source_registry.source_scope_notes`

Validation highlights:

- Source entries must include `publisher`, `url`, and `accessed_at_utc` (HTTP/HTTPS, ISO UTC).
- Findings must **not** include factual claims beyond source identification.

### 2.3 AG-10 (Identity & Legal)

Required sections:

- `step_meta`
- `entities_delta`
- `relations_delta` (must be empty)
- `findings`
- `sources`
- `field_sources`

Target entity requirements (entity_id = `TGT-001`):

- `entity_id`, `entity_type`, `entity_name`, `domain`, `entity_key`
- `legal_name`, `legal_form`, `founding_year`, `registration_signals`

Validation highlights:

- `founding_year` must be an integer (1800..current year) or `"n/v"`.
- `registration_signals` must include a known registry marker.
- If any legal field is present, `sources` must be non-empty.
- `field_sources.<field>` must include evidence URLs for non-`"n/v"` values.

### 2.4 AG-11 (Locations & Sites)

Required sections:

- `step_meta`
- `entities_delta`
- `relations_delta`
- `findings`
- `sources`
- `search_attempts`

Validation highlights:

- Site entities must include `entity_key`, `entity_type`, `entity_name`, `site_type`, `country_region`, `city`.
- A `TGT-001` target entity must be present.
- Relations must connect sites to the target entity.

### 2.5 AG-20 (Company Size)

Required sections:

- `step_meta`
- `entities_delta`
- `findings`
- `sources`

Target entity requirements (entity_id = `TGT-001`):

- `employee_range`
- `revenue_band`
- `market_scope_signal`

Validation highlights:

- `entity_key` and `domain` must match AG-00 meta.
- Sources required for claims.

### 2.6 AG-21+ (Research Steps)

AG-21 and all subsequent research steps are validated through the **generic research validator**. Contract-specific gatekeeper rules (e.g., minimum findings/sources, allowed entity/relation types) are read from `configs/pipeline/step_contracts.yml`.

Validation highlights:

- `findings` must be a list (min size when configured).
- `entities_delta` / `relations_delta` are required if the contract demands them.
- Evidence rules enforce sources when claims, entities, or relations are present.

## 3. Contract Evolution

To modify contracts:

1. Update `configs/pipeline/step_contracts.yml`.
2. Ensure validator logic remains compatible (no new schema systems).
3. Update documentation and examples under `docs/examples/`.
