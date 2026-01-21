# Known Limitations

The current implementation of the multi‑agent market intel pipeline is production‑ready in terms of determinism, orchestrator wiring and artifact generation, but several limitations remain.

## Baseline Agents

Agents AG‑21 through AG‑90 are provided as baseline implementations that return empty deltas and placeholder findings. They do not perform real research or enrichment. Future work should replace these baseline agents with real logic using reliable data sources or LLMs.

## ID Policy Simplification

The entity ID policy uses a simple SHA‑1 hash on the type and name fields. This may cause collisions or unstable identifiers if the name changes across runs. A more sophisticated ID strategy should be implemented for long‑term consistency.

## Lack of Parallel Execution

The orchestrator currently executes steps sequentially, despite the DAG supporting potential parallelism. Concurrency settings are defined but not applied. Future improvements could parallelize independent steps based on DAG dependencies.

## External API Calls in AG‑10/AG‑11/AG‑20

The implemented research agents (AG‑10, AG‑11, AG‑20) rely on external HTTP requests and optional LLM calls. In a production environment, these calls should be mocked or stubbed in tests to ensure reliability and determinism.

## Limited Validation

The generic validator dispatches to known step validators. For new baseline agents, the validator only checks basic schema; it does not enforce detailed semantics. Additional contracts should be defined and implemented for each new agent.