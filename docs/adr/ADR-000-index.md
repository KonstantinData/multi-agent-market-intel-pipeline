# Architekturentscheidungen (ADR)

Diese Sammlung dokumentiert die zentralen Architekturentscheidungen des Multi‑Agent‑Market‑Intel‑Pipelinesystems.

## Index

| ADR | Titel | Status | Kurzfassung |
| --- | ----- | ------ | ---------- |
| [ADR-001](ADR-001-parallel-fanout-fanin.md) | Parallel Fan‑out/Fan‑in (Orchestrierung/DAG) | Angenommen | Pipeline wird als DAG orchestriert, mit paralleler Ausführung und deterministischem Zusammenführen. |
| [ADR-002](ADR-002-contract-gated-validation.md) | Contract‑Gated Validation | Angenommen | Artefakte passieren eine definierte Contract‑Schicht, bevor sie weiterverarbeitet werden. |
| [ADR-003](ADR-003-central-entity-registry-and-ids.md) | Zentrales Entity‑Registry & ID‑Merge | Angenommen | Entitäten werden zentral registriert und dedupliziert, IDs werden gemerged. |
| [ADR-004](ADR-004-run-artifact-model.md) | Run‑Artifact‑Modell | Angenommen | Jeder Pipeline‑Run erzeugt versionierte Artefakte mit klarer Nachvollziehbarkeit. |
