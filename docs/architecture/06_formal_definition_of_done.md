# Definition of Done (DoD)

**Project:** multi-agent-market-intel-pipeline

**Scope:** Production-grade, audit-grade multi-agent company intelligence pipeline

---

## 1. Repository-Level Completion Criteria

The repository is considered **DONE** only if **all** of the following are true.

### 1.1 Structural Integrity

* All existing folders and agent step IDs are unchanged
* No breaking changes to public interfaces
* Repository runs on a clean environment using documented steps
* No duplicate or unused schema systems exist

### 1.2 Configuration Ownership

* All schemas reside exclusively in:
  * `configs/contracts/`
  * `configs/pipeline/`
  * `configs/rules/`
* No validation logic exists outside `src/validator/`

---

## 2. Run Execution Criteria

A run is considered **DONE** only if:

### 2.1 Run Creation

* Run is created exclusively via UI confirmation
* No artifacts are created before explicit user confirmation
* Each run has a unique, immutable `run_id`

### 2.2 Artifact Layout

For each run, the following exists:

<pre class="overflow-visible! px-0!" data-start="1314" data-end="1382"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>artifacts/runs/<run_id>/
  meta/
  steps/
  logs/
  exports/
</span></span></code></div></div></pre>

No step writes outside this structure.

---

## 3. AG-00 Completion Criteria (Foundation)

AG-00 is considered **DONE** only if:

* `case_normalized.json` exists and is valid
* `company_name_canonical` is non-empty
* `web_domain_normalized` is valid and normalized
* `entity_key` equals `domain:<web_domain_normalized>`
* Gatekeeper returns `PASS`
* Any WARN is explicitly recorded

---

## 4. Agent-Level Completion Criteria (AG-10+)

Each agent step (AG-10 onward) is **DONE** only if:

### 4.1 Output Artifacts

* `steps/<STEP_ID>/output.json` exists
* `steps/<STEP_ID>/validator.json` exists
* `validator.json` includes `run_id`, `pipeline_version`, and `validated_at_utc` (UTC ISO-8601)

### 4.2 Output Structure

Each `output.json` contains:

* step_id
* run_id
* timestamp (UTC)
* entities_delta or report_section
* relations_delta (if applicable)
* findings
* sources

### 4.3 Evidence Discipline

* Every consequential claim has at least one source
* Each source includes:
  * publisher
  * url
  * accessed_at_utc
* Unverifiable data is explicitly `"n/v"`

---

## 5. Gatekeeper Validation Criteria

A step is **DONE** only if the Output Contract Validator returns:

<pre class="overflow-visible! px-0!" data-start="2461" data-end="2482"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>status</span><span> = PASS
</span></span></code></div></div></pre>

### 5.1 Hard Fail Conditions

Any of the following results in  **FAIL** :

* Missing required sections or fields
* Invalid or missing entity IDs
* Duplicate entities with same domain
* Broken cross-references
* Missing sources for claims
* Schema violations

### 5.2 Warning Conditions

Warnings may exist only if:

* They are explicitly recorded
* They do not violate contract rules
* They do not affect downstream determinism

---

## 6. Orchestration Criteria

The pipeline is **DONE** only if:

* Steps execute strictly in DAG order
* No step executes after a gatekeeper FAIL
* Retry logic is bounded and logged
* Orchestrator does not modify agent outputs
* Orchestrator reacts only to validator status

---

## 7. Registry & Identity Criteria

The registry is **DONE** only if:

* `meta/entity_registry.json` exists
* All entities have stable IDs:
  * TGT-001
  * MFR-XXX
  * CUS-XXX
* No two entities share the same domain
* Entities with multiple roles share a single ID

---

## 8. Cross-Reference Integrity Criteria

Cross-references are **DONE** only if:

* All referenced IDs exist in the registry
* No dangling references exist
* Validator enforces referential integrity

---

## 9. Export Criteria

The pipeline is **DONE** only if:

### 9.1 Mandatory Exports

* `exports/report.md`
* `exports/entities.json`

### 9.2 Export Integrity

* Exports are derived only from validated artifacts
* No additional inference or recomputation occurs
* All references in exports resolve to registry IDs

---

## 10. UI Criteria

The UI is **DONE** only if:

* Intake guardrails prevent invalid input
* Preview and confirmation exist before run creation
* Step status and artifacts are visible
* Intake correction and re-run are supported
* Run archiving preserves audit trail

---

## 11. Testing Criteria

The system is **DONE** only if:

* `pytest` passes on a clean environment
* Unit tests exist for:
  * normalization
  * validator logic
  * dedupe and ID policy
* At least one integration smoke test produces valid exports

---

## 12. Determinism & Audit Criteria

The pipeline is **DONE** only if:

* Identical input produces identical structure and IDs
* Non-deterministic behavior is confined to content, not structure
* All outputs can be traced to:
  * step
  * source
  * run_id
* No artifacts are silently overwritten

---

## 13. Documentation Criteria

The system is **DONE** only if:

* Architecture specification exists and matches implementation
* Agent deliverables are documented
* Known limitations are explicitly stated

---

## 14. Final Acceptance Statement

The project is **DONE** only when:

* Every section above is satisfied
* No P0 violations exist
* No hidden bypasses of validation exist
* A full run can be executed, validated, and audited end-to-end

If any criterion fails, the system is  **NOT DONE** .
