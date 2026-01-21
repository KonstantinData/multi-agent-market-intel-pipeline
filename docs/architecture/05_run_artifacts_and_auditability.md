# Run Artifacts & Auditability

This document describes the **artifact lifecycle** for each pipeline run, including how artifacts are written, validated, and exported.

## 1. Run Root & Directory Layout

Every run lives under a unique run directory:

```
artifacts/runs/<run_id>/
  meta/
  steps/
  logs/
  exports/
```

The run context creates these folders up front and all artifacts must stay within this tree.

## 2. Artifact Lifecycle (Per Step)

For each step in the DAG:

1. The orchestrator creates `steps/<STEP_ID>/`.
2. The agent runs and emits a JSON payload.
3. `steps/<STEP_ID>/output.json` is written atomically.
4. The gatekeeper validates the payload.
5. `steps/<STEP_ID>/validator.json` is written with PASS/FAIL and errors.
6. If validation fails, the pipeline stops and logs skipped steps.

If the agent fails its own preconditions, the pipeline writes:

- `steps/<STEP_ID>/agent_error.json`

## 3. Meta Artifacts

After AG-00 succeeds, the orchestrator persists stable meta artifacts used by later steps:

- `meta/case_normalized.json`
- `meta/target_entity_stub.json`

These are the only meta payloads required by subsequent steps today.

## 4. Logs

The orchestrator writes a pipeline log:

- `logs/pipeline.log`

The log records start/end markers, step execution, validation status, and any early termination.

## 5. Exports (Derived Only From Validated Artifacts)

At the end of a successful run, the reporting layer builds exports from **validated step outputs**:

- `exports/report.md`
- `exports/entities.json`
- `exports/relations.json`
- `exports/index.json`
- `exports/entities.csv`
- `exports/relations.csv`
- `exports/index.csv`

The exporter aggregates `entities_delta` and `relations_delta` into a registry, then renders human-readable and machine-readable outputs. No additional inference is performed during export.

## 6. Immutability & Audit Rules

- Artifacts are written with atomic file moves to prevent partial writes.
- A run directory cannot be overwritten unless `--overwrite` or `--backup-existing` is provided.
- Corrections create new runs (or backup previous runs) rather than mutating historical artifacts.

## 7. Traceability Guarantees

Every artifact ties back to:

- a `run_id`
- a `step_id`
- a `pipeline_version`

This provides traceability across input, validation, and exported outputs.
