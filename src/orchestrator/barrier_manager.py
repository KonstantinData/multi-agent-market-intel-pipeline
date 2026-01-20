from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set


@dataclass
class Barrier:
    name: str
    required_steps: Set[str]
    reached_steps: Set[str] = field(default_factory=set)

    def mark_complete(self, step_id: str) -> None:
        self.reached_steps.add(step_id)

    def ready(self) -> bool:
        return self.required_steps.issubset(self.reached_steps)


@dataclass
class BarrierManager:
    """Tracks fan-in barriers for DAG execution."""

    barriers: dict[str, Barrier] = field(default_factory=dict)

    def add_barrier(self, name: str, required_steps: Iterable[str]) -> None:
        self.barriers[name] = Barrier(name=name, required_steps=set(required_steps))

    def mark_step_complete(self, step_id: str) -> None:
        for barrier in self.barriers.values():
            if step_id in barrier.required_steps:
                barrier.mark_complete(step_id)

    def ready_barriers(self) -> list[str]:
        return [name for name, barrier in self.barriers.items() if barrier.ready()]
