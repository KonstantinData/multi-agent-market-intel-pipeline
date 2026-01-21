# Entity Registry & ID Policy

This document reflects the **actual registry data model**, the ID allocation rules, and the dedupe policy used during report/export generation.

## 1. Registry Data Model

The registry is an in-memory model that aggregates `entities_delta` and `relations_delta` from step outputs. It has two primary collections:

- `entities_by_id`: map of `entity_id` → entity payload
- `relations`: list of `{source_id, relation_type, target_id, evidence}`

Each entity contains:

- `entity_id` (string)
- `entity_type` (string)
- `entity_name` (string)
- `domain` (string or null)
- `entity_key` (string)
- `attributes` (free-form dict of extra fields)
- `sources` (list of evidence entries)

## 2. Entity Keys

Entity keys are **deterministic** and are used for deduplication and identity matching.

- If a domain is present, the key is `domain:<normalized_domain>`.
- Otherwise, it can fall back to a normalized name key: `name:<normalized_name>`.
- If neither is present, the key becomes `n/v`.

Normalization strips protocols, paths, and query strings from domains and lowercases them.

## 3. ID Allocation Rules

Entity IDs are assigned by the `IdAllocator`:

- `target_company` is always `TGT-001`.
- Other entity types receive a type-based prefix and a 3-digit counter:
  - `manufacturer` → `MFR-001`, `MFR-002`, ...
  - `customer` → `CUS-001`, `CUS-002`, ...
  - `location_site` → `LOC-001`, `LOC-002`, ...
  - `subsidiary` → `SUB-001`, `SUB-002`, ...
  - unknown types → `ENT-001`, ...

The allocator seeds counters from existing registry IDs to avoid collisions.

## 4. Deduplication Policy

Entity deltas are deduplicated before merging:

1. Use `entity_key` if present and not `n/v`.
2. Else, fall back to normalized `domain`.
3. If neither exists, fall back to `name:<lowercased_name>`.

Duplicate entities are dropped from the delta; the surviving entity has its `entity_key` enforced.

## 5. Merge Semantics

During merge:

- **New entities** are added with allocated IDs if missing.
- **Existing entities** are updated by **merging attributes** and **appending sources**.
- Relations are appended as-is (no dedupe in the merger).

## 6. Cross-Reference Integrity

Cross-reference validation ensures `relation.source_id` and `relation.target_id` exist in the registry before exports are produced. This enforces referential integrity across run artifacts and exports.
