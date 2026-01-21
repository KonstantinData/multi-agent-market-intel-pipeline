# multi-agent-market-intel-pipeline

A production-grade, contract-gated multi-agent pipeline for B2B company intelligence, customer and competitor mapping, and auditable market research outputs.

---

## What this repository does

This repository implements an **artifact-based, auditable, multi-agent market intelligence pipeline** that converts a single company input (name + domain) into a structured, governance-safe output package:

- Verified target company profile (identity, legal, locations, portfolio)
- Publicly evidenced customer and reference mapping
- Peer / competitor manufacturer discovery (product-match peers)
- Customer-of-manufacturers mapping (market-wide buyer landscape)
- Sales and negotiation playbook derived from verifiable signals (no guessing)
- Cross-referenced index with stable IDs (deduplicated entities)
- Machine-readable JSON exports for downstream automation

The system is designed to run **parallel domain agents (Fan-Out)** while preserving governance via **contract validation** and a centralized **entity registry**.

---

## Core design goals

- **Auditability:** Every run produces a full artifact trail (inputs, outputs, validation results, merge states, exports).
- **Contract enforcement:** Every step must satisfy strict output contracts (schemas + rules) or it fails fast.
- **Deterministic governance:** IDs, deduplication, merge policies, and cross-references are deterministic even if LLM-generated text varies.
- **Parallel execution:** Domain agents can run in parallel; results are merged at explicit barriers.
- **Evidence-based output:** No invented facts. If something cannot be verified, output `n/v`.
- **Recruiter-ready engineering:** Clear separation of concerns, versioned configs, tests, and decision traceability (ADRs).

---

## Architecture overview

### High-level workflow

The pipeline runs as a **DAG** defined in `configs/pipeline/dag.yml`. The current
implementation executes a single linear sequence of steps (no parallel fan-out
in the orchestrator yet):

1. **AG-00** Intake normalization
2. **AG-01** Source registry
3. **AG-10** Identity and legal
4. **AG-11** Locations and sites
5. **AG-20** Company size
6. **AG-21** Financial signals
7. **AG-30** Portfolio
8. **AG-31** Markets focus
9. **AG-40** Target customers
10. **AG-41** Peer discovery
11. **AG-42** Customers of manufacturers
12. **AG-70** Supply chain technology
13. **AG-71** Supply chain risks
14. **AG-72** Sustainability and circularity
15. **AG-81** Industry trends
16. **AG-82** Trade fairs and events
17. **AG-83** Associations and memberships
18. **AG-90** Sales playbook

Each step runs only after its dependency completes and passes contract
validation.

### Key subsystems

- **Orchestrator (`src/orchestrator/`)**

  - DAG loading and resolution
  - sequential scheduling and execution (current implementation)
  - contract gatekeeper enforcement
  - retry/abort handling based on error types
  - artifact writing (atomic writes)
- **Domain Agents (`src/agents/`)**

  - single-responsibility research steps
  - each agent performs **self-validation** of its findings
  - agents emit **delta outputs** only (no global IDs)
- **Validator / Gatekeeper (`src/validator/`)**

  - schema validation (JSON Schema)
  - rule validation (required fields, evidence policy, ASCII policy)
  - cross-reference integrity checks (hard fail on broken links)
  - PASS/FAIL results control orchestration
- **Entity Registry (`src/registry/`)**

  - centralized deduplication (domain-based entity keys)
  - deterministic ID allocation (TGT/MFR/CUS)
  - merge conflict resolution with provenance tracking
  - cross-reference graph construction
- **Exporters (`src/exporters/`)**

  - Markdown report builder (`report.md`)
  - entity export (`entities.json`, `entities.csv`)
  - relations/cross-reference export (`relations.json`, `relations.csv`)
  - index export (`index.json`, `index.csv`)

---

## Governance principles

### 1) No assumption-based content

The pipeline must not invent facts.
If evidence is missing, output must be **`n/v`**.

### 2) Evidence and sources are mandatory

All consequential claims must be backed by structured sources:

- publisher
- url
- title (if available)
- accessed timestamp

### 3) Output contracts are non-negotiable

Every step output must conform to:

- `configs/contracts/*.json`
- `configs/pipeline/step_contracts.yml`
- `configs/rules/validator_rules.yml`

A failing step blocks the next step.

### 4) Centralized ID governance (no parallel ID collisions)

IDs are assigned only during registry merge:

- Target company: `TGT-001`
- Manufacturers/peers: `MFR-XXX`
- Customers: `CUS-XXX`

Agents must not generate final IDs.

### 5) Fan-Out / Fan-In barriers are explicit

Parallel steps merge only at explicit DAG nodes.
No step may consume partially merged registry states.

### 6) Artifact-based reproducibility

Each run produces a deterministic artifact layout for:

- debugging
- review
- audit trails
- reruns

---

## Repository layout

### Top-level

- `src/`Production code: orchestrator, agents, registry, validator, exporters.
  - `src/agent_common/` Shared agent utilities (canonical location for shared helpers; do not add `src/agents/common`).
- `configs/`Versioned pipeline governance:

  - DAG definition
  - contracts (schemas)
  - validation rules (ID policy, dedupe, evidence requirements)
