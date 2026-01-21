"""
    DESCRIPTION
    -----------
    dag_loader reads configs/pipeline/dag.yml and returns the canonical execution order.
The current repo uses a linear list of step IDs, but this loader is forward-compatible
with a dependency graph representation.
    """

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Union

import yaml


#note: A minimal in-memory DAG representation for orchestration.
@dataclass(frozen=True)
class DagSpec:
    """
    #note: steps_order is the deterministic topological order produced by the loader.
    """
    steps_order: List[str]
    deps: Dict[str, List[str]]


#note: Load dag.yml from disk and normalize into a DagSpec.
def load_dag(dag_path: Path) -> DagSpec:
    """
    #note: Supported formats:

    1) Linear list:
       - AG-00
       - AG-01
       - ...

    2) Graph:
       steps:
         AG-00: []
         AG-01: [AG-00]
         AG-10: [AG-00, AG-01]
       order: [AG-00, AG-01, ...]   # optional
    """
    raw = yaml.safe_load(dag_path.read_text(encoding="utf-8"))

    #note: Linear format: list of step IDs.
    if isinstance(raw, list):
        steps = [str(s).strip() for s in raw if str(s).strip()]
        return DagSpec(steps_order=steps, deps={s: [] for s in steps})

    #note: Graph format.
    if isinstance(raw, dict) and "steps" in raw:
        steps_map = raw.get("steps", {}) or {}
        deps: Dict[str, List[str]] = {}
        for k, v in steps_map.items():
            deps[str(k).strip()] = [str(x).strip() for x in (v or [])]

        #note: Prefer explicit order if provided, otherwise compute a deterministic topo sort.
        order_raw = raw.get("order")
        if isinstance(order_raw, list) and order_raw:
            order = [str(s).strip() for s in order_raw if str(s).strip()]
        else:
            order = _topo_sort(deps)

        return DagSpec(steps_order=order, deps=deps)

    raise ValueError(f"Unsupported DAG format in {dag_path}")


#note: Deterministic topological sort with lexical tie-breaking.
def _topo_sort(deps: Dict[str, List[str]]) -> List[str]:
    remaining: Set[str] = set(deps.keys())
    resolved: Set[str] = set()
    order: List[str] = []

    while remaining:
        ready = sorted([s for s in remaining if set(deps.get(s, [])) <= resolved])
        if not ready:
            raise ValueError(f"DAG has a cycle or unresolved deps: {sorted(remaining)}")
        for step in ready:
            order.append(step)
            remaining.remove(step)
            resolved.add(step)

    return order
