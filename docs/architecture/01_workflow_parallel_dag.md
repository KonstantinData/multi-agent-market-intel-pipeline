# Workflow DAG & Parallelization

This document reflects the **current, enforced DAG** and how the scheduler decides what can run in parallel.

## 1. Source of Truth

The pipeline DAG is loaded directly from `configs/pipeline/dag.yml`, and every run follows that order exactly as listed in the file. The orchestrator walks the DAG nodes sequentially and hard-fails if any dependency is missing. This means **the declared DAG is authoritative** for step ordering and parallelization eligibility.

## 2. Current DAG (v1)

The current DAG is a **linear chain** (no fan-out). As configured today, there is no parallel execution; every step depends on the previous one.

```mermaid
graph TD
  AG00[AG-00 Intake Normalization]
  AG01[AG-01 Source Registry]
  AG10[AG-10 Identity & Legal]
  AG11[AG-11 Locations & Sites]
  AG20[AG-20 Company Size]
  AG21[AG-21 Financial Signals]
  AG30[AG-30 Portfolio]
  AG31[AG-31 Markets Focus]
  AG40[AG-40 Target Customers]
  AG41[AG-41 Peer Discovery]
  AG42[AG-42 Customers of Manufacturers]
  AG70[AG-70 Supply Chain Tech]
  AG71[AG-71 Supply Chain Risks]
  AG72[AG-72 Sustainability & Circular]
  AG81[AG-81 Industry Trends]
  AG82[AG-82 Trade Fairs & Events]
  AG83[AG-83 Associations & Memberships]
  AG90[AG-90 Sales Playbook]

  AG00 --> AG01 --> AG10 --> AG11 --> AG20 --> AG21 --> AG30 --> AG31 --> AG40 --> AG41 --> AG42 --> AG70 --> AG71 --> AG72 --> AG81 --> AG82 --> AG83 --> AG90
```

### DAG Definition (excerpt)

```yaml
- step_id: "AG-00"
  depends_on: []
- step_id: "AG-01"
  depends_on: ["AG-00"]
- step_id: "AG-10"
  depends_on: ["AG-01"]
# ...
- step_id: "AG-90"
  depends_on: ["AG-83"]
```

## 3. Parallelization Rules

Parallelism is **possible**, but only when the DAG contains multiple nodes that depend on the same prerequisites. The batch scheduler computes the ready set by checking whether a node's dependencies are a subset of completed steps.

- If two steps share the same dependency set (or one depends only on already completed nodes), they are **eligible to run in parallel**.
- If a step has any unmet dependency, it **must not** run.

As of the current DAG, **every node depends on the immediately previous step**, so **no parallel batches exist**.

## 4. Change Policy

To introduce real parallelization:

1. Update `configs/pipeline/dag.yml` to introduce branches.
2. Ensure the orchestrator continues to enforce dependency presence (no implicit ordering).
3. Keep gatekeeping intact: any step failure stops downstream nodes even if they were parallel-eligible.

The DAG remains the single control plane for step ordering and potential concurrency.