- `docs/`Architecture documentation and decision traceability:

  - architecture deep dives
  - ADRs (architectural decisions)
  - examples
- `tests/`Unit and integration tests:

  - contract validation tests
  - registry dedupe + ID allocation tests
  - pipeline smoke tests
- `runs/`Runtime artifacts and outputs (**not committed**).Intentionally separated from `src/`.
- `scripts/`
  Local run and validation helper scripts.

---

## Run artifacts and output structure

Each pipeline execution produces a run directory like:

```text
artifacts/runs/<run_id>/
  meta/
    run_meta.json
    dag_resolved.json
    env_snapshot.json

  steps/<AG-XX>/
    input.json
    output.json
    validator.json
    log.txt

  registry/
    registry_v0_init.json
    registry_v1_post_P1.json
    ...

  exports/
    report.md
    entities.json
    entities.csv
    relations.json
    relations.csv
    index.json
    index.csv

  logs/
    pipeline.log
    errors.log
```

### Why artifacts matter

Artifacts enable:

- post-run validation and review
- deterministic debugging of failures
- evidence re-checking
- reproducible stakeholder reporting

---

## Installation

### Create and activate a virtual environment

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Git Bash:

```bash
python -m venv venv
source venv/Scripts/activate
```

### Install runtime dependencies

```bash
pip install -r requirements.txt
```

### Install development dependencies (optional)

```bash
pip install -r requirements-dev.txt
```

---

## How to run (planned CLI entrypoint)

The orchestration entrypoint is:

```bash
python -m src.orchestrator.run_pipeline \
  --run-id <run_id> \
  --case-file <path/to/case.json> \
  --pipeline-version <git_sha_or_semver>
```

Run flags:

- `--run-id` (required): ID used for the artifacts directory under `artifacts/runs/`.
- `--case-file` (required): Path to the case input JSON.
- `--pipeline-version` (optional): Overrides the pipeline version in the case file or
  `PIPELINE_VERSION`. Required one way or another.
- `--overwrite`: Replace an existing non-empty run directory.
- `--backup-existing`: Archive an existing non-empty run directory before running.

For local runs, set `OPENAI_KEY` and `PIPELINE_VERSION` in a `.env` file at the repo root
(or export them in your shell) so the agents can authenticate and the orchestrator can
resolve the required pipeline version. You can optionally set `GIT_SHA` for run metadata;
see `.env.example` for the canonical keys.

Currently, the orchestrator runs the following agents (in the DAG order above):

- AG-00 (Intake Normalization)
- AG-01 (Source Registry)
- AG-10 (Identity and Legal)
- AG-11 (Locations and Sites)
- AG-20 (Company Size)
- AG-21 (Financial Signals)
- AG-30 (Portfolio)
- AG-31 (Markets Focus)
- AG-40 (Target Customers)
- AG-41 (Peer Discovery)
- AG-42 (Customers of Manufacturers)
- AG-70 (Supply Chain Tech)
- AG-71 (Supply Chain Risks)
- AG-72 (Sustainability & Circularity)
- AG-81 (Industry Trends)
- AG-82 (Trade Fairs & Events)
- AG-83 (Associations & Memberships)
- AG-90 (Sales Playbook)

A typical run expects a case input with:

- `company_name`
- `company_domain`
- `pipeline_version` (or provide `--pipeline-version` / `PIPELINE_VERSION`)

Example case format:

```json
{
  "company_name": "GROB-WERKE GmbH & Co. KG",
  "company_domain": "grobgroup.com",
  "pipeline_version": "local-dev+001"
}
```

---

## Testing

### Run unit tests

```bash
pytest -q
```

### Run full suite with coverage

```bash
pytest --cov=src --cov-report=term-missing
```

---

## CI/CD gates

The CI workflow is intended to enforce:

- schema/contract validation tests
- unit tests
- optional static checks (ruff, mypy)

See: `.github/workflows/ci.yml`

---

## Decision traceability (ADRs)

Key architectural decisions are captured as ADRs in:

- `docs/adr/`

Start here:

- `docs/adr/ADR-000-index.md`

---

## Contributing / engineering workflow

This repository follows a contract-first development process:

1. Write/update contracts (`configs/contracts/`, `configs/rules/`)
2. Implement step logic (`src/agents/`, `src/validator/`, `src/registry/`)
3. Add/extend tests (`tests/`)
4. Validate via CI gates
5. Commit changes with clear messages

---

## Roadmap (engineering milestones)

P0 (must-have)

- Orchestrator skeleton + DAG loader
- Contract validator v1 (schema + rules)
- Central entity registry + deterministic IDs
- Minimal exporters (`entities.json` + `report.md`)

P1 (important)

- Parallel scheduler + explicit barriers
- Merge conflict resolution policy + provenance tracking
- Full cross-reference matrix export

P2 (nice-to-have)

- Pre-commit hooks + strict linting gates
- Rich report formatting and optional diagrams
- Advanced caching / memoization layer

---

## License

This project is available under a Non-Commercial license. Commercial licensing is available on request.

See [LICENSE](LICENSE)
