# Validation & Gatekeeping

This document captures how the **gatekeeper** validates step outputs and how the orchestrator reacts to PASS/FAIL.

## 1. Gatekeeper Responsibilities

The gatekeeper provides **structural validation**, not semantic judgment. It enforces:

- Required sections and fields per step contract
- Evidence/source rules when claims are present
- Timestamp and pipeline version formats
- Entity key invariants
- Step-specific logic (e.g., AG-10 relations must be empty)

## 2. Validation Flow

For each step:

1. The orchestrator runs the agent.
2. The raw `output.json` is written.
3. The gatekeeper validates the output against the step contract.
4. A `validator.json` payload is written with PASS/FAIL, errors, and warnings.
5. If validation fails, the pipeline **stops immediately** and logs skipped steps.

## 3. Step Meta Validation

Every step validates `step_meta`:

- `run_id` must be non-empty.
- `pipeline_version` must be a git SHA or SemVer with build metadata.
- Timestamps must be ISO-8601 UTC (seconds precision).

If `step_meta` is invalid, the step fails gatekeeping.

## 4. Step-Specific Validation (Highlights)

### 4.1 AG-00

- `entity_key` must be `domain:<web_domain_normalized>`.
- `web_domain_normalized` must pass domain validation.

### 4.2 AG-01

- `primary_sources` must be non-empty.
- Source entries must include `publisher`, `url`, `accessed_at_utc`.
- Findings must not contain claims beyond source identification.

### 4.3 AG-10

- `TGT-001` entity is required and must include legal fields.
- `relations_delta` must be empty.
- Non-`"n/v"` legal fields require sources and field-specific evidence URLs.

### 4.4 AG-11

- Site entities must include required fields (site type, region, city, etc.).
- Relations must link sites to the target entity.

### 4.5 AG-20

- `TGT-001` entity is required with size signals.
- `entity_key` and `domain` must match AG-00 meta artifacts.
- Sources required for claims.

### 4.6 AG-21+

- Contracts define minimum findings/sources and allowed entity/relation types.
- Evidence rules enforce sources when claims are present.

## 5. Validator Output Artifact

The validator emits a structured result:

```json
{
  "step_id": "AG-10",
  "run_id": "<run_id>",
  "pipeline_version": "<version>",
  "validated_at_utc": "2024-01-02T03:04:05Z",
  "ok": true,
  "errors": [],
  "warnings": []
}
```

The orchestrator uses **only** the `ok` flag to decide whether to continue.
