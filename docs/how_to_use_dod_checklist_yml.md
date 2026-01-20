# How to Use `dod_checklist.yml`

This document explains the **intended usage, scope, and enforcement model** of the
`dod_checklist.yml` file.

The checklist is not documentation fluff.
It is a **machine-checkable acceptance contract** for the repository.

---

## 1. Purpose of `dod_checklist.yml`

The `dod_checklist.yml` defines **what “DONE” objectively means** for this project.

It serves as:

- a **single source of truth** for completion criteria
- a **machine-enforceable acceptance gate**
- a **shared contract** between humans, agents, CI, and reviewers

Anything not explicitly satisfied in this checklist is, by definition, **not done**.

---

## 2. What This File Is (and Is Not)

### It IS

- A deterministic checklist (true / false conditions)
- Automatable by scripts and CI jobs
- A governance artifact
- A review and audit tool
- A guardrail against silent quality degradation

### It IS NOT

- A roadmap
- A wish list
- A high-level architecture description
- A replacement for tests or validators
- A subjective quality assessment

---

## 3. Who Uses It

### 3.1 CI / Automation

CI pipelines can:

- Parse `dod_checklist.yml`
- Enforce subsets of checks (e.g. testing, exports)
- Fail builds if required conditions are unmet

Example uses:

- Block merges if `pytest_passes != true`
- Block releases if mandatory exports are missing
- Assert no writes outside `artifacts/`

---

### 3.2 Gatekeeper / Validator Logic

The Output Contract Validator maps directly to:

- `hard_fail_conditions`
- `evidence_rules`
- `registry_and_identity`
- `cross_reference_integrity`

The validator should ensure that **no agent output flips any checklist item from true to false**.

---

### 3.3 Human Reviewers / Auditors

Reviewers use the checklist as:

- an acceptance scorecard
- a binary approval gate

Review question becomes:

> “Which checklist items are false, and why?”

Not:

> “Does this look good to me?”

---

### 3.4 LLM / Agent Instructions

Agents can be instructed:

> “Your output must not cause any item in `dod_checklist.yml` to become false.”

This removes ambiguity and prevents:

- schema drift
- undocumented assumptions
- silent contract violations

---

## 4. How to Enforce It in Practice

### 4.1 Partial Enforcement Is Allowed

Not all checks must be enforced at once.

Typical progression:

1. Enforce `testing` + `artifact_layout`
2. Enforce `gatekeeper_validation`
3. Enforce `registry_and_identity`
4. Enforce full `final_acceptance`

The checklist supports **incremental hardening**.

---

### 4.2 Binary Semantics

Each checklist item is interpreted strictly:

- `true` = satisfied
- `false` = not satisfied
- missing = not satisfied

There are no “partial passes”.

---

## 5. Relationship to Tests and Validators

- **Tests** prove behavior
- **Validators** enforce structure
- **DoD checklist** defines acceptance

All three are required.
None replace the others.

The checklist answers:

> “Are we allowed to call this DONE?”

---

## 6. Change Management Rules

Changes to `dod_checklist.yml` are **high-impact**.

Recommended rules:

- Treat checklist changes like breaking changes
- Require explicit justification
- Never weaken constraints silently
- Tightening constraints is allowed and encouraged

---

## 7. Why This Matters

Without a machine-checkable DoD:

- quality degrades silently
- governance erodes over time
- agents optimize for output volume, not correctness
- reviews become subjective and inconsistent

With it:

- quality is explicit
- enforcement is automatable
- scaling agents does not scale chaos
- audits become trivial

---

## 8. Final Statement

`dod_checklist.yml` is the **acceptance authority** of this repository.

If a condition is not satisfied:

- the system is **not done**
- the run is **not acceptable**
- the output is **not production-grade**

There are no exceptions.
