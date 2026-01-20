# Architecture Specification

**Project:** multi-agent-market-intel-pipeline

**Purpose:** Deterministic, auditable, multi-agent B2B company intelligence with strict output contracts and governance

---

## 1. Architectural Goals

### 1.1 Primary Goals

* Produce **verifiable, evidence-backed company intelligence**
* Enforce **structural correctness** independently from content quality
* Ensure **auditability and reproducibility** of every run
* Scale agent count without degrading governance
* Prevent silent corruption (schema drift, dedupe errors, broken references)

### 1.2 Non-Goals

* Real-time / streaming processing
* Autonomous decision-making without evidence
* Free-form LLM outputs
* Heuristic or probabilistic validation

---

## 2. High-Level System Architecture

### 2.1 Core Components

The system consists of five strictly separated layers:

1. **UI Layer**
2. **Orchestration Layer**
3. **Domain Agent Layer**
4. **Output Contract Validation Layer (Gatekeeper)**
5. **Artifact & Registry Layer**

Each layer has  **clear ownership and failure boundaries** .

---

## 3. UI Layer

### 3.1 Responsibility

* Human interaction only
* No business logic
* No validation authority

### 3.2 Key Functions

* Intake input collection (company_name, domain, optional fields)
* Live normalization preview (AG-00 pre-view)
* Hard input guardrails (invalid domain disables start)
* Explicit confirmation before run creation
* Run monitoring (step status, artifacts)
* Intake correction workflow (case_corrected.json)
* Run archiving (non-destructive)

### 3.3 Architectural Constraints

* UI must never write step outputs
* UI must never bypass orchestrator or validator
* UI must never decide PASS/FAIL

---

## 4. Orchestration Layer

### 4.1 Role

The Orchestrator is  **dumb but strict** .

It:

* Executes agents in defined order
* Persists artifacts
* Delegates validation
* Decides flow control

It does  **not** :

* Judge content correctness
* Modify agent outputs
* Apply heuristics

### 4.2 Execution Model

* Batch execution
* One run = one immutable artifact tree
* Deterministic control flow driven by DAG config

### 4.3 Step Lifecycle

For each step:

1. Load required artifacts (meta + registry snapshot)
2. Execute domain agent
3. Persist raw step output
4. Invoke Output Contract Validator
5. Act on validator result:
   * PASS → continue
   * FAIL → retry (bounded) or abort

---

## 5. Domain Agent Layer

### 5.1 Agent Responsibility

Each domain agent is **fully responsible for content quality** within its scope.

Agents must:

* Perform research or structured extraction
* Use inference only when source-backed
* Emit `"n/v"` when verification is impossible
* Normalize entity names and domains
* Output strictly contract-compliant structures

### 5.2 What Agents Are NOT

* Agents are not validators
* Agents do not manage IDs globally
* Agents do not dedupe globally
* Agents do not decide pipeline continuation

### 5.3 Determinism Policy

* Logic and formatting must be deterministic
* LLM usage is allowed only with:
  * fixed prompts
  * fixed output schemas
  * validator enforcement

---

## 6. Output Contract Validation Layer (Gatekeeper)

### 6.1 Purpose

The Gatekeeper is the **structural quality authority** of the system.

It validates:

* Format correctness
* Schema adherence
* Structural completeness
* Cross-reference integrity

It does **not** evaluate:

* Business plausibility
* Strategic relevance
* Semantic correctness beyond structure

### 6.2 Validation Scope

The Gatekeeper enforces:

* Output schema validity
* Mandatory sections present
* Entity ID rules respected
* Dedupe rules applied
* Cross-references resolvable
* Source format correctness
* Correct usage of `"n/v"`

### 6.3 Validator Output

Validator returns a deterministic result:

* status: PASS or FAIL
* error list with types
* fix instructions (machine-readable)

The Orchestrator reacts **only** to status.

---

## 7. Artifact Model

### 7.1 Artifact Root

<pre class="overflow-visible! px-0!" data-start="4281" data-end="4313"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>artifacts/runs/<run_id>/
</span></span></code></div></div></pre>

### 7.2 Mandatory Substructure

<pre class="overflow-visible! px-0!" data-start="4346" data-end="4391"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>meta/
steps/<STEP_ID>/
logs/
</span><span>exports</span><span>/
</span></span></code></div></div></pre>

### 7.3 Immutability Rules

* Step outputs are append-only
* Corrections create new artifacts, never overwrite
* Archived runs are moved, not deleted

---

## 8. Registry & Identity Model

### 8.1 Central Entity Registry

A single authoritative registry per run:

<pre class="overflow-visible! px-0!" data-start="4655" data-end="4688"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>meta/entity_registry.json
</span></span></code></div></div></pre>

### 8.2 ID Policy

* Target company: TGT-001
* Manufacturers: MFR-XXX
* Customers: CUS-XXX

If an entity fulfills multiple roles:

* **One ID only**

### 8.3 Dedupe Rules

* Primary key: normalized domain
* Secondary key: canonical name (only if domain n/v)
* No two IDs may share the same domain

---

## 9. Cross-Reference Model

### 9.1 Crossref Graph

<pre class="overflow-visible! px-0!" data-start="5042" data-end="5074"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>meta/crossref_graph.json
</span></span></code></div></div></pre>

### 9.2 Rules

* No reference to non-existent IDs
* Circular references allowed only if semantically valid
* Validator enforces referential integrity

---

## 10. Configuration Ownership

### 10.1 Configuration Domains

* `configs/pipeline/`

  DAG, retries, concurrency
* `configs/contracts/`

  Output and entity schemas
* `configs/rules/`

  Normalization, dedupe, ID policies

### 10.2 Explicit Constraint

No additional schema systems may be introduced.

---

## 11. Error Handling & Failure Semantics

### 11.1 Failure Types

* **Hard FAIL** : pipeline stops
* **Warning** : pipeline continues with annotation

### 11.2 Retry Policy

* Limited retries per step
* Fix instructions passed back to agent
* Infinite retries forbidden

---

## 12. Exports Layer

### 12.1 Final Deliverables

* report.md (human-readable intelligence)
* entities.json (machine-consumable table)
* index / crossref matrix (navigation + linkage)

### 12.2 Export Rules

* Derived only from validated artifacts
* No recomputation
* No additional inference

---

## 13. Audit & Compliance Guarantees

The architecture guarantees:

* Full traceability from output to source
* Deterministic pipeline behavior
* Explicit handling of unknowns via `"n/v"`
* Structural correctness independent of LLM behavior
* Safe extensibility by adding agents without weakening governance

---

## 14. Architectural Summary

This system follows a  **strict separation of concerns** :

* Humans interact via UI
* Orchestrator controls flow
* Agents create content
* Validator enforces structure
* Registry preserves identity
* Artifacts preserve truth

This makes the pipeline **scalable, reviewable, and defensible** in professional, regulatory, and commercial contexts.
