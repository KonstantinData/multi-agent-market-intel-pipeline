from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

from src.orchestrator.dag_loader import StepNode


@dataclass
class BatchScheduler:
    """Determines which steps are ready based on DAG dependencies."""

    dag: List[StepNode]

    def ready_steps(self, completed: Iterable[str]) -> List[StepNode]:
        completed_set = set(completed)
        ready = []
        for node in self.dag:
            if node.step_id in completed_set:
                continue
            if set(node.depends_on).issubset(completed_set):
                ready.append(node)
        return ready

    def remaining_steps(self, completed: Iterable[str]) -> Set[str]:
        completed_set = set(completed)
        return {node.step_id for node in self.dag if node.step_id not in completed_set}
