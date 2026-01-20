from __future__ import annotations

from dataclasses import dataclass
from typing import List

import yaml


@dataclass(frozen=True)
class StepNode:
    step_id: str
    depends_on: List[str]


@dataclass(frozen=True)
class DagConfig:
    nodes: List[StepNode]


def load_dag(path: str) -> DagConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    nodes: List[StepNode] = []
    for entry in data.get("dag", []) or []:
        step_id = str(entry.get("step_id"))
        depends_on = entry.get("depends_on", []) or []
        nodes.append(StepNode(step_id=step_id, depends_on=list(depends_on)))
    return DagConfig(nodes=nodes)
